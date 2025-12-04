import requests
from typing import Dict, List

COINGECKO_SIMPLE = "https://api.coingecko.com/api/v3/simple/price"
FNG_API = "https://api.alternative.me/fng/"

def prices_coingecko(ids: List[str]) -> Dict[str, dict]:
    """
    ids: list of coin ids (e.g., ['bitcoin','ethereum'])
    returns mapping id -> {'usd': price}
    """
    if not ids:
        return {}
    params = {"ids": ",".join(ids), "vs_currencies": "usd"}
    r = requests.get(COINGECKO_SIMPLE, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def fetch_fear_greed():
    try:
        r = requests.get(FNG_API, timeout=8)
        r.raise_for_status()
        d = r.json()
        if d.get("data"):
            entry = d["data"][0]
            return {"value": int(entry["value"]), "classification": entry["value_classification"]}
    except Exception:
        pass
    return {"value": None, "classification": "unknown"}
