from django.core.management.base import BaseCommand
from playwright.sync_api import sync_playwright

class Command(BaseCommand):
    help = "Dump Betika row HTML to find correct selectors"

    def handle(self, *args, **options):
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=False, slow_mo=80)
            page = browser.new_context(
                viewport={"width":1366,"height":768},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                locale="en-KE"
            ).new_page()
            page.set_default_timeout(30000)
            page.goto("https://www.betika.com/en-ke/s/football/highlights",
                      wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 500)")
                page.wait_for_timeout(800)

            rows = page.locator(".prebet-match").all()
            self.stdout.write(f"Found {len(rows)} rows\n")
            if rows:
                html = rows[0].inner_html()
                with open("betika_row.html","w",encoding="utf-8") as f:
                    f.write(html)
                self.stdout.write("Saved: betika_row.html  open in VS Code to inspect")
            browser.close()
