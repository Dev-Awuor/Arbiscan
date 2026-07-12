from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from accounts.billing import get_provider


class Command(BaseCommand):
    help = "Grant premium access to a user (manual billing scaffold)"

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("--days", type=int, default=30)

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            self.stderr.write(f"No user '{options['username']}'.")
            return
        sub = get_provider().activate(user, days=options["days"], external_ref="cli")
        self.stdout.write(self.style.SUCCESS(
            f"{user.username} -> premium until {sub.expires_at:%Y-%m-%d %H:%M} "
            f"(is_premium={sub.is_premium})"))
