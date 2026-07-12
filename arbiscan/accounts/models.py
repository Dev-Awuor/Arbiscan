from django.conf import settings
from django.db import models
from django.utils import timezone


class Subscription(models.Model):
    """A user's access tier. Free by default; premium unlocks the live data feed.

    Billing is intentionally pluggable: `provider`/`external_ref` record which
    backend granted premium (manual for now; M-Pesa/Stripe later) without the
    rest of the app needing to know."""
    TIERS = [("free", "Free"), ("premium", "Premium")]
    STATUS = [("active", "Active"), ("expired", "Expired"), ("cancelled", "Cancelled")]

    user        = models.OneToOneField(settings.AUTH_USER_MODEL,
                                       on_delete=models.CASCADE,
                                       related_name="subscription")
    tier        = models.CharField(max_length=10, choices=TIERS, default="free")
    status      = models.CharField(max_length=10, choices=STATUS, default="active")
    provider    = models.CharField(max_length=30, blank=True)   # "manual" | "mpesa" | "stripe"
    external_ref= models.CharField(max_length=120, blank=True)  # provider txn/sub id
    started_at  = models.DateTimeField(null=True, blank=True)
    expires_at  = models.DateTimeField(null=True, blank=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} [{self.tier}/{self.status}]"

    @property
    def is_premium(self) -> bool:
        if self.tier != "premium" or self.status != "active":
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True
