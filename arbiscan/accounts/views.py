from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from .billing import get_provider
from .serializers import RegisterSerializer, MeSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    ser = RegisterSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = ser.save()                       # signal creates the free Subscription
    refresh = RefreshToken.for_user(user)
    return Response({
        "user":    MeSerializer(user).data,
        "access":  str(refresh.access_token),
        "refresh": str(refresh),
    }, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me_view(request):
    return Response(MeSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout_view(request):
    """Begin an upgrade. Stubbed today (manual provider); the seam for M-Pesa/Stripe."""
    plan = request.data.get("plan", "premium")
    return Response(get_provider().start_checkout(request.user, plan))
