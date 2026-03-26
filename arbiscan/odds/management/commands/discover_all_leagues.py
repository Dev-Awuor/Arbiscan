import time
import requests
from django.core.management.base import BaseCommand
from django.conf import settings

# OddsPapi sport IDs  ordered by arb value (liquidity + bookmaker coverage)
SPORTS = {
    10: "Football",
    6:  "Tennis",
    7:  "Basketball",
    11: "American Football",
    8:  "Baseball",
    9:  "Ice Hockey",
    5:  "MMA/UFC",
    12: "Rugby Union",
    13: "Rugby League",
    14: "Cricket",
    15: "Volleyball",
    16: "Handball",
    17: "Snooker",
    18: "Darts",
    19: "Esports",
    20: "Boxing",
}

class Command(BaseCommand):
    help = "Discover all leagues across all sports, ranked by fixture count"

    def add_arguments(self, parser):
        parser.add_argument("--min-fixtures", type=int, default=5,
                            help="Only show leagues with at least N upcoming fixtures")
        parser.add_argument("--save", action="store_true",
                            help="Save ranked league IDs to .league_ids file for use in fetch_odds")
        parser.add_argument("--top", type=int, default=50,
                            help="How many top leagues to save/show")

    def handle(self, *args, **options):
        api_key = settings.ODDSPAPI_KEY
        min_fx  = options["min_fixtures"]
        top_n   = options["top"]
        all_leagues = []

        for sport_id, sport_name in SPORTS.items():
            time.sleep(2.0)
            try:
                r = requests.get(
                    "https://api.oddspapi.io/v4/tournaments",
                    params={"sportId": sport_id, "apiKey": api_key},
                    timeout=15
                )
                if r.status_code == 429:
                    self.stdout.write(f"  [429] {sport_name}  skipping")
                    time.sleep(30)
                    continue
                if r.status_code != 200:
                    continue

                tournaments = r.json()
                if not isinstance(tournaments, list):
                    continue

                for t in tournaments:
                    future = t.get("futureFixtures", 0) or 0
                    upcoming = t.get("upcomingFixtures", 0) or 0
                    live = t.get("liveFixtures", 0) or 0
                    total = future + upcoming + live

                    if total < min_fx:
                        continue

                    all_leagues.append({
                        "sport_id":   sport_id,
                        "sport":      sport_name,
                        "id":         t["tournamentId"],
                        "name":       t.get("tournamentName", "?"),
                        "category":   t.get("categoryName", "?"),
                        "fixtures":   total,
                    })

            except Exception as e:
                self.stdout.write(f"  ERROR {sport_name}: {e}")
                continue

        # Sort by fixture count descending (more fixtures = more arb opportunities)
        all_leagues.sort(key=lambda x: x["fixtures"], reverse=True)

        self.stdout.write(f"\n{'#':<4} {'Sport':<18} {'League':<35} {'Category':<20} {'ID':<10} {'Fixtures'}")
        self.stdout.write("-" * 100)

        for i, lg in enumerate(all_leagues[:top_n], 1):
            self.stdout.write(
                f"{i:<4} {lg['sport']:<18} {lg['name']:<35} {lg['category']:<20} {lg['id']:<10} {lg['fixtures']}"
            )

        if options["save"]:
            import requests as req
            api_key = settings.ODDSPAPI_KEY
            probe_books = ["pinnacle", "bet365", "1xbet"]
            min_book_coverage = 2
            verified = []

            self.stdout.write("\nProbing each league against " + probe_book + " for real odds coverage...")
            for lg in all_leagues[:top_n]:
                time.sleep(2.0)
                try:
                    books_with_coverage = []
                    for pb in probe_books:
                        time.sleep(1.5)
                        try:
                            r = req.get(
                                "https://api.oddspapi.io/v4/odds-by-tournaments",
                                params={
                                    "tournamentIds": lg["id"],
                                    "bookmaker":     pb,
                                    "oddsFormat":    "decimal",
                                    "apiKey":        api_key,
                                },
                                timeout=15
                            )
                            if r.status_code == 429:
                                self.stdout.write("  [429] Rate limited - waiting 30s...")
                                time.sleep(30)
                                continue
                            data = r.json() if r.status_code == 200 else []
                            if isinstance(data, list) and len(data) > 0:
                                books_with_coverage.append(pb)
                        except Exception:
                            continue
                    if len(books_with_coverage) >= min_book_coverage:
                        verified.append(lg)
                        self.stdout.write("  [YES] " + lg["sport"] + " / " + lg["name"] + " covered by: " + str(books_with_coverage))
                    else:
                        self.stdout.write("  [NO ] " + lg["sport"] + " / " + lg["name"] + " (only " + str(books_with_coverage) + ")")
                except Exception as e:
                    self.stdout.write("  [ERR] " + str(e))
                    continue

            ids = [str(lg["id"]) for lg in verified]
            with open(".league_ids", "w") as f:
                f.write(",".join(ids))
            self.stdout.write("\nVerified " + str(len(ids)) + " bookmaker-covered leagues saved to .league_ids")
            self.stdout.write("Run: python manage.py fetch_odds --from-file --books <books>")
