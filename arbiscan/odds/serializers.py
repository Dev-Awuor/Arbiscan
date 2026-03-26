from rest_framework import serializers
from .models import Tournament, Fixture, BookmakerOdds, ArbitrageResult


class TournamentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Tournament
        fields = ["id","api_id","slug","name","category"]


class BookmakerOddsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = BookmakerOdds
        fields = ["id","bookmaker","market","source","is_active",
                  "leg1","leg2","leg3","leg1_label","leg2_label","leg3_label","fetched_at"]


class FixtureSerializer(serializers.ModelSerializer):
    tournament = TournamentSerializer(read_only=True)
    odds       = BookmakerOddsSerializer(many=True, read_only=True)

    class Meta:
        model  = Fixture
        fields = ["id","fixture_id","tournament","home_team","away_team",
                  "kickoff","status","odds","updated_at"]


class ArbitrageResultSerializer(serializers.ModelSerializer):
    match   = serializers.SerializerMethodField()
    kickoff = serializers.SerializerMethodField()
    league  = serializers.SerializerMethodField()

    def get_match(self, obj):
        return f"{obj.fixture.home_team} vs {obj.fixture.away_team}"
    def get_kickoff(self, obj):
        return obj.fixture.kickoff
    def get_league(self, obj):
        return obj.fixture.tournament.name if obj.fixture.tournament else ""

    class Meta:
        model  = ArbitrageResult
        fields = ["id","match","kickoff","league","market","pair_label",
                  "books","odds","stakes","bankroll","payout","profit",
                  "profit_pct","arb_sum","is_high_odds","scanned_at"]
