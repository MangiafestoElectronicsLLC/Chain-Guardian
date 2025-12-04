import pandas as pd, time

class Portfolio:
    def __init__(self, store): self.store, self.df = store, pd.DataFrame(store.get("orders", []))
    def _reload(self): self.df = pd.DataFrame(self.store.get("orders", []))
    def add_order(self, order):
        order = dict(order)
        order.setdefault("id", int(time.time()*1000))
        order.setdefault("status","open")
        self.store.setdefault("orders", []).append(order)

    def compute_stats(self, price_provider, default_quote="USDT"):
        if self.df.empty: return {}
        df = self.df.copy()
        df["side"] = df["side"].str.lower()
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
        stats = {}
        for asset,g in df.groupby("asset"):
            buys, sells = g[g["side"]=="buy"], g[g["side"]=="sell"]
            buy_qty, sell_qty = buys["amount"].sum(), sells["amount"].sum()
            remaining_qty = max(buy_qty-sell_qty,0.0)
            total_cost = (buys["amount"]*buys["price"]).sum()
            avg_buy = total_cost/buy_qty if buy_qty>0 else 0.0
            base = asset.split("/")[0].lower()
            price_map = price_provider([base])
            cur = price_map.get(base,{}).get("price",0.0)
            unrealized = remaining_qty*cur - remaining_qty*avg_buy
            cost_basis = remaining_qty*avg_buy
            unreal_pct = (unrealized/cost_basis*100.0) if cost_basis>0 else 0.0
            principal = total_cost
            realized = (sells["amount"]*sells["price"]).sum()
            stats[asset] = {"asset":asset,"remaining_qty":remaining_qty,"avg_buy":avg_buy,"current_price":cur,
                            "unrealized_value":unrealized,"unrealized_pct":unreal_pct,
                            "principal":principal,"realized":realized}
        return stats
