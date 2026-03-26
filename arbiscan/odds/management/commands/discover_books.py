import requests
import time
from django.core.management.base import BaseCommand
from django.conf import settings

# 60+ known bookmaker slugs on OddsPapi spanning sharp, soft, African, Asian
CANDIDATE_BOOKS = [
    # Sharp (low margin, reference prices)
    "pinnacle", "singbet", "sbobet", "isnbet", "isports",
    # Soft European
    "bet365", "williamhill", "bwin", "unibet", "betfair",
    "betvictor", "paddypower", "ladbrokes", "coral",
    "skybet", "betfred", "mrgreen", "888sport",
    # Soft Eastern European / Global
    "1xbet", "marathonbet", "parimatch", "fonbet",
    "betconstruct", "betsson", "nordicbet", "betway",
    # Asian
    "dafabet", "maxbet", "betradar",
    # African
    "sportpesa", "betika", "premierbet", "bangbet",
    "mozzartbet", "betin", "odibets", "hollywoodbets",
    # US
    "draftkings", "fanduel", "betmgm", "caesars", "pointsbet",
    # Others
    "betano", "superbet", "tipsport", "doxxbet",
    "coolbet", "expekt", "betsafe", "bet-at-home",
]

class Command(BaseCommand):
    help = "Discover which bookmakers have data for your tournaments on OddsPapi"

    def add_arguments(self, parser):
        parser.add_argument("--leagues",  nargs="+", default=["ucl","epl"])
        parser.add_argument("--save",     action="store_true",
                            help="Save working books to settings hint")

    def handle(self, *args, **options):
        key    = settings.ODDSPAPI_KEY
        t_map  = settings.TOURNAMENT_MAP
        tids   = [t_map[l][0] for l in options["leagues"] if l in t_map]
        tid_str = ",".join(str(t) for t in tids)

        self.stdout.write(
            f"\nTesting {len(CANDIDATE_BOOKS)} bookmaker slugs "
            f"against tournaments {tids}...\n")

        working  = []
        slugs_by_margin = []

        for slug in CANDIDATE_BOOKS:
            try:
                url = (f"https://api.oddspapi.io/v4/odds-by-tournaments"
                       f"?tournamentIds={tid_str}&bookmaker={slug}"
                       f"&apiKey={key}&oddsFormat=decimal")
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    fixtures_with_odds = [
                        fx for fx in data
                        if isinstance(fx, dict)
                        and slug in fx.get("bookmakerOdds", {})
                        and fx["bookmakerOdds"][slug].get("bookmakerIsActive")
                    ]
                    if fixtures_with_odds:
                        # Estimate margin from first fixture FT_1X2
                        margin = self._estimate_margin(
                            fixtures_with_odds[0]["bookmakerOdds"][slug])
                        working.append(slug)
                        slugs_by_margin.append((slug, len(fixtures_with_odds), margin))
                        status = f"  {len(fixtures_with_odds):>3} fixtures  margin{margin:+.2f}%"
                    else:
                        status = "  no active odds"
                elif r.status_code == 404:
                    status = "  404"
                else:
                    status = f"  HTTP {r.status_code}"
            except Exception as e:
                status = f"  error: {e}"

            self.stdout.write(f"  {slug:<22} {status}")
            time.sleep(0.3)   # be nice to the API

        # Rank by margin (sharpest first)
        slugs_by_margin.sort(key=lambda x: x[2])

        self.stdout.write(f"\n{'='*55}")
        self.stdout.write(f"WORKING BOOKS ({len(working)} found):")
        self.stdout.write(f"{'='*55}")
        self.stdout.write(f"\n{'Book':<22} {'Fixtures':>9} {'Margin':>10}")
        self.stdout.write(f"{'-'*44}")
        for slug, count, margin in slugs_by_margin:
            tag = "  SHARP" if margin < 3.0 else ("  SOFT" if margin > 6.0 else "")
            self.stdout.write(f"  {slug:<20} {count:>8}  {margin:>+8.2f}%{tag}")

        self.stdout.write(f"\n\nRecommended fetch command:")
        top = " ".join(s for s, _, _ in slugs_by_margin[:12])
        self.stdout.write(
            f"python manage.py fetch_odds --leagues ucl epl laliga --books {top}")

    def _estimate_margin(self, bdata: dict) -> float:
        mkts = bdata.get("markets", {})
        m101 = mkts.get("101", {})
        outcomes = m101.get("outcomes", {})
        prices = []
        for oc in outcomes.values():
            p = oc.get("players", {}).get("0", {}).get("price")
            if p and float(p) < 50:
                prices.append(float(p))
        if len(prices) >= 2:
            s = sum(1/p for p in prices)
            return round((s - 1) * 100, 2)
        return 999.0
