from rest_framework.permissions import BasePermission


class IsPremium(BasePermission):
    """Allow only authenticated users with an active premium subscription."""
    message = "A premium subscription is required for live data. Upgrade to access."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        sub = getattr(user, "subscription", None)
        return bool(sub and sub.is_premium)
