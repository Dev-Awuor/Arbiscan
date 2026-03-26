from django.core.management.base import BaseCommand
from odds.services.oddspapi import OddspapiClient

class Command(BaseCommand):
    help = "List all available bookmakers on OddsPapi"

    def handle(self, *args, **options):
        client = OddspapiClient()
        try:
            data = client._get("bookmakers", {})
            if isinstance(data, list):
                self.stdout.write(f"\n{len(data)} bookmakers available:\n")
                for b in sorted(data, key=lambda x: x.get("name","").lower()):
                    self.stdout.write(f"  {b.get('slug','?'):<25} {b.get('name','?')}")
            else:
                self.stdout.write(str(data))
        except Exception as e:
            self.stdout.write(f"Error: {e}")
