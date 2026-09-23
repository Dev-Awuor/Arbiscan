import time
import requests
from django.conf import settings
from odds.services.cache import get_cached, set_cached
from odds.services.extractor import MARKET_ID_MAP

RATE_LIMIT_SLEEP = 4.0
MAX_RETRIES      = 3
BACKOFF_BASE     = 15
CACHE_TTL        = 3600   # fixtures / tournaments
TOURNAMENT_BATCH = 10     # ponytail: tournamentIds per odds call; docs show comma lists, max size undocumented
ODDS_CACHE_TTL   = 300    # prices: arbs close in minutes, and fetched_at (the scan freshness filter) is stamped at save time


class OddspapiClient:

    def __init__(self):
        self.api_key  = settings.ODDSPAPI_KEY
        self.base_url = "https://api.oddspapi.io/v4"
        self.session  = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, endpoint: str, params: dict, cache: bool = True, ttl: int = CACHE_TTL,
             shrink=None) -> list | dict:
        params_with_key = {**params, "apiKey": self.api_key}

        # Check cache first
        if cache:
            cached = get_cached(endpoint, params, ttl_seconds=ttl)
            if cached is not None:
                return cached

        url = f"{self.base_url}/{endpoint}"

        for attempt in range(MAX_RETRIES):
            time.sleep(RATE_LIMIT_SLEEP)
            try:
                r = self.session.get(url, params=params_with_key, timeout=20)

                if r.status_code == 200:
                    data = r.json()
                    if shrink:
                        data = shrink(data)
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
        }, ttl=ODDS_CACHE_TTL)

    def get_fixtures(self, tournament_id) -> list:
        return self._get("fixtures", {"tournamentId": tournament_id})

    def get_tournaments(self, sport_id) -> list:
        """List all tournaments for a sport (used by the interactive `arb`
        command to show currently-active events)."""
        data = self._get("tournaments", {"sportId": sport_id})
        return data if isinstance(data, list) else []

    def fetch_multi_book_odds(self, tournament_ids: list, bookmakers: list, debug: bool = False) -> dict:
        """One call per bookmaker per TOURNAMENT_BATCH tournaments (was one per
        bookmaker per tournament). Responses are trimmed to the markets we scan
        before caching - raw payloads carry ~100 markets per book (~1-2 MB)."""
        now = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        tids = [str(t) for t in tournament_ids]
        combined = {}
        for i, book in enumerate(bookmakers):
            print("  [" + str(i+1) + "/" + str(len(bookmakers)) + "] Fetching " + book + "...")
            data = []
            for k in range(0, len(tids), TOURNAMENT_BATCH):
                chunk = self._get("odds-by-tournaments", {
                    "tournamentIds": ",".join(tids[k:k + TOURNAMENT_BATCH]),
                    "bookmaker":     book,
                    "oddsFormat":    "decimal",
                }, ttl=ODDS_CACHE_TTL, shrink=_keep_scanned_markets)
                if isinstance(chunk, list):
                    data.extend(chunk)
            if debug:
                print("    -> Got " + str(len(data)) + " records from " + book)

            for fx in data:
                if not isinstance(fx, dict):
                    continue
                fid = fx.get("fixtureId")
                # Started fixtures can't be arbed pre-match; skip them early.
                if not fid or (fx.get("startTime") or "9") < now:
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


def _keep_scanned_markets(data):
    """Drop every market the extractor never reads."""
    if not isinstance(data, list):
        return data
    for fx in data:
        for b in (fx.get("bookmakerOdds") or {}).values():
            if isinstance(b, dict) and "markets" in b:
                b["markets"] = {k: v for k, v in b["markets"].items() if k in MARKET_ID_MAP}
    return data
