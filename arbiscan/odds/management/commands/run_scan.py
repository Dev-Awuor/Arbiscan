from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Full pipeline: fetch OddsPapi + scrape Betika + scan arbs + report"

    def add_arguments(self, parser):
        parser.add_argument("--leagues",     nargs="+", default=["ucl","epl","laliga"])
        parser.add_argument("--bankroll",    type=float, default=10000)
        parser.add_argument("--top",         type=int,   default=20)
        parser.add_argument("--skip-betika", action="store_true")
        parser.add_argument("--visible",     action="store_true")

    def handle(self, *args, **options):
        self.stdout.write("\n" + "="*55)
        self.stdout.write("  ARBISCAN FULL PIPELINE")
        self.stdout.write("="*55 + "\n")

        # 1. Fetch OddsPapi
        self.stdout.write("\n[1/4] Fetching OddsPapi odds...")
        call_command("fetch_odds", leagues=options["leagues"])

        # 2. Scrape Betika
        if not options["skip_betika"]:
            self.stdout.write("\n[2/4] Scraping Betika...")
            call_command("scrape_betika",
                         visible=options["visible"],
                         max_matches=150)
        else:
            self.stdout.write("\n[2/4] Betika scrape skipped.")

        # 3. Scan arbs
        self.stdout.write("\n[3/4] Scanning for arbitrage...")
        call_command("scan_arbs", clear=True, bankroll=options["bankroll"])

        # 4. Report
        self.stdout.write("\n[4/4] Report:\n")
        call_command("arb_report", top=options["top"])
