from typing import List

def get_whale_activity(store: dict) -> List[str]:
    """
    Displays tracked BTC/ETH addresses or Top-100 placeholders.
    If you later integrate Blockchair/Etherscan, replace this with real inflow/outflow logic.
    """
    lines = []
    tracked = store.get("tracked_addresses", {"btc": [], "eth": []})
    btc = tracked.get("btc", [])
    eth = tracked.get("eth", [])
    if btc or eth:
        lines.append("Tracked wallets:")
        for a in btc[:50]:
            lines.append(f"BTC | {a[:8]}... | activity: pending integration")
        for a in eth[:50]:
            lines.append(f"ETH | {a[:8]}... | activity: pending integration")
    else:
        lines.append("Top 100 whale wallets (demo):")
        lines.append("BTC | 1A1zP1e... | inflow: — | outflow: — | exchange: —")
        lines.append("ETH | 0x742d3... | inflow: — | outflow: — | exchange: —")
        lines.append("Add addresses via Addresses to enable live tracking.")
    return lines
