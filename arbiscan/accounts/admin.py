from django.contrib import admin
from django.utils import timezone

from .billing import get_provider
from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ("user", "tier", "status", "is_premium", "provider", "expires_at")
    list_filter   = ("tier", "status", "provider")
    search_fields = ("user__username", "user__email", "external_ref")
    actions       = ["grant_premium_30d", "revoke_premium"]

    @admin.display(boolean=True, description="Premium?")
    def is_premium(self, obj):
        return obj.is_premium

    @admin.action(description="Grant premium (30 days)")
    def grant_premium_30d(self, request, queryset):
        provider = get_provider()
        for sub in queryset:
            provider.activate(sub.user, days=30, external_ref="admin")
        self.message_user(request, f"Granted premium to {queryset.count()} user(s).")

    @admin.action(description="Revoke premium")
    def revoke_premium(self, request, queryset):
        queryset.update(tier="free", status="active", expires_at=timezone.now())
        self.message_user(request, "Revoked premium.")
