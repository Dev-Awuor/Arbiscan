import time
import requests
from django.conf import settings
from odds.services.cache import get_cached, set_cached

RATE_LIMIT_SLEEP = 4.0
MAX_RETRIES      = 3
BACKOFF_BASE     = 15
CACHE_TTL        = 3600   # 1 hour  odds dont change faster than this


class OddspapiClient:

    def __init__(self):
        self.api_key  = settings.ODDSPAPI_KEY
        self.base_url = "https://api.oddspapi.io/v4"
        self.session  = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, endpoint: str, params: dict, cache: bool = True) -> list | dict:
        params_with_key = {**params, "apiKey": self.api_key}

        # Check cache first
        if cache:
            cached = get_cached(endpoint, params, ttl_seconds=CACHE_TTL)
            if cached is not None:
                return cached

        url = f"{self.base_url}/{endpoint}"

        for attempt in range(MAX_RETRIES):
            time.sleep(RATE_LIMIT_SLEEP)
            try:
                r = self.session.get(url, params=params_with_key, timeout=20)

                if r.status_code == 200:
                    data = r.json()
                    if cache:
                        set_cached(endpoint, params, data)
                    return data

                if r.status_code == 429:
                    wait = BACKOFF_BASE * (2 ** attempt)
                    print(f"  [429] Rate limited. Waiting {wait}s (attempt {attempt+1}/{MAX_RETRIES})...")
                    time.sleep(wait)
                    continue

                if r.status_code in (400, 404):
                    return []

                r.raise_for_status()

            except requests.exceptions.Timeout:
                wait = BACKOFF_BASE * (2 ** attempt)
                print(f"  [Timeout] Retrying in {wait}s...")
                time.sleep(wait)
            except requests.exceptions.RequestException as e:
                print(f"  [Error] {e}")
                return []

        print(f"  [FAILED] {url} after {MAX_RETRIES} attempts")
        return []

    def get_odds_by_tournament(self, tournament_id, bookmaker: str) -> list:
        return self._get("odds-by-tournaments", {
            "tournamentIds": tournament_id,
            "bookmaker":     bookmaker,
            "oddsFormat":    "decimal",
        })

    def get_fixtures(self, tournament_id) -> list:
        return self._get("fixtures", {"tournamentId": tournament_id})

    def get_tournaments(self, sport_id) -> list:
        """List all tournaments for a sport (used by the interactive `arb`
        command to show currently-active events)."""
        data = self._get("tournaments", {"sportId": sport_id})
        return data if isinstance(data, list) else []

    def fetch_multi_book_odds(self, tournament_ids: list, bookmakers: list, debug: bool = False) -> dict:
        combined = {}
        for i, book in enumerate(bookmakers):
            if i > 0:
                import time as _t; _t.sleep(8.0)   # inter-book pause
            print("  [" + str(i+1) + "/" + str(len(bookmakers)) + "] Fetching " + book + "...")
            all_data = []
            for tid in tournament_ids:
                chunk = self._get("odds-by-tournaments", {
                    "tournamentIds": str(tid),
                    "bookmaker":     book,
                    "oddsFormat":    "decimal",
                })
                if isinstance(chunk, list):
                    all_data.extend(chunk)
            data = all_data
            if debug:
                print("    -> Got " + str(len(data)) + " records from " + book)

            if not isinstance(data, list):
                continue

            for fx in data:
                if not isinstance(fx, dict):
                    continue
                fid = fx.get("fixtureId")
                if not fid:
                    continue
                if fid not in combined:
                    combined[fid] = {
                        "fixtureId":     fid,
                        "tournamentId":  fx.get("tournamentId"),
                        "startTime":     fx.get("startTime"),
                        "bookmakerOdds": {},
                    }
                bk_odds = fx.get("bookmakerOdds", {})
                if book in bk_odds:
                    combined[fid]["bookmakerOdds"][book] = bk_odds[book]

        return combined

    def fetch_fixture_names(self, tournament_ids: list) -> dict:
        names = {}
        for tid in tournament_ids:
            try:
                for fx in self.get_fixtures(tid):
                    names[fx["fixtureId"]] = (
                        fx.get("participant1Name", "?"),
                        fx.get("participant2Name", "?"),
                    )
            except Exception as e:
                print(f"  WARNING names/{tid}: {e}")
        return names
