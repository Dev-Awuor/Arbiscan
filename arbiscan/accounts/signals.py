from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Subscription


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_subscription(sender, instance, created, **kwargs):
    """Every user gets a free Subscription row on creation."""
    if created:
        Subscription.objects.get_or_create(user=instance)
