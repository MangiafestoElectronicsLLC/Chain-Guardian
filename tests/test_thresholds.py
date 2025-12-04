from chainguardian.thresholds import profit_take_signal
def test_threshold_signal():
    stats = {"avg_buy":100.0, "current_price":400.0, "remaining_qty":1.0, "cost_basis":100.0}
    sig, qty = profit_take_signal(stats, profit_pct=300.0)
    assert sig is True
    assert qty > 0
