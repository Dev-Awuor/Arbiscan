from django.core.management.base import BaseCommand
from odds.services.oddspapi import OddspapiClient
from django.conf import settings
import json

class Command(BaseCommand):
    help = "Print raw OddsPapi response for one fixture"

    def add_arguments(self, parser):
        parser.add_argument("--book",       default="1xbet")
        parser.add_argument("--league",     default="ucl")
        parser.add_argument("--fixture-id", default=None)

    def handle(self, *args, **options):
        client  = OddspapiClient()
        t_map   = settings.TOURNAMENT_MAP
        tid     = t_map[options["league"]][0]
        book    = options["book"]

        self.stdout.write(f"\nFetching raw: {book} / {options['league']} (tid={tid})\n")
        fixtures = client.get_odds_by_tournament(tid, book)

        if not isinstance(fixtures, list) or not fixtures:
            self.stdout.write("No data returned.")
            return

        # Pick the first fixture or the one specified
        fx = fixtures[0]
        for f in fixtures:
            if options["fixture_id"] and str(f.get("fixtureId")) == options["fixture_id"]:
                fx = f
                break

        fid  = fx.get("fixtureId")
        self.stdout.write(f"Fixture ID : {fid}")
        self.stdout.write(f"Start Time : {fx.get('startTime')}")

        book_odds = fx.get("bookmakerOdds", {})
        if book not in book_odds:
            self.stdout.write(f"Book '{book}' not in response. Available: {list(book_odds.keys())}")
            return

        bdata  = book_odds[book]
        markets = bdata.get("markets", {})
        self.stdout.write(f"\nMarket IDs available: {list(markets.keys())}\n")

        for mid, mdata in markets.items():
            outcomes = mdata.get("outcomes", {})
            self.stdout.write(f"  Market ID: {mid}")
            for oc_id, oc_data in outcomes.items():
                player = oc_data.get("players", {}).get("0", {})
                price  = player.get("price", "?")
                bk_oc  = player.get("bookmakerOutcomeId", "?")
                self.stdout.write(f"    oc_id={oc_id:<6} bookmakerOutcomeId={str(bk_oc):<10} price={price}")
            self.stdout.write("")
