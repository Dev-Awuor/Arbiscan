from collections import Counter

from django.db.models import Avg, Count, Max
from django.conf import settings
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Fixture, BookmakerOdds, ArbitrageResult
from .serializers import (FixtureSerializer, BookmakerOddsSerializer,
                          ArbitrageResultSerializer, CalcInputSerializer)
from .services.engine import scan_fixture
from .services.calculator import calc_stakes
from .services import reporting

# Everything except the calculator requires login (DEFAULT_PERMISSION_CLASSES).


def _open_arbs():
    """Valid arbs on fixtures that have not kicked off yet."""
    return ArbitrageResult.objects.filter(
        is_valid=True, profit_pct__gt=0, fixture__kickoff__gt=timezone.now())


@api_view(["POST"])
@permission_classes([AllowAny])
def calculator_view(request):
    """Public arbitrage calculator. Pure math, no data feed."""
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
    serializer_class = FixtureSerializer
    queryset         = Fixture.objects.filter(status="upcoming").order_by("kickoff")


class FixtureDetailView(generics.RetrieveAPIView):
    serializer_class = FixtureSerializer
    queryset         = Fixture.objects.prefetch_related("odds")
    lookup_field     = "pk"


class ArbitrageResultListView(generics.ListAPIView):
    serializer_class = ArbitrageResultSerializer
    queryset         = ArbitrageResult.objects.filter(is_valid=True).order_by("-profit_pct")


@api_view(["GET"])
def live_sure_bets_view(request):
    """Open arbs, each sized so the match alone yields `target` profit.
    Reuses reporting.build_snapshot so numbers match the signed PDF reports."""
    try:
        target = float(request.query_params.get("target", 500))
    except ValueError:
        target = 0
    if target <= 0:
        return Response({"error": "target must be a positive number"}, status=400)

    qs = _open_arbs().select_related("fixture").order_by("-profit_pct")
    if request.query_params.get("market"):
        qs = qs.filter(market=request.query_params["market"])
    rows = reporting.build_snapshot(qs[:100], target)
    return Response({"target": target, "count": len(rows), "sure_bets": rows})


@api_view(["GET"])
def stats_view(request):
    """Pipeline health + arb summary for the dashboard overview."""
    now   = timezone.now()
    arbs  = _open_arbs()
    odds  = BookmakerOdds.objects.filter(is_active=True, fixture__kickoff__gt=now)
    agg   = arbs.aggregate(n=Count("id"), best=Max("profit_pct"), avg=Avg("profit_pct"))
    books = Counter(b for bs in arbs.values_list("books", flat=True) for b in (bs or []))
    num   = lambda v: round(float(v), 3) if v is not None else None
    return Response({
        "fixtures":    Fixture.objects.filter(kickoff__gt=now).count(),
        "odds_rows":   odds.count(),
        "books":       sorted(odds.values_list("bookmaker", flat=True).distinct()),
        "last_fetch":  BookmakerOdds.objects.aggregate(t=Max("fetched_at"))["t"],
        "last_scan":   ArbitrageResult.objects.aggregate(t=Max("scanned_at"))["t"],
        "arbs":        agg["n"],
        "best_margin": num(agg["best"]),
        "avg_margin":  num(agg["avg"]),
        "by_market":   list(arbs.values("market").annotate(n=Count("id")).order_by("-n")),
        "by_book":     [{"book": b, "n": n} for b, n in books.most_common()],
    })


@api_view(["POST"])
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
