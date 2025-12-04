import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .encryptor import load_store, save_store
from .portfolio import Portfolio
from .market_data import prices_coingecko, fetch_fear_greed
from .graphs import build_unrealized_bar, build_distribution_pie
from .thresholds import profit_take_signal, fear_buy_signal
from .top_wallets import get_whale_activity
from .config import REFRESH_SECONDS_DEFAULT, DEFAULT_QUOTE, PROFIT_PCT_DEFAULT
from .rtc import now_str

import threading
import time

class ChainGuardianApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chain Guardian Dashboard")
        self.geometry("1200x800")
        self.store = load_store()
        self.portfolio = Portfolio(self.store)
        self.refresh_seconds = int(self.store.get("settings", {}).get("refresh_seconds", REFRESH_SECONDS_DEFAULT))
        self._build_ui()
        self._start_refresh()

    def _build_ui(self):
        # Top summary bar
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=8, pady=8)

        self.summary_total = self._summary_card(top, "Total value", "$0.00")
        self.summary_24h = self._summary_card(top, "24h change", "—")
        self.summary_unreal = self._summary_card(top, "Unrealized P/L", "$0.00 (0.00%)")
        self.summary_fng = self._summary_card(top, "Fear & Greed", "—")

        top_controls = ttk.Frame(top)
        top_controls.pack(side=tk.RIGHT)
        ttk.Button(top_controls, text="Refresh", command=self.manual_refresh).pack(side=tk.LEFT, padx=6)
        ttk.Button(top_controls, text="Orders", command=self.manage_orders).pack(side=tk.LEFT)
        ttk.Button(top_controls, text="Addresses", command=self.manage_addresses).pack(side=tk.LEFT, padx=6)
        ttk.Button(top_controls, text="API Keys", command=self.manage_api_keys).pack(side=tk.LEFT)
        ttk.Button(top_controls, text="Settings", command=self.manage_settings).pack(side=tk.LEFT, padx=6)
        self.clock = ttk.Label(top_controls, text=now_str())
        self.clock.pack(side=tk.LEFT, padx=8)
        self._tick_clock()

        # Notebook
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Portfolio tab
        self.tab_portfolio = ttk.Frame(self.nb)
        self.nb.add(self.tab_portfolio, text="Portfolio")
        self._build_portfolio_tab(self.tab_portfolio)

        # Whale tab
        self.tab_whales = ttk.Frame(self.nb)
        self.nb.add(self.tab_whales, text="Whale Watch")
        self._build_whale_tab(self.tab_whales)

        # Orders tab
        self.tab_orders = ttk.Frame(self.nb)
        self.nb.add(self.tab_orders, text="Orders")
        self._build_orders_tab(self.tab_orders)

        # Status bar
        self.status = ttk.Label(self, text="Ready")
        self.status.pack(fill=tk.X)

    def _summary_card(self, parent, title, value):
        frm = ttk.Frame(parent, relief=tk.GROOVE, padding=8)
        frm.pack(side=tk.LEFT, padx=6)
        ttk.Label(frm, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w")
        lbl = ttk.Label(frm, text=value, font=("Segoe UI", 12))
        lbl.pack(anchor="w")
        return lbl

    def _build_portfolio_tab(self, parent):
        left = ttk.Frame(parent)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cols = ["asset","qty","avg_cost","cur_price","chg_24h","total_value","unreal_d","unreal_pct","exchange","note"]
        self.table = ttk.Treeview(left, columns=cols, show="headings")
        for c, w in zip(cols, [120,90,90,90,80,110,110,90,100,160]):
            self.table.heading(c, text=c.replace("_"," ").title(), command=lambda col=c: self._sort_table(col, False))
            self.table.column(c, width=w, anchor=tk.CENTER)
        self.table.pack(fill=tk.BOTH, expand=True)

        right = ttk.Frame(parent)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)

        ttk.Label(right, text="Portfolio distribution").pack(anchor="w")
        self.fig_pie = build_distribution_pie({})
        self.canvas_pie = FigureCanvasTkAgg(self.fig_pie, master=right)
        self.canvas_pie.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        ttk.Label(right, text="% Unrealized by asset").pack(anchor="w")
        self.fig_bar = build_unrealized_bar({})
        self.canvas_bar = FigureCanvasTkAgg(self.fig_bar, master=right)
        self.canvas_bar.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _build_whale_tab(self, parent):
        ttk.Label(parent, text="BTC/ETH Top 100 Whale Wallets (24h inflow/outflow)").pack(anchor="w", padx=6, pady=6)
        self.whale_text = tk.Text(parent, height=25)
        self.whale_text.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _build_orders_tab(self, parent):
        top = ttk.Frame(parent)
        top.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(top, text="Add Order", command=self.add_order).pack(side=tk.LEFT)
        ttk.Button(top, text="Delete Selected", command=self.delete_selected_order).pack(side=tk.LEFT, padx=6)

        cols = ["id","asset","side","amount","price","exchange","timestamp","note","status"]
        self.orders_tree = ttk.Treeview(parent, columns=cols, show="headings", height=18)
        for c in cols:
            self.orders_tree.heading(c, text=c.capitalize())
            self.orders_tree.column(c, width=120 if c!="note" else 220, anchor=tk.CENTER)
        self.orders_tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

    def _sort_table(self, col, reverse):
        data = [(self.table.set(k, col), k) for k in self.table.get_children("")]
        def parse(v):
            try:
                return float(str(v).replace("%","").replace("$","").replace(",",""))
            except:
                return str(v)
        data.sort(key=lambda t: parse(t[0]), reverse=reverse)
        for i, (_, k) in enumerate(data):
            self.table.move(k, "", i)
        self.table.heading(col, command=lambda: self._sort_table(col, not reverse))

    def _tick_clock(self):
        self.clock.config(text=now_str())
        self.after(1000, self._tick_clock)

    def add_order(self):
        dialog = OrderDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.portfolio.add_order(dialog.result)
            save_store(self.store)
            self.refresh_ui(force=True)

    def delete_selected_order(self):
        sel = self.orders_tree.selection()
        if not sel:
            return
        ids = []
        for item in sel:
            vals = self.orders_tree.item(item, "values")
            try:
                ids.append(int(vals[0]))
            except:
                pass
        if not ids:
            return
        self.store["orders"] = [o for o in self.store.get("orders", []) if int(o.get("id", -1)) not in ids]
        save_store(self.store)
        self.portfolio._reload()
        self.refresh_ui(force=True)

    def manage_addresses(self):
        top = tk.Toplevel(self)
        top.title("Manage Tracked Addresses")
        top.geometry("600x400")
        ttk.Label(top, text="Enter BTC addresses (one per line):").pack(anchor="w", padx=6, pady=(6,0))
        txt_btc = tk.Text(top, height=8)
        txt_btc.pack(fill=tk.X, padx=6)
        txt_btc.insert("1.0", "\n".join(self.store.get("tracked_addresses", {}).get("btc", [])))
        ttk.Label(top, text="Enter ETH addresses (one per line):").pack(anchor="w", padx=6, pady=(6,0))
        txt_eth = tk.Text(top, height=8)
        txt_eth.pack(fill=tk.X, padx=6)
        txt_eth.insert("1.0", "\n".join(self.store.get("tracked_addresses", {}).get("eth", [])))
        def save_addrs():
            btc_list = [l.strip() for l in txt_btc.get("1.0","end").splitlines() if l.strip()]
            eth_list = [l.strip() for l in txt_eth.get("1.0","end").splitlines() if l.strip()]
            self.store.setdefault("tracked_addresses", {})["btc"] = btc_list
            self.store.setdefault("tracked_addresses", {})["eth"] = eth_list
            save_store(self.store)
            top.destroy()
        ttk.Button(top, text="Save", command=save_addrs).pack(pady=8)

    def manage_api_keys(self):
        top = tk.Toplevel(self)
        top.title("API Keys")
        top.geometry("500x260")
        ttk.Label(top, text="Set API keys (JSON path: store['api_keys']). Currently used for future whale integrations.").pack(fill=tk.X, padx=6, pady=6)
        current = self.store.get("api_keys", {})
        txt = tk.Text(top, height=10)
        txt.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        import json
        try:
            txt.insert("1.0", json.dumps(current, indent=2))
        except Exception:
            txt.insert("1.0", "{}")
        def save_keys():
            try:
                data = json.loads(txt.get("1.0","end"))
                self.store["api_keys"] = data
                save_store(self.store)
                top.destroy()
            except Exception as e:
                messagebox.showerror("Invalid JSON", str(e))
        ttk.Button(top, text="Save", command=save_keys).pack(pady=6)

    def manage_settings(self):
        top = tk.Toplevel(self)
        top.title("Settings")
        top.geometry("400x220")
        s = self.store.get("settings", {})
        refresh = tk.StringVar(value=str(s.get("refresh_seconds", REFRESH_SECONDS_DEFAULT)))
        default_quote = tk.StringVar(value=s.get("default_quote", DEFAULT_QUOTE))
        profit_pct = tk.StringVar(value=str(s.get("profit_pct_to_take", PROFIT_PCT_DEFAULT)))

        frm = ttk.Frame(top); frm.pack(padx=8, pady=8, fill=tk.X)
        ttk.Label(frm, text="Refresh seconds").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=refresh, width=12).grid(row=0, column=1, pady=4)
        ttk.Label(frm, text="Default quote").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=default_quote, width=12).grid(row=1, column=1, pady=4)
        ttk.Label(frm, text="Profit % threshold").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(frm, textvariable=profit_pct, width=12).grid(row=2, column=1, pady=4)
        def save_settings():
            try:
                self.store.setdefault("settings", {})["refresh_seconds"] = int(refresh.get())
                self.store["settings"]["default_quote"] = default_quote.get().upper()
                self.store["settings"]["profit_pct_to_take"] = float(profit_pct.get())
                save_store(self.store)
                self.refresh_seconds = int(self.store["settings"]["refresh_seconds"])
                top.destroy()
                self.status.config(text="Settings saved")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        ttk.Button(top, text="Save", command=save_settings).pack(pady=6)

    def manual_refresh(self):
        threading.Thread(target=self._refresh, daemon=True).start()

    def _start_refresh(self):
        self._stop = False
        def loop():
            while not self._stop:
                try:
                    self._refresh()
                except Exception as e:
                    print("refresh error", e)
                    self.status.config(text=f"Refresh error: {e}")
                time.sleep(self.refresh_seconds)
        threading.Thread(target=loop, daemon=True).start()

    def _refresh(self):
        # reload
        self.store = load_store()
        self.portfolio.store = self.store
        self.portfolio._reload()
        df = self.portfolio.df

        bases = list({ (a.split("/")[0].upper() if "/" in a else a.upper()) for a in df["asset"].astype(str).unique() }) if not df.empty else []
        bases_lower = [b.lower() for b in bases]
        def provider(symbols_lower):
            data = prices_coingecko(symbols_lower)
            return data

        stats = self.portfolio.compute_stats(provider, default_quote=self.store.get("settings", {}).get("default_quote", DEFAULT_QUOTE))
        fng = fetch_fear_greed()
        whales = get_whale_activity(self.store)

        self.after(0, lambda: self._update_ui(stats, fng, whales))

    def _update_ui(self, stats, fng, whale_lines):
        # Portfolio table and summary
        for r in self.table.get_children():
            self.table.delete(r)

        total_value = 0.0
        total_unreal = 0.0
        for sym, s in stats.items():
            qty = s['remaining_qty'] or 0.0
            avg = s['avg_buy'] or 0.0
            cur = s['current_price'] or 0.0
            unreal_d = s['unrealized_value'] or 0.0
            unreal_pct = s['unrealized_pct'] or 0.0
            total = qty * cur
            total_value += total
            total_unreal += unreal_d
            chg = s.get("change_24h", None)
            chg_str = f"{chg:.2f}%" if isinstance(chg, (int,float)) else "—"

            signal, qty_to_sell = profit_take_signal(s, profit_pct=self.store.get("settings", {}).get("profit_pct_to_take", PROFIT_PCT_DEFAULT))
            note = f"Take-profit: sell {qty_to_sell:.6f}" if signal else ""

            self.table.insert("", "end", values=[
                sym, f"{qty:.6f}", f"{avg:.4f}", f"{cur:.4f}", chg_str,
                f"${total:,.2f}", f"${unreal_d:,.2f}", f"{unreal_pct:.2f}%", s.get("exchange","—"), note
            ])

        # Summary cards
        self.summary_total.config(text=f"${total_value:,.2f}")
        total_unreal_pct = (total_unreal / total_value * 100.0) if total_value else 0.0
        self.summary_unreal.config(text=f"${total_unreal:,.2f} ({total_unreal_pct:.2f}%)")
        self.summary_24h.config(text="—")  # aggregate 24h change requires historical; omitted here
        self.summary_fng.config(text=f"{fng.get('value','—')} ({fng.get('classification','—')})")

        # Charts
        fig_dist = build_distribution_pie(stats)
        self.canvas_pie.figure = fig_dist
        self.canvas_pie.draw()
        fig_bar = build_unrealized_bar(stats)
        self.canvas_bar.figure = fig_bar
        self.canvas_bar.draw()

        # Whales
        self.whale_text.delete("1.0", "end")
        self.whale_text.insert("1.0", "\n".join(whale_lines))

        self.status.config(text=f"Refreshed at {now_str()}")

    def manage_orders(self):
        self.nb.select(self.tab_orders)

class OrderDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add Order")
        self.result = None
        self._build()
        self.grab_set()

    def _build(self):
        frm = ttk.Frame(self)
        frm.pack(padx=8, pady=8)
        labels = [
            ("Asset (e.g., XRP/USDT)", "asset"),
            ("Side (buy/sell)", "side"),
            ("Amount", "amount"),
            ("Price", "price"),
            ("Exchange", "exchange"),
            ("Note", "note")
        ]
        self.vars = {}
        for i, (lab, key) in enumerate(labels):
            ttk.Label(frm, text=lab).grid(row=i, column=0, sticky="w", pady=4)
            v = tk.StringVar()
            ttk.Entry(frm, textvariable=v, width=40).grid(row=i, column=1, pady=4)
            self.vars[key] = v
        btn = ttk.Frame(self)
        btn.pack(fill=tk.X, padx=8, pady=(0,8))
        ttk.Button(btn, text="OK", command=self.on_ok).pack(side=tk.RIGHT)
        ttk.Button(btn, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=6)

    def on_ok(self):
        data = {k: v.get().strip() for k, v in self.vars.items()}
        if not data.get("asset") or not data.get("side") or not data.get("amount"):
            messagebox.showerror("Missing", "asset, side and amount required")
            return
        try:
            data["amount"] = float(data["amount"])
        except Exception:
            messagebox.showerror("Bad amount", "Amount must be numeric")
            return
        try:
            data["price"] = float(data.get("price") or 0.0)
        except Exception:
            data["price"] = 0.0
        self.result = data
        self.destroy()

def main():
    app = ChainGuardianApp()
    app.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), app.destroy()))
    app.mainloop()

if __name__ == "__main__":
    main()
