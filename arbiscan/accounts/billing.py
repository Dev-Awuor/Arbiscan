"""
Pluggable billing interface.

The app only knows about `BillingProvider`. Today the single implementation is
`ManualProvider` (premium granted by an admin / the grant_premium command). Real
providers - M-Pesa STK via Paystack/IntaSend, or Stripe - implement the same two
methods later without touching the rest of the codebase.
"""
from abc import ABC, abstractmethod
from datetime import timedelta

from django.utils import timezone

from .models import Subscription


class BillingProvider(ABC):
    name = "abstract"

    @abstractmethod
    def start_checkout(self, user, plan: str) -> dict:
        """Begin a purchase; return whatever the client needs (redirect URL,
        STK push ref, etc.). Real providers fill this in."""
        ...

    @abstractmethod
    def activate(self, user, days: int = 30, external_ref: str = "") -> Subscription:
        """Mark the user premium (called on successful payment/webhook)."""
        ...


class ManualProvider(BillingProvider):
    """No real charge - an operator grants access. Used for scaffolding/dev."""
    name = "manual"

    def start_checkout(self, user, plan: str = "premium") -> dict:
        return {
            "provider": self.name,
            "status": "manual",
            "message": "Payments not yet wired. An admin can grant premium access.",
        }

    def activate(self, user, days: int = 30, external_ref: str = "") -> Subscription:
        sub, _ = Subscription.objects.get_or_create(user=user)
        now = timezone.now()
        sub.tier = "premium"
        sub.status = "active"
        sub.provider = self.name
        sub.external_ref = external_ref
        sub.started_at = now
        sub.expires_at = now + timedelta(days=days)
        sub.save()
        return sub


def get_provider() -> BillingProvider:
    """Return the configured provider. Swap here when wiring M-Pesa/Stripe."""
    return ManualProvider()
