import requests
from typing import List

def _etherscan_balance(addr: str, api_key: str) -> float | None:
    """
    Returns ETH balance (in ETH) for an address using Etherscan, or None on error.
    """
    try:
        r = requests.get(
            "https://api.etherscan.io/api",
            params={"module":"account","action":"balance","address":addr,"tag":"latest","apikey":api_key},
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "1":
            wei = int(data.get("result", "0"))
            return wei / 1e18
    except Exception:
        pass
    return None

def _blockchair_balance_btc(addr: str) -> float | None:
    """
    Returns BTC balance (in BTC) via Blockchair (no key required for basic lookups).
    """
    try:
        r = requests.get(f"https://api.blockchair.com/bitcoin/dashboards/address/{addr}", timeout=10)
        r.raise_for_status()
        data = r.json()
        info = data.get("data", {}).get(addr, {}).get("address", {})
        sat = int(info.get("balance", 0))
        return sat / 1e8
    except Exception:
        pass
    return None

def get_whale_activity(store: dict) -> List[str]:
    """
    Produces lines describing balances for tracked BTC/ETH addresses.
    Uses Etherscan if api_keys['etherscan'] present; Blockchair for BTC.
    """
    lines = []
    tracked = store.get("tracked_addresses", {})
    api_keys = store.get("api_keys", {})
    etherscan_key = api_keys.get("etherscan")

    for addr in tracked.get("eth", []):
        bal = _etherscan_balance(addr, etherscan_key) if etherscan_key else None
        if bal is None:
            lines.append(f"ETH {addr[:8]}…: balance unavailable (add Etherscan key)")
        else:
            lines.append(f"ETH {addr[:8]}…: {bal:.4f} ETH")

    for addr in tracked.get("btc", []):
        bal = _blockchair_balance_btc(addr)
        if bal is None:
            lines.append(f"BTC {addr[:8]}…: balance unavailable")
        else:
            lines.append(f"BTC {addr[:8]}…: {bal:.6f} BTC")

    return lines
