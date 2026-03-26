from django.core.management.base import BaseCommand
from odds.models import ArbitrageResult


class Command(BaseCommand):
    help = "Print intra-platform arb action cards"

    def add_arguments(self, parser):
        parser.add_argument("--target",    type=float, default=500)
        parser.add_argument("--min-margin", type=float, default=0.0)

    def handle(self, *args, **options):
        target     = options["target"]
        min_margin = options["min_margin"]

        arbs = ArbitrageResult.objects.filter(
            pair_label__startswith="INTRA:",
            profit_pct__gt=min_margin
        ).order_by("-profit_pct").select_related("fixture")

        if not arbs.exists():
            self.stdout.write("No intra-arbs found. Run: python manage.py scan_intra_arbs --clear")
            return

        self.stdout.write(f"\nINTRA-PLATFORM ARBS  |  target: KES {target:,.0f} profit")
        self.stdout.write("=" * 65)
        total_profit = 0

        for i, arb in enumerate(arbs, 1):
            parts     = arb.pair_label.split(":")   # INTRA:book:label
            book      = parts[1].upper() if len(parts) > 1 else "?"
            odds_list = arb.odds if isinstance(arb.odds, list) else []
            odd_a     = float(odds_list[0]) if len(odds_list) > 0 else 0
            odd_b     = float(odds_list[1]) if len(odds_list) > 1 else 0

            if not odd_a or not odd_b:
                continue

            needed  = float(target) / (float(arb.profit_pct) / 100)
            imp_a   = 1.0 / odd_a
            imp_b   = 1.0 / odd_b
            total   = imp_a + imp_b
            stake_a = round(needed * (imp_a / total), 2)
            stake_b = round(needed - stake_a, 2)
            profit  = round(stake_a * odd_a - needed, 2)
            total_profit += profit

            label_parts = arb.market.split("+")
            leg_a_lbl   = label_parts[0]
            leg_b_lbl   = label_parts[1] if len(label_parts) > 1 else ""

            self.stdout.write(
                f"\n#{i}  {arb.fixture.home_team} vs {arb.fixture.away_team}"
            )
            self.stdout.write(
                f"    Book   : {book}  |  Market: {arb.market}  |  Margin: +{float(arb.profit_pct):.3f}%"
            )
            self.stdout.write(
                f"    Leg A  : KES {stake_a:>10,.2f}  @ {odd_a:<6}  [{leg_a_lbl}]"
            )
            self.stdout.write(
                f"    Leg B  : KES {stake_b:>10,.2f}  @ {odd_b:<6}  [{leg_b_lbl}]"
            )
            self.stdout.write(
                f"    Profit : KES {profit:>10,.2f}  (total stake: KES {needed:,.0f})"
            )

        self.stdout.write(f"\n{'='*65}")
        self.stdout.write(
            f"  {arbs.count()} intra-arbs  |  Total profit: KES {total_profit:,.2f}"
        )
