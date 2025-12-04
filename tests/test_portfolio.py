from chainguardian.portfolio import Portfolio
def test_portfolio_basic():
    store = {"orders": [{"id":"1","asset":"BTC/USDT","side":"buy","amount":1.0,"price":100.0}], "settings":{}}
    p = Portfolio(store)
    stats = p.compute_stats(lambda syms: {"BTC":{"usd":400.0}})
    assert "BTC/USDT" in stats
    assert stats["BTC/USDT"]["avg_buy"] == 100.0
    assert stats["BTC/USDT"]["current_price"] == 400.0
