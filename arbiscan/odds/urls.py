from django.urls import path
from . import views

urlpatterns = [
    path("fixtures/",                      views.FixtureListView.as_view(),         name="fixture-list"),
    path("fixtures/<int:pk>/",             views.FixtureDetailView.as_view(),       name="fixture-detail"),
    path("fixtures/<int:pk>/scan/",        views.scan_fixture_view,                 name="fixture-scan"),
    path("fixtures/<int:pk>/manual-odds/", views.add_manual_odds_view,              name="manual-odds"),
    path("arbs/",                          views.ArbitrageResultListView.as_view(), name="arb-list"),
]
