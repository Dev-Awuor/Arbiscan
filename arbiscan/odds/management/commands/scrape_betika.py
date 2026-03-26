from django.core.management.base import BaseCommand
from odds.models import Fixture, BookmakerOdds
from odds.services.betika_scraper import BetikaOdds, fuzzy_match

FIELD_MAP = {
    "FT_1X2": [("leg1","home","Home"),("leg2","draw","Draw"),("leg3","away","Away")],
    "H2H":    [("leg1","home","Home"),("leg2","away","Away")],
    "BTTS":   [("leg1","yes","Yes"),("leg2","no","No")],
    "OU25":   [("leg1","over","Over"),("leg2","under","Under")],
    "OU15":   [("leg1","over","Over"),("leg2","under","Under")],
    "OU35":   [("leg1","over","Over"),("leg2","under","Under")],
    "DC":     [("leg1","1X","1X"),("leg2","12","12"),("leg3","X2","X2")],
    "DNB":    [("leg1","home","Home"),("leg2","away","Away")],
    "HT_1X2": [("leg1","home","Home"),("leg2","draw","Draw"),("leg3","away","Away")],
    "SET1":   [("leg1","home","Home"),("leg2","away","Away")],
}


class Command(BaseCommand):
    help = "Scrape Betika odds across all sports and save for arb scanning"

    def add_arguments(self, parser):
        parser.add_argument("--sports",      nargs="+",
                            default=["football","tennis","basketball"])
        parser.add_argument("--max-matches", type=int, default=60)
        parser.add_argument("--visible",     action="store_true")
        parser.add_argument("--no-deep",     action="store_true",
                            help="Skip clicking into each match (faster, fewer markets)")
        parser.add_argument("--dry-run",     action="store_true")
        parser.add_argument("--threshold",   type=float, default=0.58)

    def handle(self, *args, **options):
        headless = not options["visible"]
        deep     = not options["no_deep"]

        self.stdout.write(f"\n[Betika] Sports: {options['sports']} | Deep: {deep}\n")

        scraper = BetikaOdds(headless=headless)
        raw     = scraper.scrape(
            sports=options["sports"],
            max_per_url=options["max_matches"],
            deep=deep,
        )

        if not raw:
            self.stdout.write(self.style.WARNING("No data scraped."))
            return

        self.stdout.write(f"\nScraped {len(raw)} total matches\n")

        fixtures    = list(Fixture.objects.filter(status="upcoming"))
        fixture_map = {f"{fx.home_team} vs {fx.away_team}": fx for fx in fixtures}
        all_keys    = list(fixture_map.keys())

        matched = saved = skipped = 0

        for betika_key, data in raw.items():
            match_key = fuzzy_match(betika_key, all_keys, threshold=options["threshold"])

            if not match_key:
                self.stdout.write(f"  NO MATCH : {betika_key}")
                skipped += 1
                continue

            fixture = fixture_map[match_key]
            matched += 1
            self.stdout.write(f"  MATCHED  : {betika_key:<45} -> {match_key}")

            if options["dry_run"]:
                for mkt, legs in data["markets"].items():
                    self.stdout.write(f"    {mkt:<12}: {legs}")
                continue

            for mkt_label, legs in data["markets"].items():
                mapping = FIELD_MAP.get(mkt_label)
                if not mapping:
                    continue
                kwargs = {"source":"manual","is_active":True,
                          "leg1_label":"","leg2_label":"","leg3_label":""}
                valid = True
                for db_field, data_key, label_val in mapping:
                    val = legs.get(data_key)
                    if val:
                        kwargs[db_field] = val
                        kwargs[f"{db_field}_label"] = label_val
                    else:
                        valid = False
                        break
                if not valid:
                    continue
                BookmakerOdds.objects.update_or_create(
                    fixture=fixture, bookmaker="betika", market=mkt_label,
                    defaults=kwargs)
                saved += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nMatched: {matched}  Saved: {saved} odds  Skipped: {skipped}"))
        if saved > 0 and not options["dry_run"]:
            self.stdout.write("Next: python manage.py scan_arbs --clear")
