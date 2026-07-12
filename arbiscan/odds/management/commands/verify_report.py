from django.core.management.base import BaseCommand
from odds.models import Report
from odds.services import reporting


class Command(BaseCommand):
    help = "Verify a report's authenticity (content hash + HMAC signature)"

    def add_arguments(self, parser):
        parser.add_argument("--id", required=True,
                            help="Report ID (full UUID or 8-char short id)")

    def handle(self, *args, **options):
        rid = options["id"].strip().lower()
        report = None
        for r in Report.objects.all():
            full = str(r.report_id).lower()
            if rid in (full, full[:8], full.replace("-", "")[:len(rid)]):
                report = r
                break
        if not report:
            self.stderr.write(f"No report matching '{rid}'.")
            return

        ok = reporting.verify(report)
        self.stdout.write(f"\nReport ID : {report.report_id}")
        self.stdout.write(f"Generated : {report.created_at:%Y-%m-%d %H:%M:%S %Z}")
        self.stdout.write(f"Sport     : {report.sport or '-'}   Arbs: {report.arb_count}")
        self.stdout.write(f"SHA-256   : {report.content_hash}")
        self.stdout.write(f"PDF       : {report.pdf_path or '-'}")
        if ok:
            self.stdout.write(self.style.SUCCESS(
                "\nAUTHENTIC - signature valid and snapshot intact (produced by this system)."))
        else:
            self.stdout.write(self.style.ERROR(
                "\nINVALID - hash/signature mismatch (tampered, or generated with a different key)."))
