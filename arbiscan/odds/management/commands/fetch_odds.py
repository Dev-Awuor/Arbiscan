from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime
from odds.models import Tournament, Fixture, BookmakerOdds
from odds.services.oddspapi import OddspapiClient
from odds.services.extractor import extract_all_markets, filter_consistent_books

MARKET_LEG_MAP = {
    "FT_1X2": [("leg1","home"),("leg2","draw"),("leg3","away")],
    "H2H":    [("leg1","home"),("leg2","away")],
    "BTTS":   [("leg1","yes"), ("leg2","no")],
    "OU25":   [("leg1","over"),("leg2","under")],
    "OU15":   [("leg1","over"),("leg2","under")],
    "OU35":   [("leg1","over"),("leg2","under")],
    "DC":     [("leg1","1x"), ("leg2","x2"), ("leg3","12")],
}
MARKET_LABELS = {
    "FT_1X2":("Home","Draw","Away"),
    "H2H":   ("Home","Away",""),
    "BTTS":  ("Yes","No",""),
    "OU25":  ("Over","Under",""),
    "OU15":  ("Over","Under",""),
    "OU35":  ("Over","Under",""),
    "DC":     ("1X","X2","12"),
}


class Command(BaseCommand):
    help = "Fetch live odds from OddsPapi and persist to database"

    def add_arguments(self, parser):
        parser.add_argument("--leagues",   nargs="+", default=["ucl","epl","laliga"],
                            help="League slugs, or all for everything in TOURNAMENT_MAP")
        parser.add_argument("--tids",      nargs="+", default=None,
                            help="Raw OddsPapi tournament IDs (used by the interactive "
                                 "arb command for live tennis/MMA events)")
        parser.add_argument("--from-file", action="store_true",
                            help="Load tournament IDs from .league_ids")
        parser.add_argument("--books",     nargs="+",
                            default=["pinnacle","bet365","1xbet","unibet"])
        parser.add_argument("--dry-run",   action="store_true")
        parser.add_argument("--debug",     action="store_true",
                            help="Print raw API response count per book")

    def handle(self, *args, **options):
        client  = OddspapiClient()
        leagues = options["leagues"]
        books   = options["books"]
        t_map   = settings.TOURNAMENT_MAP

        if options["tids"]:
            tid_list = [str(t) for t in options["tids"]]
            self.stdout.write("Using " + str(len(tid_list)) + " tournament IDs passed via --tids")

        elif options["from_file"]:
            try:
                with open(".league_ids") as f:
                    tid_list = [int(i) for i in f.read().strip().split(",") if i.strip()]
                self.stdout.write("Loaded " + str(len(tid_list)) + " league IDs from .league_ids")
            except FileNotFoundError:
                self.stderr.write("ERROR: .league_ids not found. Run: python manage.py discover_all_leagues --save")
                return

        elif "all" in leagues:
            tid_list = [v[0] for v in t_map.values()]
            self.stdout.write("Using all " + str(len(tid_list)) + " leagues from TOURNAMENT_MAP")

        else:
            tid_list = [t_map[l][0] for l in leagues if l in t_map]
            missing  = [l for l in leagues if l not in t_map]
            if missing:
                self.stderr.write("WARNING: Unknown slugs ignored: " + str(missing))

        if not tid_list:
            self.stderr.write("No valid leagues resolved. Aborting.")
            return

        self.stdout.write("\nFetching: " + str(len(tid_list)) + " tournaments x " + str(books))
        raw   = client.fetch_multi_book_odds(tid_list, books, debug=options["debug"])
        names = client.fetch_fixture_names(tid_list)
        self.stdout.write(f"Fixtures: {len(raw)}  Names: {len(names)}\n")

        skipped = 0
        fixtures, odds_rows = {}, []   # fixture_id -> Fixture ; (fixture_id, BookmakerOdds)

        for fid, fx in raw.items():
            home, away = names.get(fid, ("?","?"))
            if "?" in (home, away):
                skipped += 1
                continue

            # Extract odds per book
            raw_book_data = {}
            for book, bdata in fx["bookmakerOdds"].items():
                mkts = extract_all_markets(bdata)
                if mkts:
                    raw_book_data[book] = mkts

            # Remove books with reversed home/away from FT_1X2 only
            book_data = filter_consistent_books(raw_book_data) if len(raw_book_data) >= 2 else {}
            if len(book_data) < 2:
                skipped += 1
                continue

            if options["dry_run"]:
                ft_books = [b for b in book_data if "FT_1X2" in book_data[b]]
                ou_books = [b for b in book_data if "OU25"   in book_data[b]]
                self.stdout.write(
                    f"  [DRY] {home} vs {away:<32} "
                    f"FT:{ft_books}  OU:{ou_books}")
                continue

            fixtures[fid] = Fixture(
                fixture_id=fid, home_team=home, away_team=away, status="upcoming",
                kickoff=parse_datetime(fx["startTime"]) if fx.get("startTime") else None,
            )
            fixtures[fid].api_tid = str(fx.get("tournamentId", "?"))
            for book, mkts in book_data.items():
                for mkt_label, legs in mkts.items():
                    leg_map = MARKET_LEG_MAP.get(mkt_label, [])
                    labels  = MARKET_LABELS.get(mkt_label, ("","",""))
                    odds_rows.append((fid, BookmakerOdds(
                        bookmaker=book, market=mkt_label, is_active=True, source="oddspapi",
                        leg1=legs.get(leg_map[0][1]) if len(leg_map)>0 else None,
                        leg2=legs.get(leg_map[1][1]) if len(leg_map)>1 else None,
                        leg3=legs.get(leg_map[2][1]) if len(leg_map)>2 else None,
                        leg1_label=labels[0], leg2_label=labels[1],
                        leg3_label=labels[2] if len(labels)>2 else "",
                    )))

        if fixtures:
            self._save(fixtures, odds_rows)

        self.stdout.write(self.style.SUCCESS(
            f"\nSaved {len(fixtures)} fixtures, {len(odds_rows)} odds. Skipped: {skipped}"))

    @transaction.atomic
    def _save(self, fixtures, odds_rows):
        """Bulk upserts: a handful of queries instead of one per row."""
        tids = {f.api_tid for f in fixtures.values()}
        known = dict(Tournament.objects.filter(api_id__in=tids).values_list("api_id", "id"))
        Tournament.objects.bulk_create([
            Tournament(api_id=t, slug="", name=f"Tournament {t}", category="")
            for t in tids if t not in known])
        known = dict(Tournament.objects.filter(api_id__in=tids).values_list("api_id", "id"))
        for f in fixtures.values():
            f.tournament_id = known[f.api_tid]

        Fixture.objects.bulk_create(
            fixtures.values(), update_conflicts=True, unique_fields=["fixture_id"],
            update_fields=["tournament", "home_team", "away_team", "kickoff", "status", "updated_at"])
        ids = dict(Fixture.objects.filter(fixture_id__in=fixtures).values_list("fixture_id", "id"))
        for fid, o in odds_rows:
            o.fixture_id = ids[fid]
        BookmakerOdds.objects.bulk_create(
            [o for _, o in odds_rows], batch_size=500, update_conflicts=True,
            unique_fields=["fixture", "bookmaker", "market"],
            update_fields=["leg1", "leg2", "leg3", "leg1_label", "leg2_label", "leg3_label",
                           "is_active", "source", "fetched_at"])
