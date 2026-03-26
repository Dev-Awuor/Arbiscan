MAX_ODDS_CAP = 30.0  # reject corrupted/ghost odds
from django.core.management.base import BaseCommand
from odds.models import Fixture, BookmakerOdds, ArbitrageResult


class Command(BaseCommand):
    help = "Scan for intra-platform arbs (same bookmaker, two complementary markets)"

    def add_arguments(self, parser):
        parser.add_argument("--bankroll",   type=float, default=10000)
        parser.add_argument("--min-margin", type=float, default=0.0)
        parser.add_argument("--clear",      action="store_true")

    def handle(self, *args, **options):
        bankroll   = options["bankroll"]
        min_margin = options["min_margin"]

        if options["clear"]:
            deleted, _ = ArbitrageResult.objects.filter(
                pair_label__startswith="INTRA:"
            ).delete()
            self.stdout.write(f"Cleared {deleted} previous intra-arb results")

        fixtures = Fixture.objects.all()
        found = 0
        near  = 0

        for fixture in fixtures:
            for r in self.scan_fixture(fixture, bankroll, min_margin):
                if r["margin"] > 0:
                    found += 1
                    ArbitrageResult.objects.update_or_create(
                        fixture    = fixture,
                        market     = r["label"],
                        pair_label = f"INTRA:{r['book']}:{r['label']}",
                        defaults={
                            "bankroll":   bankroll,
                            "profit":     r["profit"],
                            "profit_pct": r["margin"],
                            "arb_sum":    r["imp_total"],
                            "books":      [r["book"], r["book"]],
                            "odds":       [r["odd_a"], r["odd_b"]],
                            "stakes":     [r["stake_a"], r["stake_b"]],
                            "payout":     round(r["stake_a"] * r["odd_a"], 2),
                            "is_valid":   True,
                            "is_high_odds": r["odd_a"] > 3.0 or r["odd_b"] > 3.0,
                        }
                    )
                else:
                    near += 1

        self.stdout.write(self.style.SUCCESS(
            f"Done - {found} intra-arbs found, {near} near-misses"
        ))

    def scan_fixture(self, fixture, bankroll, min_margin):
        results = []
        ft_qs   = BookmakerOdds.objects.filter(fixture=fixture, market="FT_1X2")
        dc_qs   = BookmakerOdds.objects.filter(fixture=fixture, market="DC")
        btts_qs = BookmakerOdds.objects.filter(fixture=fixture, market="BTTS")
        ou15_qs = BookmakerOdds.objects.filter(fixture=fixture, market="OU15")
        ou25_qs = BookmakerOdds.objects.filter(fixture=fixture, market="OU25")

        # --- DC + FT_1X2 (requires DC market in DB) ---
        for dc in dc_qs:
            book = dc.bookmaker
            ft   = ft_qs.filter(bookmaker=book).first()
            if not ft:
                continue
            checks = [
                ("DC_1X+Away", dc.leg1, ft.leg3),
                ("DC_X2+Home", dc.leg2, ft.leg1),
                ("DC_12+Draw", dc.leg3, ft.leg2),
            ]
            results.extend(self._eval(checks, book, bankroll, min_margin))

        # NOTE: BTTS+OU and OU15+OU25 combos removed - they are NOT
        # collectively exhaustive and produce false arbitrage signals.
        # Only DC+FT_1X2 combos are mathematically valid intra-book arbs.
        # DC market data needed - run fetch_odds after adding DC to extractor.

        return results

    def _eval(self, checks, book, bankroll, min_margin):
        results = []
        for label, odd_a, odd_b in checks:
            if not odd_a or not odd_b:
                continue
            try:
                imp_a = 1.0 / float(odd_a)
                imp_b = 1.0 / float(odd_b)
            except (ZeroDivisionError, TypeError):
                continue
            total  = imp_a + imp_b
            margin = (1.0 - total) * 100
            if margin < min_margin:
                continue
            stake_a = round(bankroll * (imp_a / total), 2)
            stake_b = round(bankroll - stake_a, 2)
            profit  = round((stake_a * float(odd_a)) - bankroll, 2)
            results.append({
                "book":      book,
                "label":     label,
                "odd_a":     float(odd_a),
                "odd_b":     float(odd_b),
                "margin":    round(margin, 4),
                "imp_total": round(total, 6),
                "stake_a":   stake_a,
                "stake_b":   stake_b,
                "profit":    profit,
            })
        return results
