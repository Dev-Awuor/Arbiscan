from django.contrib import admin
from .models import Tournament, Fixture, BookmakerOdds, ArbitrageResult

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ["name","api_id","category"]

@admin.register(Fixture)
class FixtureAdmin(admin.ModelAdmin):
    list_display  = ["home_team","away_team","kickoff","status","tournament"]
    list_filter   = ["status","tournament"]
    search_fields = ["home_team","away_team"]

@admin.register(BookmakerOdds)
class BookmakerOddsAdmin(admin.ModelAdmin):
    list_display = ["fixture","bookmaker","market","leg1","leg2","leg3","source","fetched_at"]
    list_filter  = ["bookmaker","market","source"]

@admin.register(ArbitrageResult)
class ArbitrageResultAdmin(admin.ModelAdmin):
    list_display = ["fixture","market","profit_pct","books","is_high_odds","scanned_at"]
    list_filter  = ["market","is_high_odds"]
    ordering     = ["-profit_pct"]
