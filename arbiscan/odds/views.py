from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from .models import Fixture, BookmakerOdds, ArbitrageResult
from .serializers import (FixtureSerializer, BookmakerOddsSerializer,
                          ArbitrageResultSerializer, CalcInputSerializer)
from .services.engine import scan_fixture
from .services.calculator import calc_stakes
from .services import reporting
from accounts.permissions import IsPremium


@api_view(["POST"])
@permission_classes([AllowAny])
def calculator_view(request):
    """FREE public arbitrage calculator. No auth, no data feed - pure math."""
    ser = CalcInputSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    d = ser.validated_data
    try:
        result = calc_stakes(
            d["odds"],
            total_stake=d.get("total_stake"),
            target_profit=d.get("target_profit"),
        )
    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    return Response(result)


class FixtureListView(generics.ListAPIView):
    permission_classes = [IsPremium]
    serializer_class   = FixtureSerializer
    queryset           = Fixture.objects.filter(status="upcoming").order_by("kickoff")


class FixtureDetailView(generics.RetrieveAPIView):
    permission_classes = [IsPremium]
    serializer_class   = FixtureSerializer
    queryset           = Fixture.objects.prefetch_related("odds")
    lookup_field       = "pk"


class ArbitrageResultListView(generics.ListAPIView):
    permission_classes = [IsPremium]
    serializer_class   = ArbitrageResultSerializer
    queryset           = ArbitrageResult.objects.filter(is_valid=True).order_by("-profit_pct")


def _is_premium(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    sub = getattr(user, "subscription", None)
    return bool(sub and sub.is_premium)


@api_view(["GET"])
@permission_classes([AllowAny])
def live_sure_bets_view(request):
    """Live sure-bets feed with a FREEMIUM teaser.

    Free / anonymous users see only the lower-ROI arbs (up to FREE_ARB_ROI_CAP)
    and a count of how many higher-profit ones are locked. Premium unlocks them
    all. Reuses reporting.size_arb so the numbers match the signed PDF reports."""
    target  = float(request.query_params.get("target", 500))
    cap     = float(getattr(settings, "FREE_ARB_ROI_CAP", 1.0))
    premium = _is_premium(request.user)

    qs = ArbitrageResult.objects.filter(
        is_valid=True, profit_pct__gt=0).select_related("fixture").order_by("-profit_pct")
    if request.query_params.get("market"):
        qs = qs.filter(market=request.query_params["market"])
    all_arbs = list(qs[:100])

    if premium:
        visible, locked = all_arbs, 0
    else:
        visible = [a for a in all_arbs if float(a.profit_pct) <= cap]
        locked  = len(all_arbs) - len(visible)

    rows = [r for a in visible if (r := reporting.size_arb(a, target))]
    return Response({
        "target":       target,
        "is_premium":   premium,
        "free_roi_cap": cap,
        "count":        len(rows),
        "locked_count": locked,
        "sure_bets":    rows,
    })


@api_view(["POST"])
@permission_classes([IsPremium])
def scan_fixture_view(request, pk):
    try:
        fixture = Fixture.objects.prefetch_related("odds").get(pk=pk)
    except Fixture.DoesNotExist:
        return Response({"error": "Fixture not found"}, status=404)
    book_data = {}
    for o in fixture.odds.filter(is_active=True):
        book_data.setdefault(o.bookmaker, {})[o.market] = o.as_dict()
    if len(book_data) < 2:
        return Response({"error": "Need >= 2 bookmakers"}, status=400)
    bankroll = float(request.data.get("bankroll", settings.DEFAULT_BANKROLL))
    results  = scan_fixture(book_data, bankroll=bankroll)
    return Response({
        "fixture":         f"{fixture.home_team} vs {fixture.away_team}",
        "kickoff":         fixture.kickoff,
        "books_available": list(book_data.keys()),
        "arb_count":       sum(1 for r in results if r["arb"]),
        "near_miss_count": sum(1 for r in results if not r["arb"]),
        "results":         results,
    })


@api_view(["POST"])
@permission_classes([IsPremium])
def add_manual_odds_view(request, pk):
    try:
        fixture = Fixture.objects.get(pk=pk)
    except Fixture.DoesNotExist:
        return Response({"error": "Fixture not found"}, status=404)
    data = request.data
    mkt  = data.get("market","FT_1X2")
    book = data.get("bookmaker","")
    if not book:
        return Response({"error": "bookmaker required"}, status=400)
    FIELD_MAP = {
        "FT_1X2": [("leg1","home","Home"),("leg2","draw","Draw"),("leg3","away","Away")],
        "BTTS":   [("leg1","yes","Yes"),("leg2","no","No")],
        "OU25":   [("leg1","over","Over"),("leg2","under","Under")],
        "OU15":   [("leg1","over","Over"),("leg2","under","Under")],
        "OU35":   [("leg1","over","Over"),("leg2","under","Under")],
    }
    mapping = FIELD_MAP.get(mkt, [])
    kwargs  = {"source":"manual","is_active":True,
               "leg1_label":"","leg2_label":"","leg3_label":""}
    for db_field, data_key, label_val in mapping:
        val = data.get(data_key)
        if val is None:
            return Response({"error": f"Missing: {data_key}"}, status=400)
        kwargs[db_field] = val
        kwargs[f"{db_field}_label"] = label_val
    obj, created = BookmakerOdds.objects.update_or_create(
        fixture=fixture, bookmaker=book, market=mkt, defaults=kwargs)
    return Response(BookmakerOddsSerializer(obj).data,
                    status=status.HTTP_201_CREATED if created else 200)
