from django.conf import settings

NEAR_MISS = getattr(settings, "NEAR_MISS_THRESHOLD", 3.0)


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
    payout = round(stakes[0]*odds_list[0], 2)
    profit = round(payout - bankroll, 2)
    return stakes, payout, profit


def scan_fixture(book_data: dict, bankroll: float = 10000,
                 near_miss_threshold: float = NEAR_MISS) -> list:
    books = list(book_data.keys())
    hits  = []

    def add(market, pair, bks, odds):
        r = check_3way(*odds) if len(odds) == 3 else check_2way(*odds)
        if r["arb"] or r["overround_pct"] < near_miss_threshold:
            sk, pay, prof = compute_stakes(odds, bankroll) if r["arb"] else ([], 0, 0)
            hits.append({"market":market,"pair":pair,"books":bks,"odds":odds,
                          "stakes":sk,"payout":pay,"profit_kes":prof, **r})

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

    for mkt, label in [("OU25","O/U 2.5"),("OU15","O/U 1.5"),("OU35","O/U 3.5")]:
        for bO in books:
            for bU in books:
                if bO == bU: continue
                ov = book_data[bO].get(mkt,{}).get("over")
                un = book_data[bU].get(mkt,{}).get("under")
                if ov and un:
                    add(label,"Ov+Un",[bO,bU],[ov,un])

    seen = {}
    for h in hits:
        k = (h["market"], tuple(sorted(set(h["books"]))))
        if k not in seen or h["margin"] > seen[k]["margin"]:
            seen[k] = h
    return sorted(seen.values(), key=lambda x: x["margin"], reverse=True)
