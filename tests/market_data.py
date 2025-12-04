import requests
from typing import List, Dict
from .config import COINGECKO_TIMEOUT, FEAR_GREED_TIMEOUT

def prices_coingecko(bases: List[str]) -> Dict[str, dict]:
    """
    Returns: {base: {"price": float, "change_24h": float}}
    bases should be lowercase coin ids recognized by CoinGecko (e.g., "bitcoin", "ethereum", "xrp").
    Fallback: if a coin id fails, it won't crash; it just won't include that base.
    """
    if not bases:
        return {}

    # Map common symbols to CoinGecko ids
    map_id = {
        "btc": "bitcoin", "eth": "ethereum", "xrp": "ripple", "pol": "polygon", "usdt": "tether"
    }
    ids = []
    for b in bases:
        ids.append(map_id.get(b, b))

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(ids), "vs_currencies": "usd", "include_24hr_change": "true"}
    try:
        r = requests.get(url, params=params, timeout=COINGECKO_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        out = {}
        for b, cid in zip(bases, ids):
            if cid in data:
                out[b] = {
                    "price": float(data[cid].get("usd", 0.0)),
                    "change_24h": float(data[cid].get("usd_24h_change", 0.0))
                }
        return out
    except Exception:
        # Graceful fallback
        return {b: {"price": 0.0, "change_24h": None} for b in bases}

def fetch_fear_greed() -> dict:
    """
    Fetches Fear & Greed index from alternative.me.
    Returns example: {"value": "26", "classification": "Fear"}
    """
    url = "https://api.alternative.me/fng/"
    try:
        r = requests.get(url, timeout=FEAR_GREED_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        if "data" in j and j["data"]:
            d = j["data"][0]
            return {"value": d.get("value"), "classification": d.get("value_classification")}
        return {"value": None, "classification": None}
    except Exception:
        return {"value": None, "classification": None}
