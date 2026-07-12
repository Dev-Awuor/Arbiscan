from django.core.management.base import BaseCommand
from django.conf import settings
from odds.models import ArbitrageResult
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

MARKET_LEGS = {
    "FT_1X2":     ["Home",  "Draw",  "Away"],
    "H2H":        ["Home",  "Away"],
    "BTTS":       ["Yes",   "No"],
    "OU25":       ["Over",  "Under"],
    "OU15":       ["Over",  "Under"],
    "OU35":       ["Over",  "Under"],
    "DC":         ["1X",    "X2",    "12"],
    "DNB":        ["Home",  "Away"],
    "HT_1X2":     ["Home",  "Draw",  "Away"],
    "SET1":       ["Home",  "Away"],
    "DC_1X+Away": ["1X",    "Away"],
    "DC_X2+Home": ["X2",    "Home"],
    "DC_12+Draw": ["12",    "Draw"],
    "DC_1X+Draw": ["1X",    "Draw"],
    "DC_X2+Draw": ["X2",    "Draw"],
    "DC_12+Home": ["12",    "Home"],
}


def to_list(val):
    """Ensure val is always a list regardless of how it was stored."""
    if isinstance(val, list):
        return val
    if isinstance(val, dict):
        return list(val.values())
    return [val]


def scale_to_target(arb, target_profit: float):
    current_profit = float(arb.profit)
    if current_profit <= 0:
        return None
    scale    = target_profit / current_profit
    stakes   = [round(float(s) * scale, 2) for s in to_list(arb.stakes)]
    bankroll = round(sum(stakes), 2)
    return {"bankroll": bankroll, "profit": round(target_profit, 2), "stakes": stakes}


class Command(BaseCommand):
    help = "Show arb report  use --target KES to scale stakes to a profit goal"

    def add_arguments(self, parser):
        parser.add_argument("--top",      type=int,   default=20)
        parser.add_argument("--target",   type=float, default=None,
                            help="KES profit you want  e.g. --target 500")
        parser.add_argument("--bankroll", type=float, default=None)

    def handle(self, *args, **options):
        bankroll = options["bankroll"] or float(getattr(settings, "DEFAULT_BANKROLL", 10000))
        arbs     = ArbitrageResult.objects.filter(is_valid=True).order_by("-profit_pct")

        if not arbs.exists():
            self.stdout.write(self.style.WARNING(
                "No results. Run: python manage.py scan_arbs"))
            return

        if options["target"]:
            self._target_report(arbs, options["target"])
        else:
            self._standard_report(arbs, options["top"])

    #  Target mode 

    def _target_report(self, arbs, target: float):
        console.print(f"\n[bold cyan]ARBISCAN  TARGET: KES {target:,.0f} profit per match[/bold cyan]\n")

        # Each card is sized independently so that THAT match alone yields the
        # target profit - the bettor can place any single card to hit the goal.
        cards = []
        for arb in arbs:
            if float(arb.profit_pct) <= 0:
                continue
            scaled = scale_to_target(arb, target)
            if scaled:
                cards.append((arb, scaled))

        if not cards:
            console.print("[red]No valid arbs. Run fetch_odds + scan_arbs first.[/red]")
            return

        # Summary table  ranked by margin (least bankroll first)
        t = Table(box=box.ROUNDED, header_style="bold magenta", expand=True)
        t.add_column("#",        width=4, style="bold yellow")
        t.add_column("Match",    min_width=28)
        t.add_column("Market",   width=8)
        t.add_column("Margin",   justify="right", width=9)
        t.add_column("Bankroll", justify="right", width=16)
        t.add_column("Profit",   justify="right", style="bold green", width=14)

        for i, (arb, scaled) in enumerate(cards, 1):
            t.add_row(
                f"#{i}",
                str(arb.fixture),
                arb.market,
                f"+{arb.profit_pct}%",
                f"KES {scaled['bankroll']:>12,.2f}",
                f"KES {scaled['profit']:>10,.2f}",
            )

        console.print(t)
        cheapest = min(cards, key=lambda c: c[1]["bankroll"])
        console.print(
            f"\n  Each card is sized to make [bold green]KES {target:,.0f}[/bold green] on its own.")
        console.print(
            f"  Cheapest to hit target: [bold]{cheapest[0].fixture}[/bold] "
            f"with KES {cheapest[1]['bankroll']:,.2f} bankroll.\n")

        # Action cards
        console.print("[bold cyan] ACTION CARDS [/bold cyan]")
        self._print_cards(cards)

    #  Standard mode 

    def _standard_report(self, arbs, top: int):
        results = list(arbs[:top])
        console.print(f"\n[bold cyan]ARBISCAN  Top {len(results)} Arbs[/bold cyan]\n")

        t = Table(box=box.ROUNDED, header_style="bold magenta", expand=True)
        t.add_column("Match",    min_width=28)
        t.add_column("Kickoff",  width=12)
        t.add_column("Market",   width=8)
        t.add_column("Books",    min_width=24)
        t.add_column("Margin",   justify="right", width=9)
        t.add_column("Profit",   justify="right", style="bold green", width=14)

        for arb in results:
            books_str = " / ".join(to_list(arb.books))
            t.add_row(
                str(arb.fixture),
                str(arb.fixture.kickoff)[:10] if arb.fixture.kickoff else "?",
                arb.market,
                books_str,
                f"+{arb.profit_pct}%",
                f"KES {float(arb.profit):>10,.2f}",
            )

        console.print(t)

        cards = [(arb, {"stakes": to_list(arb.stakes),
                        "profit": float(arb.profit),
                        "bankroll": float(arb.bankroll)}) for arb in results]
        self._print_cards(cards)

    #  Shared action card printer 

    def _print_cards(self, cards):
        for i, (arb, scaled) in enumerate(cards, 1):
            books  = to_list(arb.books)
            odds   = to_list(arb.odds)
            stakes = scaled["stakes"]
            # For 2-way H2H (tennis/basketball/MMA) the legs ARE the two
            # participants, so name them directly instead of "Home/Away".
            if arb.market == "H2H":
                legs = [arb.fixture.home_team, arb.fixture.away_team]
            else:
                legs = MARKET_LEGS.get(arb.market, [f"Leg{j+1}" for j in range(len(odds))])

            console.print(f"\n[bold yellow]#{i}  {arb.fixture}[/bold yellow]")
            console.print(f"    Kickoff : {arb.fixture.kickoff}  |  Market: [cyan]{arb.market}[/cyan]")
            console.print(f"    {''*54}")
            for j in range(len(odds)):
                leg   = legs[j]   if j < len(legs)   else f"Leg{j+1}"
                book  = books[j]  if j < len(books)  else "?"
                odd   = float(odds[j])
                stake = float(stakes[j]) if j < len(stakes) else 0
                console.print(
                    f"    Bet [bold]KES {stake:>10,.2f}[/bold]  on "
                    f"[cyan]{leg:<5}[/cyan] @ {odd:.3f}    [magenta]{book.upper()}[/magenta]"
                )
            console.print(f"    {''*54}")
            console.print(
                f"    [bold green]Guaranteed profit: KES {scaled['profit']:>10,.2f}"
                f"  (+{arb.profit_pct}%)[/bold green]")
