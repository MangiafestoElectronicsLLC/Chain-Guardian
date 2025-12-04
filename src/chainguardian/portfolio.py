import pandas as pd
from typing import Dict, Any
from datetime import datetime

DEFAULT_COLS = ["id","asset","side","amount","price","exchange","timestamp","note","status"]

class Portfolio:
    def __init__(self, store: Dict[str, Any]):
        self.store = store
        self._reload()

    def _reload(self):
        self.df = pd.DataFrame(self.store.get("orders", []))
        for c in DEFAULT_COLS:
            if c not in self.df.columns:
                self.df[c] = ""
        self.df["amount"] = pd.to_numeric(self.df["amount"], errors="coerce").fillna(0.0)
        self.df["price"] = pd.to_numeric(self.df["price"], errors="coerce").fillna(0.0)
        try:
            self.next_id = int(self.df["id"].astype(int).max()) + 1 if not self.df.empty else 1
        except Exception:
            self.next_id = 1

    def add_order(self, order: Dict[str, Any]):
        order = order.copy()
        order.setdefault("id", str(self.next_id))
        order.setdefault("timestamp", datetime.utcnow().isoformat())
        order.setdefault("status", "open")
        self.store.setdefault("orders", []).append(order)
        self.next_id += 1

    def save(self, save_fn):
        # save_fn should be encryptor.save_store
        save_fn(self.store)
        self._reload()

    def compute_stats(self, price_lookup_fn, default_quote="USDT"):
        """
        Returns mapping symbol -> stats dict including avg_buy, current_price, unrealized_pct, realized
        price_lookup_fn: callable(list_of_bases)->dict mapping lowercased base -> {'usd': price}
        """
        if self.df.empty:
            return {}
        d = self.df.copy()
        d["asset"] = d["asset"].astype(str)
        d["side"] = d["side"].astype(str).str.lower()
        d["amount"] = pd.to_numeric(d["amount"], errors="coerce").fillna(0.0)
        d["price"] = pd.to_numeric(d["price"], errors="coerce").fillna(0.0)

        def base_of(s):
            return s.split("/")[0].strip().upper() if "/" in s else s.strip().upper()

        groups = {}
        for _, row in d.iterrows():
            sym = row["asset"]
            base = base_of(sym)
            quote = sym.split("/")[1].upper() if "/" in sym else default_quote
            key = f"{base}/{quote}"
            if key not in groups:
                groups[key] = {"buys": [], "sells": [], "net": 0.0}
            amt = float(row["amount"])
            pr = float(row["price"]) if float(row["price"]) > 0 else None
            if row["side"].startswith("buy"):
                groups[key]["buys"].append({"amount": amt, "price": pr})
                groups[key]["net"] += amt
            else:
                groups[key]["sells"].append({"amount": amt, "price": pr})
                groups[key]["net"] -= amt

        bases = [k.split("/")[0] for k in groups.keys()]
        price_data = price_lookup_fn([b.lower() for b in bases]) if bases else {}
        price_map = {}
        for b in bases:
            entry = price_data.get(b.lower())
            price_map[b] = entry.get("usd") if isinstance(entry, dict) else None

        results = {}
        for key, data in groups.items():
            base = key.split("/")[0]
            buys = [dict(b) for b in data["buys"]]
            realized = 0.0
            for s in data["sells"]:
                qty = s["amount"]
                sell_price = s["price"] or 0.0
                while qty > 0 and buys:
                    lot = buys[0]
                    take = min(qty, lot["amount"])
                    realized += take * (sell_price - (lot["price"] or 0.0))
                    lot["amount"] -= take
                    qty -= take
                    if lot["amount"] <= 0:
                        buys.pop(0)
            remaining_qty = sum(b["amount"] for b in buys)
            cost_basis = sum((b["amount"] * (b["price"] or 0.0)) for b in buys)
            avg_buy = (cost_basis / remaining_qty) if remaining_qty > 0 else None
            current = price_map.get(base)
            unreal_val = None
            unreal_pct = None
            if current and avg_buy and remaining_qty > 0:
                unreal_val = (current - avg_buy) * remaining_qty
                unreal_pct = ((current - avg_buy) / avg_buy) * 100.0
            results[key] = {
                "base": base, "quote": key.split("/")[1],
                "net": data["net"], "remaining_qty": remaining_qty, "cost_basis": cost_basis,
                "avg_buy": avg_buy, "current_price": current, "unrealized_value": unreal_val,
                "unrealized_pct": unreal_pct, "realized": realized
            }
        return results
