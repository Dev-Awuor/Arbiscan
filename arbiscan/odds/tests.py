from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import ArbitrageResult, Fixture
from .services.calculator import calc_stakes
from .services.engine import scan_fixture


class MathTests(TestCase):
    def test_calculator_two_way_arb(self):
        r = calc_stakes([2.10, 2.10], total_stake=10000)
        self.assertTrue(r["is_arb"])
        self.assertEqual([l["stake"] for l in r["per_leg"]], [5000.0, 5000.0])
        self.assertEqual(r["profit"], 500.0)

    def test_calculator_target_profit(self):
        r = calc_stakes([2.10, 2.10], target_profit=500)
        self.assertAlmostEqual(r["profit"], 500.0, delta=0.02)

    def test_engine_ou_uses_market_code_and_rejects_ghost_margin(self):
        hits = scan_fixture({
            "a": {"OU25": {"over": 2.10, "under": 1.80}},
            "b": {"OU25": {"over": 1.80, "under": 2.10}},
        })
        arbs = [h for h in hits if h["arb"]]
        self.assertEqual({h["market"] for h in arbs}, {"OU25"})
        # 20% "margin" is a data error, not an arb
        self.assertFalse(scan_fixture({"a": {"H2H": {"home": 3.0, "away": 1.1}},
                                       "b": {"H2H": {"home": 1.1, "away": 3.0}}}, near_miss_threshold=0))


class LiveFeedTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user("u", password="password123")

    def _arb(self, kickoff, pct):
        fx = Fixture.objects.create(fixture_id=str(kickoff) + str(pct), home_team="A",
                                    away_team="B", kickoff=kickoff)
        return ArbitrageResult.objects.create(
            fixture=fx, market="H2H", pair_label="A+B", books=["x", "y"], odds=[2.1, 2.1],
            stakes=[5000, 5000], payout=10500, profit=500, profit_pct=pct, arb_sum=0.9524)

    def test_login_required(self):
        self.assertEqual(self.client.get("/api/live/sure-bets/").status_code, 401)
        self.assertEqual(self.client.get("/api/stats/").status_code, 401)

    def test_hides_started_fixtures_ranks_all_margins(self):
        self.client.force_login(self.user)
        now = timezone.now()
        self._arb(now - timedelta(hours=1), 0.5)   # already kicked off
        self._arb(now + timedelta(hours=1), 0.5)
        self._arb(now + timedelta(hours=2), 4.0)   # no margin cap any more
        d = self.client.get("/api/live/sure-bets/?target=500").json()
        self.assertEqual(d["count"], 2)
        self.assertEqual([b["rank"] for b in d["sure_bets"]], [1, 2])
        st = self.client.get("/api/stats/").json()
        self.assertEqual((st["arbs"], st["best_margin"]), (2, 4.0))
        self.assertEqual(st["by_book"], [{"book": "x", "n": 2}, {"book": "y", "n": 2}])

    def test_bad_target(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/live/sure-bets/?target=abc").status_code, 400)


class PipelineTests(TestCase):
    def test_trim_keeps_only_scanned_markets(self):
        from .services.oddspapi import _keep_scanned_markets
        d = _keep_scanned_markets([{"bookmakerOdds": {"b": {"markets": {"101": 1, "999": 2}}}}])
        self.assertEqual(list(d[0]["bookmakerOdds"]["b"]["markets"]), ["101"])

    def test_fetch_save_upserts(self):
        from odds.management.commands.fetch_odds import Command
        from .models import BookmakerOdds

        def run(price):
            f = Fixture(fixture_id="f1", home_team="A", away_team="B", status="upcoming",
                        kickoff=timezone.now() + timedelta(days=1))
            f.api_tid = "17"
            o = BookmakerOdds(bookmaker="x", market="H2H", leg1=price, leg2=2.0,
                              leg1_label="Home", leg2_label="Away")
            Command()._save({"f1": f}, [("f1", o)])

        run(1.9)
        run(2.2)   # same keys: updates, no duplicates
        self.assertEqual(Fixture.objects.count(), 1)
        self.assertEqual(float(BookmakerOdds.objects.get().leg1), 2.2)
