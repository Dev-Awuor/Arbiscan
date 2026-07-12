"""
Interactive arbitrage run.

Walks the user through a short build-up of questions:
    sport -> tournament(s) -> target profit -> bankroll -> books
then runs the pipeline (fetch -> cross-book scan -> action-card report).

Focus is clean CROSS-book 2-way arbs (tennis / basketball / MMA via the H2H
market) plus the World Cup (3-way FT_1X2). The old same-bookmaker intra-platform
scan is intentionally NOT used here - it produced fake +50-87% "arbs".
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.conf import settings
from odds.services.oddspapi import OddspapiClient


def _fx_count(t):
    return ((t.get("futureFixtures", 0) or 0)
            + (t.get("upcomingFixtures", 0) or 0)
            + (t.get("liveFixtures", 0) or 0))


def _ask(prompt, default=""):
    try:
        val = input(prompt).strip()
    except EOFError:
        return default
    return val if val else default


def _ask_float(prompt, default):
    raw = _ask(prompt, str(default))
    try:
        return float(raw)
    except ValueError:
        return float(default)


class Command(BaseCommand):
    help = "Interactive arbitrage run (sport -> tournament -> target -> books -> fetch/scan/report)"

    def handle(self, *args, **options):
        sports = settings.SPORTS
        keys   = list(sports.keys())

        # 1) Sport
        self.stdout.write("\n=== ARBISCAN  |  pick a sport ===")
        for i, k in enumerate(keys, 1):
            s = sports[k]
            self.stdout.write(f"  {i}. {s['name']:<16} ({s['type']} / {s['market']})")
        sport_key = None
        sel = _ask("Sport # [1]: ", "1")
        try:
            sport_key = keys[int(sel) - 1]
        except (ValueError, IndexError):
            self.stderr.write("Invalid sport choice."); return
        sport = sports[sport_key]
        self.stdout.write(f"  -> {sport['name']}")

        # 2) Tournament(s)
        tids, tnames = self._pick_tournaments(sport)
        if not tids:
            self.stderr.write("No tournaments available/selected. Aborting."); return

        # 3) Targets
        target   = _ask_float("\nTarget profit KES [500]: ", 500)
        bankroll = _ask_float("Max bankroll per arb KES [10000]: ", 10000)

        # 4) Books (auto-select, show & confirm)
        books = self._pick_books(sport)
        if len(books) < 2:
            self.stderr.write("Need at least 2 books for cross-book arbs. Aborting."); return

        # 5) Confirm
        self.stdout.write("\n--- RUN PLAN " + "-" * 30)
        self.stdout.write(f"  Sport    : {sport['name']}  ({sport['type']}, market {sport['market']})")
        self.stdout.write(f"  Events   : {', '.join(tnames[:6])}" + (" ..." if len(tnames) > 6 else ""))
        self.stdout.write(f"  Target   : KES {target:,.0f}     Bankroll/arb: KES {bankroll:,.0f}")
        self.stdout.write(f"  Books    : {', '.join(books)}")
        self.stdout.write("-" * 43)
        if _ask("Proceed? [Y/n]: ", "y").lower().startswith("n"):
            self.stdout.write("Aborted."); return

        # 6) Pipeline
        self.stdout.write("\n[1/3] Fetching live odds...")
        call_command("fetch_odds", tids=tids, books=books)

        self.stdout.write("\n[2/3] Scanning cross-book arbs...")
        call_command("scan_arbs", clear=True, bankroll=bankroll,
                     markets=[sport["market"]])

        self.stdout.write("\n[3/3] Action cards:\n")
        call_command("arb_report", target=target)

        # 7) Optional traceable PDF
        if not _ask("\nGenerate timestamped PDF report (with traceability QR)? [Y/n]: ",
                    "y").lower().startswith("n"):
            call_command("report_pdf", target=target, sport=sport["name"],
                         market=sport["market"], books=books)

    # ---- helpers -------------------------------------------------------

    def _pick_tournaments(self, sport):
        # Fixed tournaments (e.g. World Cup) - no API call needed.
        if sport.get("tournaments"):
            items = list(sport["tournaments"].values())   # (api_id, name)
            tids  = [str(i[0]) for i in items]
            names = [i[1] for i in items]
            self.stdout.write("  Tournaments: " + ", ".join(names))
            return tids, names

        # Live-fetched (tennis/MMA/basketball rotate weekly).
        self.stdout.write("  Fetching live tournaments (1 API call)...")
        try:
            tours = OddspapiClient().get_tournaments(sport["sport_id"])
        except Exception as e:
            self.stderr.write(f"  Could not list tournaments: {e}")
            return [], []

        active = [t for t in tours if _fx_count(t) > 0]
        nf = sport.get("name_filter") or []
        if nf:
            pref = [t for t in active
                    if any(s.lower() in (str(t.get("tournamentName", "")) + " "
                                         + str(t.get("categoryName", ""))).lower()
                           for s in nf)]
            active = pref or active
        active.sort(key=_fx_count, reverse=True)
        active = active[:20]
        if not active:
            return [], []

        self.stdout.write("\n  Active tournaments:")
        for i, t in enumerate(active, 1):
            self.stdout.write(
                f"   {i:>2}. {t.get('tournamentName')} "
                f"[{t.get('categoryName')}]  ({_fx_count(t)} fx)")

        sel = _ask(f"  Pick #(s) comma-separated, or 'all' [all]: ", "all")
        if sel.lower() == "all":
            chosen = active
        else:
            chosen = []
            for p in sel.split(","):
                try:
                    idx = int(p.strip()) - 1
                    if 0 <= idx < len(active):
                        chosen.append(active[idx])
                except ValueError:
                    continue
        tids  = [str(t.get("tournamentId")) for t in chosen]
        names = [str(t.get("tournamentName")) for t in chosen]
        return tids, names

    def _pick_books(self, sport):
        rec = sport["books"]
        self.stdout.write("\n  Recommended books: " + ", ".join(rec))
        sel = _ask("  Enter to accept, or type a comma-separated list: ", "")
        if not sel:
            return rec
        return [b.strip().lower() for b in sel.split(",") if b.strip()]
