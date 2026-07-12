XBET_MAP = {"1": "home", "2": "draw", "3": "away"}

SEMANTIC_MAP = {
    "home":"home", "away":"away", "draw":"draw",
    "yes":"yes",   "no":"no",
    "gg":"yes",    "ng":"no",
    "w1":"home",   "w2":"away", "x":"draw",
    "9":"over",    "10":"under",
}

OC_BTTS_MAP = {"104":"yes", "105":"no"}

# Match-winner 2-way market (tennis / basketball / MMA). Outcome ids are stable:
# 123 = participant 1 (home), 124 = participant 2 (away). Some books (bet365) use
# opaque numeric bookmakerOutcomeIds, so we map by oc_id, not by bookmakerOutcomeId.
H2H_OC_MAP = {"123": "home", "124": "away"}

MARKET_ID_MAP = {
    "101":  "FT_1X2",
    "123":  "H2H",      # 2-way match winner (tennis/basketball/MMA)
    "104":  "BTTS",
    "1010": "OU25",
    "108":  "OU15",
    "1012": "OU35",
    "10216": "DC",      # bookmakerMarketId=20, 3 outcomes
    "10219": "DC",      # bookmakerMarketId=154, 3 outcomes (alt)
}

# DC outcome ID mapping: 388=1X, 390=X2, 389=12 (bm=20) | 475=1X, 476=X2, 477=12 (bm=154)
DC_OC_MAP = {
    "388": "1x", "390": "x2", "389": "12",   # bookmakerMarketId=20
    "475": "1x", "476": "x2", "477": "12",   # bookmakerMarketId=154
    "424": "1x", "425": "x2", "426": "12",   # bookmakerMarketId=27 (HT variant)
}

MARKET_EXPECTED_LEGS = {
    "FT_1X2": {"home","draw","away"},
    "BTTS":   {"yes","no"},
    "OU25":   {"over","under"},
    "OU15":   {"over","under"},
    "OU35":   {"over","under"},
    "DC":     {"1x","x2","12"},
    "H2H":    {"home","away"},
}


def extract_legs(mkts_block: dict, market_id: str) -> dict:
    mkt  = mkts_block.get(str(market_id), {})
    legs = {}
    for oc_id, oc_data in mkt.get("outcomes", {}).items():
        player = oc_data.get("players", {}).get("0", {})
        price  = player.get("price")
        if not price or float(price) >= 50:
            continue
        raw = str(player.get("bookmakerOutcomeId", "")).lower().strip()
        # H2H match-winner: map by stable oc_id so books with opaque numeric
        # bookmakerOutcomeIds (e.g. bet365) still resolve to home/away.
        if str(market_id) == "123" and str(oc_id) in H2H_OC_MAP:
            legs[H2H_OC_MAP[str(oc_id)]] = round(float(price), 3)
        elif raw in SEMANTIC_MAP:
            legs[SEMANTIC_MAP[raw]] = round(float(price), 3)
        elif raw in XBET_MAP:
            legs[XBET_MAP[raw]] = round(float(price), 3)
        elif raw in DC_OC_MAP:
            legs[DC_OC_MAP[raw]] = round(float(price), 3)
        elif "/" in raw:
            parts = raw.split("/")
            suffix = parts[-1].strip()
            if suffix in ("over","under"):
                legs[suffix] = round(float(price), 3)
            elif suffix in ("home","away","draw"):
                legs[suffix] = round(float(price), 3)
        else:
            btts = OC_BTTS_MAP.get(str(oc_id))
            if btts:
                legs[btts] = round(float(price), 3)
    return legs


def extract_all_markets(bookmaker_odds_block: dict) -> dict:
    if not bookmaker_odds_block.get("bookmakerIsActive"):
        return {}
    mkts   = bookmaker_odds_block.get("markets", {})
    result = {}
    for mid, mlabel in MARKET_ID_MAP.items():
        legs     = extract_legs(mkts, mid)
        expected = MARKET_EXPECTED_LEGS.get(mlabel, set())
        if expected.issubset(legs.keys()):
            result[mlabel] = {k: legs[k] for k in expected}
    return result


def get_majority_favorite(book_data: dict) -> str:
    """Return 'home' or 'away' based on what most books agree on."""
    votes = {"home": 0, "away": 0}
    for bv in book_data.values():
        ft = bv.get("FT_1X2", {})
        h, a = ft.get("home"), ft.get("away")
        if h and a:
            votes["home" if h < a else "away"] += 1
    return "home" if votes["home"] >= votes["away"] else "away"


def filter_consistent_books(book_data: dict) -> dict:
    """
    Drop FT_1X2 from any book that disagrees with the majority on which
    side is the favourite. This prevents fake arbs from reversed fixtures.
    Other markets (BTTS, O/U) are kept untouched.
    """
    if not book_data:
        return book_data
    majority_fav = get_majority_favorite(book_data)
    cleaned = {}
    for book, markets in book_data.items():
        ft = markets.get("FT_1X2", {})
        h, a = ft.get("home"), ft.get("away")
        if h and a:
            book_fav = "home" if h < a else "away"
            if book_fav != majority_fav:
                markets = {k: v for k, v in markets.items() if k != "FT_1X2"}
        if markets:
            cleaned[book] = markets
    return cleaned


def validate_consistency(book_data: dict) -> bool:
    return True
