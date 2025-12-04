import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from .encryptor import load_store, save_store
from .portfolio import Portfolio
from .market_data import prices_coingecko, fetch_fear_greed
from .graphs import build_unrealized_bar
from .thresholds import profit_take_signal, fear_buy_signal
import threading
import time

REFRESH_SECONDS_DEFAULT = 30

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chain Guardian")
        self.geometry("1000x700")
        self.store = load_store()
        self.portfolio = Portfolio(self.store)
        self.refresh_seconds = int(self.store.get("settings", {}).get("refresh_seconds", REFRESH_SECONDS_DEFAULT))
        self._build_ui()
        self._start_refresh()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(top, text="Add Order", command=self.add_order).pack(side=tk.LEFT)
        ttk.Button(top, text="Manage Addresses", command=self.manage_addresses).pack(side=tk.LEFT, padx=6)
        ttk.Button(top, text="Manage API Keys", command=self.manage_api_keys).pack(side=tk.LEFT)
        ttk.Button(top, text="Refresh", command=self.manual_refresh).pack(side=tk.LEFT, padx=6)
        self.clock = ttk.Label(top, text="")
        self.clock.pack(side=tk.RIGHT)
        self.update_clock()

        # table of orders
        cols = ["id","asset","side","amount","price","exchange","timestamp","note","status"]
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=100, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # right panel for stats & chart
        bottom = ttk.Frame(self)
        bottom.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        self.stats = tk.Text(bottom, height=10)
        self.stats.pack(fill=tk.X)
        # chart
        self.figure = build_unrealized_bar({})
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.canvas = FigureCanvasTkAgg(self.figure, master=bottom)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.status = ttk.Label(self, text="Ready")
        self.status.pack(fill=tk.X)

    def update_clock(self):
        import datetime
        self.clock.config(text=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.after(1000, self.update_clock)

    def add_order(self):
        dialog = OrderDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.portfolio.add_order(dialog.result)
            save_store(self.store)
            self.refresh_ui()

    def manage_addresses(self):
        top = tk.Toplevel(self)
        top.title("Manage Tracked Addresses")
        top.geometry("600x400")
        txt = tk.Text(top)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert("1.0", "\n".join(self.store.get("tracked_addresses", {}).get("btc", [])))
        def save():
            btc_list = [l.strip() for l in txt.get("1.0", "end").splitlines() if l.strip()]
            self.store.setdefault("tracked_addresses", {})["btc"] = btc_list
            save_store(self.store)
            top.destroy()
        ttk.Button(top, text="Save", command=save).pack()

    def manage_api_keys(self):
        top = tk.Toplevel(self)
        top.title("API Keys (Etherscan / Blockchair / Exchanges)")
        top.geometry("600x240")
        label = ttk.Label(top, text="Set api keys in JSON format under store['api_keys'] or use CLI later.")
        label.pack(fill=tk.X, padx=6, pady=6)
        ttk.Button(top, text="Open folder for manual edit", command=lambda: messagebox.showinfo("Info", "Open ~/.chainguardian/store.enc via decryptor tool")).pack(pady=6)

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
                time.sleep(self.refresh_seconds)
        threading.Thread(target=loop, daemon=True).start()

    def _refresh(self):
        self.store = load_store()
        self.portfolio.store = self.store
        self.portfolio._reload()
        df = self.portfolio.df
        # get bases and fetch prices
        bases = list({ (a.split("/")[0].upper() if "/" in a else a.upper()) for a in df["asset"].astype(str).unique() }) if not df.empty else []
        price_data = {}
        if bases:
            try:
                price_data = prices_coingecko([b.lower() for b in bases])
            except Exception:
                price_data = {}
        stats = self.portfolio.compute_stats(lambda syms: price_data, default_quote=self.store.get("settings", {}).get("default_quote","USDT"))
        fng = fetch_fear_greed()
        # update ui
        self.after(0, lambda: self._update_ui(df, stats, fng))

    def _update_ui(self, df, stats, fng):
        # table
        for r in self.tree.get_children():
            self.tree.delete(r)
        for _, row in df.iterrows():
            vals = [str(row.get(c,"")) for c in ["id","asset","side","amount","price","exchange","timestamp","note","status"]]
            self.tree.insert("", "end", values=vals)
        # stats text
        self.stats.delete("1.0", "end")
        lines = [f"Fear&Greed value: {fng.get('value')} ({fng.get('classification')})", ""]
        for sym, s in stats.items():
            lines.append(f"{sym}: qty {s['remaining_qty']} avg {s['avg_buy'] or 0:.4f} cur {s['current_price'] or 0:.4f} unreal ${s['unrealized_value'] or 0:.2f} ({(s['unrealized_pct'] or 0):.2f}%)")
            # profit-take
            signal, qty = profit_take_signal(s, profit_pct=self.store.get("settings", {}).get("profit_pct_to_take",300.0))
            if signal:
                lines.append(f" TAKE-PROFIT SUGGESTION: sell {qty:.6f} to recover initial capital")
        self.stats.insert("1.0", "\n".join(lines))
        # chart
        fig = build_unrealized_bar(stats)
        self.canvas.figure = fig
        self.canvas.draw()
        self.status.config(text="Refreshed")

    def stop(self):
        self._stop = True

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
        labels = [("Asset (BTC/USDT)", "asset"), ("Side (buy/sell)", "side"), ("Amount", "amount"), ("Price", "price"), ("Exchange", "exchange"), ("Note","note")]
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
        except:
            data["price"] = 0.0
        self.result = data
        self.destroy()

def main():
    app = App()
    app.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), app.destroy()))
    app.mainloop()

if __name__ == "__main__":
    main()
