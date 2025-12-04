import requests
from typing import List, Dict

BLOCKCHAIR_API = "https://api.blockchair.com"
ETHERSCAN_API = "https://api.etherscan.io/api"

def fetch_eth_balance(address: str, apikey: str = None):
    params = {"module":"account","action":"balance","address":address,"tag":"latest"}
    if apikey:
        params["apikey"] = apikey
    r = requests.get(ETHERSCAN_API, params=params, timeout=8)
    r.raise_for_status()
    d = r.json()
    if d.get("status") == "1":
        return int(d.get("result", "0")) / 1e18
    return None

def fetch_btc_balance_blockchair(address: str):
    r = requests.get(f"{BLOCKCHAIR_API}/bitcoin/dashboards/address/{address}", timeout=8)
    r.raise_for_status()
    d = r.json()
    if "data" in d and address in d["data"]:
        try:
            sat = int(d["data"][address]["address"]["balance"])
            return sat / 1e8
        except Exception:
            return None
    return None

def top_addresses_blockchair(chain: str = "bitcoin", limit: int = 100) -> List[str]:
    # best-effort: public endpoints vary; advise user to supply list if this fails
    try:
        r = requests.get(f"{BLOCKCHAIR_API}/{chain}/addresses?limit={limit}", timeout=8)
        r.raise_for_status()
        d = r.json()
        if isinstance(d.get("data"), list):
            return [item.get("address") for item in d["data"] if item.get("address")]
    except Exception:
        pass
    return []
