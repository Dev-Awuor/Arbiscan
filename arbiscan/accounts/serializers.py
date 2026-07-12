from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Subscription


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email    = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, v):
        if User.objects.filter(username=v).exists():
            raise serializers.ValidationError("Username already taken.")
        return v

    def create(self, data):
        return User.objects.create_user(
            username=data["username"],
            email=data.get("email", ""),
            password=data["password"],
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    is_premium = serializers.BooleanField(read_only=True)

    class Meta:
        model  = Subscription
        fields = ["tier", "status", "is_premium", "provider", "started_at", "expires_at"]


class MeSerializer(serializers.ModelSerializer):
    subscription = SubscriptionSerializer(read_only=True)

    class Meta:
        model  = User
        fields = ["id", "username", "email", "subscription"]
