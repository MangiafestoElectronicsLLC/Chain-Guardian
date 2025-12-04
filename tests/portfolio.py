import time
import pandas as pd

class Portfolio:
    def __init__(self, store: dict):
        self.store = store
        self.df = pd.DataFrame(self.store.get("orders", []))

    def _reload(self):
        self.df = pd.DataFrame(self.store.get("orders", []))

    def add_order(self, order: dict):
        # assign id and defaults
        order = dict(order)
        order.setdefault("id", int(time.time() * 1000))
        order.setdefault("status", "open")
        order.setdefault("timestamp", pd.Timestamp.now().isoformat())
        self.store.setdefault("orders", []).append(order)

    def compute_stats(self, price_provider, default_quote="USDT"):
        """
        Aggregates per asset symbol (e.g., XRP/USDT) with:
        remaining_qty, avg_buy, current_price, unrealized_value, unrealized_pct
        """
        if self.df.empty:
            return {}

        # Normalize and group by asset
        df = self.df.copy()
        df["asset"] = df["asset"].astype(str)
        df["side"] = df["side"].astype(str).str.lower()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)

        # Compute net positions and weighted averages per asset
        stats = {}
        for asset, g in df.groupby("asset"):
            buys = g[g["side"] == "buy"]
            sells = g[g["side"] == "sell"]

            buy_qty = buys["amount"].sum()
            sell_qty = sells["amount"].sum()
            remaining_qty = max(buy_qty - sell_qty, 0.0)

            # Weighted average buy price on buys only
            total_cost = (buys["amount"] * buys["price"]).sum()
            avg_buy = (total_cost / buy_qty) if buy_qty > 0 else 0.0

            # Determine base symbol (left of slash)
            base = asset.split("/")[0].upper() if "/" in asset else asset.upper()
            price_map = price_provider([base.lower()])
            pinfo = price_map.get(base.lower(), {})
            current_price = pinfo.get("price", None)
            change_24h = pinfo.get("change_24h", None)

            unrealized_value = (remaining_qty * current_price) - (remaining_qty * avg_buy) if (current_price is not None) else 0.0
            # Avoid division by zero
            cost_basis = remaining_qty * avg_buy
            unrealized_pct = ((unrealized_value / cost_basis) * 100.0) if cost_basis > 0 else 0.0

            stats[asset] = {
                "asset": asset,
                "remaining_qty": float(remaining_qty),
                "avg_buy": float(avg_buy),
                "current_price": float(current_price or 0.0),
                "change_24h": change_24h,
                "unrealized_value": float(unrealized_value),
                "unrealized_pct": float(unrealized_pct),
                "exchange": self._dominant_exchange(g)
            }
        return stats

    def _dominant_exchange(self, g):
        if "exchange" not in g.columns: return "—"
        counts = g["exchange"].fillna("—").value_counts()
        return counts.index[0] if not counts.empty else "—"
