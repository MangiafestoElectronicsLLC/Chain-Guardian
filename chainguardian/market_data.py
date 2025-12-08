import requests

def prices_coingecko(symbols_lower, quote="USD"):
    """
    Fetch prices and 24h change for base symbols via CoinGecko.
    symbols_lower: ['btc','eth','xrp'] (CoinGecko uses coin IDs; for simplicity we try symbol as ID fallback)
    Returns: { 'btc': {'price': float, 'change_24h': float}, ... }
    """
    out = {}
    if not symbols_lower:
        return out
    # Heuristic: treat symbols as IDs; for robust behavior, map symbols -> IDs. Keep it simple here.
    ids = ",".join(symbols_lower)
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ids, "vs_currencies": quote.lower(), "include_24hr_change": "true"},
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        for sym in symbols_lower:
            info = data.get(sym, {})
            price = info.get(quote.lower())
            chg = info.get(f"{quote.lower()}_24h_change")
            out[sym] = {"price": float(price) if price is not None else 0.0,
                        "change_24h": float(chg) if chg is not None else None}
    except Exception:
        for sym in symbols_lower:
            out[sym] = {"price": 0.0, "change_24h": None}
    return out

def fetch_fear_greed():
    """
    Fear & Greed Index via alternative.me API.
    """
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and data.get("data"):
            item = data["data"][0]
            return {"value": item.get("value"), "classification": item.get("value_classification")}
    except Exception:
        pass
    return {"value": "—", "classification": "Unavailable"}
