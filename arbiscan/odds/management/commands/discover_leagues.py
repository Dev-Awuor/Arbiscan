import requests
from django.core.management.base import BaseCommand
from django.conf import settings

SPORT_IDS = {
    "football":    10,
    "tennis":      13,
    "basketball":  18,
    "cricket":     21,
    "rugby":       12,
    "ice_hockey":  17,
    "volleyball":  23,
    "baseball":    16,
    "handball":    24,
    "esports":     151,
}

class Command(BaseCommand):
    help = "List all available tournaments per sport on OddsPapi"

    def add_arguments(self, parser):
        parser.add_argument("--sports", nargs="+", default=["football","tennis","basketball"])
        parser.add_argument("--min-fixtures", type=int, default=3)

    def handle(self, *args, **options):
        key = settings.ODDSPAPI_KEY

        for sport in options["sports"]:
            sid = SPORT_IDS.get(sport)
            if not sid:
                continue
            url = f"https://api.oddspapi.io/v4/tournaments?sportId={sid}&apiKey={key}"
            r   = requests.get(url, timeout=10)
            if r.status_code != 200:
                self.stdout.write(f"{sport}: HTTP {r.status_code}")
                continue

            data = r.json()
            leagues = [
                t for t in data
                if isinstance(t, dict)
                and (t.get("upcomingFixtures",0) + t.get("futureFixtures",0)) >= options["min_fixtures"]
            ]
            leagues.sort(key=lambda x: x.get("upcomingFixtures",0)+x.get("futureFixtures",0), reverse=True)

            self.stdout.write(f"\n{'='*55}")
            self.stdout.write(f"{sport.upper()}  {len(leagues)} leagues with {options['min_fixtures']} fixtures")
            self.stdout.write(f"{'='*55}")
            for t in leagues[:30]:
                total = t.get("upcomingFixtures",0) + t.get("futureFixtures",0)
                self.stdout.write(
                    f"  id={t['tournamentId']:<6} "
                    f"upcoming={t.get('upcomingFixtures',0):<5} "
                    f"{t.get('categoryName',''):<20} "
                    f"{t['tournamentName']}")

