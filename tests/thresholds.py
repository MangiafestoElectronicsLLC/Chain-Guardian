def profit_take_signal(stat: dict, profit_pct: float = 300.0):
    """
    Decide if unrealized profit exceeds threshold.
    Returns (signal: bool, qty_to_sell: float).
    Strategy: if unrealized_pct >= profit_pct, suggest selling enough to recover initial capital.
    """
    unreal_pct = stat.get("unrealized_pct", 0.0) or 0.0
    qty = stat.get("remaining_qty", 0.0) or 0.0
    avg = stat.get("avg_buy", 0.0) or 0.0
    cur = stat.get("current_price", 0.0) or 0.0

    if qty <= 0 or avg <= 0 or cur <= 0:
        return (False, 0.0)

    if unreal_pct >= profit_pct:
        # target sell qty to recover cost basis
        cost_basis = qty * avg
        qty_to_sell = min(qty, cost_basis / cur)
        return (True, float(qty_to_sell))
    return (False, 0.0)

def fear_buy_signal(fng_value: float, threshold: float = 25.0):
    """
    Simple signal: consider buys when Fear & Greed is <= threshold.
    """
    try:
        val = float(fng_value)
    except Exception:
        return False
    return val <= threshold
