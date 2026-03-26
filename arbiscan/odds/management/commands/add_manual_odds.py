from django.core.management.base import BaseCommand
from odds.models import Fixture, BookmakerOdds


class Command(BaseCommand):
    help = "Manually add bookmaker odds (Betika, Sportpesa, etc.)"

    def add_arguments(self, parser):
        parser.add_argument("--fixture-id", type=int,   default=None)
        parser.add_argument("--book",       type=str,   default=None)
        parser.add_argument("--market",     type=str,   default="FT_1X2",
                            choices=["FT_1X2","BTTS","OU25","OU15","OU35"])
        parser.add_argument("--home",  type=float, default=None)
        parser.add_argument("--draw",  type=float, default=None)
        parser.add_argument("--away",  type=float, default=None)
        parser.add_argument("--yes",   type=float, default=None)
        parser.add_argument("--no",    type=float, default=None)
        parser.add_argument("--over",  type=float, default=None)
        parser.add_argument("--under", type=float, default=None)
        parser.add_argument("--list",  action="store_true")

    def handle(self, *args, **options):
        if options["list"]:
            self._list_fixtures()
            return
        if not options["fixture_id"] or not options["book"]:
            self.stderr.write("Usage: --fixture-id <id> --book <name> --market <MKT> [odds]")
            return
        try:
            fixture = Fixture.objects.get(pk=options["fixture_id"])
        except Fixture.DoesNotExist:
            self.stderr.write(f"Fixture {options['fixture_id']} not found. Use --list")
            return
        mkt = options["market"]
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
            val = options.get(data_key)
            if val is None:
                self.stderr.write(f"Missing: --{data_key}")
                return
            kwargs[db_field] = val
            kwargs[f"{db_field}_label"] = label_val
        obj, created = BookmakerOdds.objects.update_or_create(
            fixture=fixture, bookmaker=options["book"], market=mkt, defaults=kwargs)
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{action}: {options['book'].upper()} | {mkt} | {fixture}"))
        self.stdout.write("Run: python manage.py scan_arbs")

    def _list_fixtures(self):
        qs = Fixture.objects.filter(status="upcoming").order_by("kickoff")[:30]
        self.stdout.write(f"\n  {'ID':<6} {'Date':<12} {'Match':<50} {'Tournament'}")
        self.stdout.write("  " + "-"*88)
        for f in qs:
            date = f.kickoff.strftime("%Y-%m-%d") if f.kickoff else "?"
            t    = f.tournament.name[:20] if f.tournament else "?"
            self.stdout.write(f"  {f.pk:<6} {date:<12} {f.home_team} vs {f.away_team:<42} {t}")
