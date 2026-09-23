from django.conf import settings

NEAR_MISS    = getattr(settings, "NEAR_MISS_THRESHOLD", 3.0)
ODDS_LEG_CAP = getattr(settings, "ODDS_LEG_CAP", 50.0)
MAX_MARGIN   = getattr(settings, "ARB_MAX_MARGIN", 0.15)


def _sane_odds(odds) -> bool:
    """Reject corrupted/ghost prices that fabricate fake arbs.
    Every leg must be a real decimal price (>1.0) and below the cap."""
    return all(o and 1.0 < float(o) <= ODDS_LEG_CAP for o in odds)


def check_2way(oA: float, oB: float) -> dict:
    s = 1/oA + 1/oB
    m = 1 - s
    return {"arb": s < 1.0, "sum": round(s,4), "margin": round(m,4),
            "profit_pct": round(m*100,3),
            "overround_pct": round((s-1)*100,3) if s >= 1 else 0}


def check_3way(o1: float, oX: float, o2: float) -> dict:
    s = 1/o1 + 1/oX + 1/o2
    m = 1 - s
    return {"arb": s < 1.0, "sum": round(s,4), "margin": round(m,4),
            "profit_pct": round(m*100,3),
            "overround_pct": round((s-1)*100,3) if s >= 1 else 0}


def compute_stakes(odds_list: list, bankroll: float = 10000) -> tuple:
    inv    = [1/o for o in odds_list]
    total  = sum(inv)
    stakes = [round(bankroll*(i/total), 2) for i in inv]
    payout = round(min(s*o for s, o in zip(stakes, odds_list)), 2)
    profit = round(payout - bankroll, 2)
    return stakes, payout, profit


def scan_fixture(book_data: dict, bankroll: float = 10000,
                 near_miss_threshold: float = NEAR_MISS) -> list:
    books = list(book_data.keys())
    hits  = []

    def add(market, pair, bks, odds):
        # Guard 1: every leg must be a sane price (kills corrupted/ghost odds).
        if not _sane_odds(odds):
            return
        r = check_3way(*odds) if len(odds) == 3 else check_2way(*odds)
        # Guard 2: an "arb" with an implausibly large margin is a data error,
        # not a real edge (real arbs are ~0.5-5%). Drop it.
        if r["arb"] and r["margin"] > MAX_MARGIN:
            return
        if r["arb"] or r["overround_pct"] < near_miss_threshold:
            sk, pay, prof = compute_stakes(odds, bankroll) if r["arb"] else ([], 0, 0)
            hits.append({"market":market,"pair":pair,"books":bks,"odds":odds,
                          "stakes":sk,"payout":pay,"profit_kes":prof, **r})

    # --- H2H 2-way cross-book (tennis, basketball, MMA): A from book1, B from book2 ---
    for bA in books:
        for bB in books:
            if bA == bB: continue
            a = book_data[bA].get("H2H",{}).get("home")
            b = book_data[bB].get("H2H",{}).get("away")
            if a and b:
                add("H2H","A+B",[bA,bB],[a,b])

    for bH in books:
        for bD in books:
            for bA in books:
                h = book_data[bH].get("FT_1X2",{}).get("home")
                d = book_data[bD].get("FT_1X2",{}).get("draw")
                a = book_data[bA].get("FT_1X2",{}).get("away")
                if h and d and a:
                    add("FT_1X2","H+D+A",[bH,bD,bA],[h,d,a])

    for bY in books:
        for bN in books:
            if bY == bN: continue
            y = book_data[bY].get("BTTS",{}).get("yes")
            n = book_data[bN].get("BTTS",{}).get("no")
            if y and n:
                add("BTTS","Yes+No",[bY,bN],[y,n])

    for mkt in ("OU25", "OU15", "OU35"):
        for bO in books:
            for bU in books:
                if bO == bU: continue
                ov = book_data[bO].get(mkt,{}).get("over")
                un = book_data[bU].get(mkt,{}).get("under")
                if ov and un:
                    add(mkt,"Ov+Un",[bO,bU],[ov,un])

    seen = {}
    for h in hits:
        k = (h["market"], tuple(sorted(set(h["books"]))))
        if k not in seen or h["margin"] > seen[k]["margin"]:
            seen[k] = h
    return sorted(seen.values(), key=lambda x: x["margin"], reverse=True)
