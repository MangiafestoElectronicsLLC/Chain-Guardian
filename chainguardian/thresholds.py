from typing import Tuple

def profit_take_signal(stat: dict, profit_pct: float = 300.0) -> Tuple[bool, float]:
    """
    Returns (signal_bool, qty_to_sell).
    Default behavior: at >= profit_pct gain, suggest selling enough to withdraw principal.
    """
    qty = stat.get("remaining_qty", 0.0) or 0.0
    avg = stat.get("avg_buy", 0.0) or 0.0
    cur = stat.get("current_price", 0.0) or 0.0
    if avg <= 0 or qty <= 0 or cur <= 0:
        return (False, 0.0)
    pct = ((cur - avg) / avg) * 100.0
    if pct >= profit_pct:
        # Sell fraction so proceeds ~ original cost basis:
        # principal = qty * avg; sell_qty ~ principal / cur
        principal = qty * avg
        qty_to_sell = principal / cur
        qty_to_sell = min(qty_to_sell, qty)
        return (True, qty_to_sell)
    return (False, 0.0)

def fear_buy_signal(fng_value: str | int) -> bool:
    """
    Simple heuristic: buy when FNG <= 25 (Extreme Fear).
    """
    try:
        v = int(fng_value)
        return v <= 25
    except Exception:
        return False
