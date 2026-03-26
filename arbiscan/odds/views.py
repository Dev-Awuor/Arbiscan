from rest_framework import generics, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings
from .models import Fixture, BookmakerOdds, ArbitrageResult
from .serializers import FixtureSerializer, BookmakerOddsSerializer, ArbitrageResultSerializer
from .services.engine import scan_fixture


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
