from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Prefetch
from odds.models import Fixture, BookmakerOdds, ArbitrageResult
from odds.services.engine import scan_fixture


class Command(BaseCommand):
    help = "Scan stored odds for arbitrage and save results"

    def add_arguments(self, parser):
        parser.add_argument("--min-profit",    type=float, default=0.0)
        parser.add_argument("--bankroll",       type=float, default=None)
        parser.add_argument("--threshold",      type=float, default=None)
        parser.add_argument("--markets",        nargs="+",
                            default=["FT_1X2","BTTS","OU25","OU15","OU35"])
        parser.add_argument("--leagues",        nargs="+", default=None)
        parser.add_argument("--near-miss-only", action="store_true")
        parser.add_argument("--clear",          action="store_true")

    def handle(self, *args, **options):
        bankroll  = options["bankroll"]  or settings.DEFAULT_BANKROLL
        threshold = options["threshold"] or settings.NEAR_MISS_THRESHOLD
        markets   = options["markets"]
        nm_only   = options["near_miss_only"]

        if options["clear"]:
            n, _ = ArbitrageResult.objects.all().delete()
            self.stdout.write(f"Cleared {n} previous results")

        qs = Fixture.objects.filter(status="upcoming").prefetch_related(
            Prefetch("odds", queryset=BookmakerOdds.objects.filter(is_active=True)))

        if options["leagues"]:
            t_map = settings.TOURNAMENT_MAP
            tids  = [t_map[l][0] for l in options["leagues"] if l in t_map]
            qs    = qs.filter(tournament__api_id__in=tids)

        self.stdout.write(f"\nScanning {qs.count()} fixtures | KES {bankroll:,.0f}\n")
        total_arbs = total_nm = 0

        for fixture in qs:
            book_data = {}
            for o in fixture.odds.all():
                if o.market in markets:
                    book_data.setdefault(o.bookmaker, {})[o.market] = o.as_dict()
            if len(book_data) < 2:
                continue
            results = scan_fixture(book_data, bankroll=bankroll,
                                   near_miss_threshold=threshold)
            arbs = [r for r in results if r["arb"]]
            nms  = [r for r in results if not r["arb"]]
            if not nm_only:
                for r in arbs:
                    if r["profit_pct"] >= options["min_profit"]:
                        home_o = max((book_data[b].get("FT_1X2",{}).get("home",0)
                                      for b in book_data), default=0)
                        away_o = max((book_data[b].get("FT_1X2",{}).get("away",0)
                                      for b in book_data), default=0)
                        ArbitrageResult.objects.update_or_create(
                            fixture=fixture, market=r["market"], books=r["books"],
                            defaults={
                                "pair_label":  r["pair"],
                                "odds":        r["odds"],
                                "stakes":      r["stakes"],
                                "bankroll":    bankroll,
                                "payout":      r["payout"],
                                "profit":      r["profit_kes"],
                                "profit_pct":  r["profit_pct"],
                                "arb_sum":     r["sum"],
                                "is_high_odds": max(home_o,away_o) >= 4.0,
                                "is_valid":    True,
                            })
                        total_arbs += 1
            if nm_only and nms:
                best = nms[0]
                self.stdout.write(
                    f"  NM  {fixture.home_team} vs {fixture.away_team:<30} "
                    f"{best['market']:<10} {'/'.join(best['books']):<24} "
                    f"-{best['overround_pct']:.3f}%")
            total_nm += len(nms)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone - {total_arbs} arbs saved, {total_nm} near-misses."))
