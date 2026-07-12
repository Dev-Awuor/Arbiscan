from django.core.management.base import BaseCommand
from odds.models import ArbitrageResult, Report
from odds.services import reporting


class Command(BaseCommand):
    help = "Generate a timestamped, traceable PDF report from the current arbs"

    def add_arguments(self, parser):
        parser.add_argument("--target", type=float, default=500,
                            help="Profit each card is sized to yield (KES)")
        parser.add_argument("--sport",  default="")
        parser.add_argument("--market", default="",
                            help="Filter arbs by market (e.g. H2H, FT_1X2)")
        parser.add_argument("--books",  nargs="+", default=None)
        parser.add_argument("--top",    type=int, default=50)

    def handle(self, *args, **options):
        target = options["target"]
        qs = ArbitrageResult.objects.filter(
            is_valid=True, profit_pct__gt=0).order_by("-profit_pct")
        if options["market"]:
            qs = qs.filter(market=options["market"])
        arbs = list(qs[:options["top"]])
        if not arbs:
            self.stderr.write("No valid arbs to report. Run scan_arbs first.")
            return

        snapshot     = reporting.build_snapshot(arbs, target)
        total_profit = round(sum(r["profit"] for r in snapshot), 2)
        books = options["books"] or sorted({
            b for a in arbs
            for b in (a.books if isinstance(a.books, list) else [])
        })

        report = Report.objects.create(
            sport=options["sport"],
            market=options["market"] or arbs[0].market,
            target=target,
            bankroll=arbs[0].bankroll,
            books=books,
            arb_count=len(snapshot),
            total_profit=total_profit,
            snapshot=snapshot,
        )
        reporting.seal(report)                 # hash + signature (uses created_at)
        path = reporting.render_pdf(report)    # uses sealed fields for the QR
        report.pdf_path = path
        report.save(update_fields=["content_hash", "signature", "pdf_path"])

        self.stdout.write(self.style.SUCCESS(f"\nPDF report -> {path}"))
        self.stdout.write(f"  Report ID : {report.report_id}")
        self.stdout.write(f"  Arbs      : {report.arb_count}   Sized profit/card: KES {target:,.0f}")
        self.stdout.write(f"  Signature : {report.signature[:32]}...")
        self.stdout.write(f"  Verify    : python manage.py verify_report --id {report.short_id}")
