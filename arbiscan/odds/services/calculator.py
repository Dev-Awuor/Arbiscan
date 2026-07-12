"""
Standalone arbitrage / stake calculator.

Pure computation - no database, no odds feed. Powers the FREE public calculator:
a user types in their own odds (2..N outcomes) and gets the exact stake split,
total outlay and guaranteed profit. Generalises the inverse-odds math used by
`engine.compute_stakes` to any number of outcomes and adds flexible sizing
(by total stake OR by target profit).
"""


def calc_stakes(odds, total_stake=None, target_profit=None):
    """
    odds          : list of decimal odds, one per mutually-exclusive outcome (len >= 2)
    total_stake   : size the book to this total outlay (KES), OR
    target_profit : size the book so a winning outcome nets this profit (arbs only)

    Returns a dict describing the bet. For a true arb (implied_sum < 1) the payout
    is identical on every outcome, so profit is guaranteed.
    """
    odds = [float(o) for o in odds]
    if len(odds) < 2:
        raise ValueError("Need at least 2 outcomes")
    if any(o <= 1.0 for o in odds):
        raise ValueError("Every odd must be greater than 1.0")

    inv         = [1.0 / o for o in odds]
    implied_sum = sum(inv)
    is_arb      = implied_sum < 1.0
    # Margin as a share of turnover (matches the rest of the system); ROI is the
    # return on the money actually staked.
    margin_pct  = round((1.0 - implied_sum) * 100, 4)
    roi_pct     = round((1.0 / implied_sum - 1.0) * 100, 4)

    # Decide bankroll (total stake).
    if target_profit is not None:
        if not is_arb:
            # No guaranteed profit possible; fall back to a nominal book so the
            # user still sees the (negative) economics.
            bankroll = float(total_stake) if total_stake else 1000.0
        else:
            # profit = bankroll * (1/implied_sum - 1)  ->  invert for bankroll
            bankroll = float(target_profit) / (1.0 / implied_sum - 1.0)
    elif total_stake is not None:
        bankroll = float(total_stake)
    else:
        bankroll = 1000.0

    stakes  = [round(bankroll * (i / implied_sum), 2) for i in inv]
    # Payout is identical across outcomes for a balanced book; report worst-case.
    payouts = [round(stakes[k] * odds[k], 2) for k in range(len(odds))]
    payout  = round(min(payouts), 2)
    profit  = round(payout - bankroll, 2)

    per_leg = [{
        "index":   k + 1,
        "odds":    round(odds[k], 4),
        "implied_pct": round(inv[k] * 100, 3),
        "stake":   stakes[k],
        "payout":  payouts[k],
    } for k in range(len(odds))]

    return {
        "outcomes":    len(odds),
        "implied_sum": round(implied_sum, 6),
        "is_arb":      is_arb,
        "margin_pct":  margin_pct,
        "roi_pct":     roi_pct,
        "overround_pct": round((implied_sum - 1.0) * 100, 4) if not is_arb else 0.0,
        "total_stake": round(bankroll, 2),
        "guaranteed_payout": payout,
        "profit":      profit,
        "per_leg":     per_leg,
    }
