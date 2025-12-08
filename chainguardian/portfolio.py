import pandas as pd
from collections import defaultdict

class Portfolio:
    def __init__(self, store: dict):
        self.store = store
        self._reload()

    def _reload(self):
        self.df = pd.DataFrame(self.store.get("orders", []))
        if not self.df.empty and "asset" in self.df.columns:
            self.df["asset"] = self.df["asset"].astype(str)

    def add_order(self, order: dict):
        self.store.setdefault("orders", []).append(order)

    def compute_stats(self, price_provider, default_quote="USD"):
        """
        Returns dict per base symbol:
        {
          'remaining_qty': float,
          'avg_buy': float,
          'current_price': float,
          'unrealized_value': float,
          'unrealized_pct': float,
          'change_24h': float|None,
          'exchange': str|None
        }
        """
        if self.df.empty:
            return {}

        # Aggregate by base (XRP/USDT -> XRP)
        agg = defaultdict(lambda: {"buys_qty": 0.0, "buys_cost": 0.0, "sells_qty": 0.0, "exchange": None})
        for _, row in self.df.iterrows():
            asset = str(row.get("asset","")).upper()
            base = asset.split("/")[0] if "/" in asset else asset
            side = str(row.get("side","")).lower()
            qty = float(row.get("amount", 0.0))
            price = float(row.get("price", 0.0))
            if side == "buy":
                agg[base]["buys_qty"] += qty
                agg[base]["buys_cost"] += qty * price
            elif side == "sell":
                agg[base]["sells_qty"] += qty
            if not agg[base]["exchange"] and row.get("exchange"):
                agg[base]["exchange"] = row.get("exchange")

        symbols = [s.lower() for s in agg.keys()]
        price_data = price_provider(symbols)

        stats = {}
        for base, a in agg.items():
            remaining_qty = max(0.0, a["buys_qty"] - a["sells_qty"])
            avg_buy = (a["buys_cost"] / a["buys_qty"]) if a["buys_qty"] > 0 else 0.0
            cur_price = float(price_data.get(base.lower(), {}).get("price", 0.0))
            chg_24h = price_data.get(base.lower(), {}).get("change_24h")
            unrealized_value = remaining_qty * (cur_price - avg_buy)
            unrealized_pct = ((cur_price - avg_buy) / avg_buy * 100.0) if avg_buy > 0 else 0.0

            stats[base] = {
                "remaining_qty": remaining_qty,
                "avg_buy": avg_buy,
                "current_price": cur_price,
                "unrealized_value": unrealized_value,
                "unrealized_pct": unrealized_pct,
                "change_24h": chg_24h,
                "exchange": a["exchange"]
            }
        return stats
