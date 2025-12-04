from typing import Dict, Any

def profit_take_signal(stats: Dict[str, Any], profit_pct: float = 300.0):
    """
    stats: a single symbol stats dict (from portfolio.compute_stats)
    profit_pct: e.g., 300 -> means price >= avg_buy * (1 + 300/100) == 4x
    Returns: (bool_signal, suggested_qty_to_sell)
    """
    try:
        avg = stats.get("avg_buy")
        cur = stats.get("current_price")
        remaining = stats.get("remaining_qty", 0)
        cost_basis = stats.get("cost_basis", 0)
        if avg and cur and remaining > 0:
            threshold = avg * (1 + profit_pct / 100.0)
            if cur >= threshold:
                # suggest selling enough to recover cost_basis: qty = cost_basis / cur
                qty = (cost_basis / cur) if cur > 0 else 0.0
                return True, min(qty, remaining)
    except Exception:
        pass
    return False, 0.0

def fear_buy_signal(fng_value: int, threshold: int = 20):
    return (fng_value is not None) and (fng_value <= threshold)
