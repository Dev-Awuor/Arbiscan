from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path("register/",      views.register_view,          name="register"),
    path("token/",         TokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(),    name="token-refresh"),
    path("me/",            views.me_view,                 name="me"),
]
