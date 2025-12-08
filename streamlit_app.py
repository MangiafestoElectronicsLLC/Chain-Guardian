import streamlit as st
import pandas as pd
from datetime import timedelta
from chainguardian.storage import load_store, save_store
from chainguardian.portfolio import Portfolio
from chainguardian.market_data import prices_coingecko, fetch_fear_greed
from chainguardian.thresholds import profit_take_signal, fear_buy_signal
from chainguardian.top_wallets import get_whale_activity
from chainguardian.graphs import fig_distribution_pie, fig_unrealized_bar
from chainguardian.config import DEFAULT_QUOTE, PROFIT_PCT_DEFAULT
from chainguardian.rtc import now_str

st.set_page_config(page_title="Chain Guardian", layout="wide")

# Load encrypted store
store = load_store()
portfolio = Portfolio(store)

# Sidebar: Settings
st.sidebar.header("Settings")
refresh_seconds = st.sidebar.number_input(
    "Refresh seconds",
    min_value=10,
    max_value=3600,
    value=int(store.get("settings", {}).get("refresh_seconds", 60)),
    help="How often to refresh data (manual or via rerun)"
)
default_quote = st.sidebar.text_input(
    "Default quote (e.g., USD)",
    value=store.get("settings", {}).get("default_quote", DEFAULT_QUOTE)
).upper()
profit_pct = st.sidebar.number_input(
    "Profit % threshold",
    min_value=10.0,
    max_value=1000.0,
    value=float(store.get("settings", {}).get("profit_pct_to_take", PROFIT_PCT_DEFAULT)),
    help="Trigger a profit-take suggestion"
)

# Sidebar: API keys (JSON editor)
st.sidebar.header("API keys")
api_keys = store.get("api_keys", {})
api_keys_text = st.sidebar.text_area(
    "JSON (e.g., {\"etherscan\":\"KEY\",\"blockchair\":\"KEY\"})",
    value=pd.io.json.dumps(api_keys, indent=2),
    height=150
)
if st.sidebar.button("Save settings & API keys"):
    try:
        import json
        store.setdefault("settings", {})
        store["settings"]["refresh_seconds"] = int(refresh_seconds)
        store["settings"]["default_quote"] = default_quote
        store["settings"]["profit_pct_to_take"] = float(profit_pct)
        store["api_keys"] = json.loads(api_keys_text) if api_keys_text.strip() else {}
        save_store(store)
        st.sidebar.success("Saved settings and API keys")
    except Exception as e:
        st.sidebar.error(f"Failed to save: {e}")

# Sidebar: Manage addresses
st.sidebar.header("Tracked addresses")
btc_addrs = "\n".join(store.get("tracked_addresses", {}).get("btc", []))
eth_addrs = "\n".join(store.get("tracked_addresses", {}).get("eth", []))
btc_addrs_new = st.sidebar.text_area("BTC addresses (one per line)", value=btc_addrs, height=120)
eth_addrs_new = st.sidebar.text_area("ETH addresses (one per line)", value=eth_addrs, height=120)
if st.sidebar.button("Save addresses"):
    btc_list = [l.strip() for l in btc_addrs_new.splitlines() if l.strip()]
    eth_list = [l.strip() for l in eth_addrs_new.splitlines() if l.strip()]
    store.setdefault("tracked_addresses", {})["btc"] = btc_list
    store["tracked_addresses"]["eth"] = eth_list
    save_store(store)
    st.sidebar.success("Addresses saved")

st.title("Chain Guardian Dashboard")
st.caption(f"Refreshed at {now_str()}")

# Tabs
tab_portfolio, tab_whales, tab_orders, tab_status = st.tabs(["Portfolio", "Whale Watch", "Orders", "Status"])

# Refresh controls
colR1, colR2 = st.columns([1,1])
if colR1.button("Refresh data", use_container_width=True):
    st.experimental_rerun()
colR2.write(f"Auto-refresh: set via sidebar ({refresh_seconds}s).")

# Data fetch
df = portfolio.df
bases = list({ (a.split("/")[0].upper() if "/" in a else a.upper()) for a in df["asset"].astype(str).unique() }) if not df.empty else []
bases_lower = [b.lower() for b in bases]

price_provider = lambda syms: prices_coingecko(syms, quote=default_quote)
stats = portfolio.compute_stats(price_provider, default_quote=default_quote)
fear_greed = fetch_fear_greed()
whale_lines = get_whale_activity(store)

# --- Portfolio tab ---
with tab_portfolio:
    st.subheader("Summary")
    total_value = sum((s['remaining_qty'] or 0.0) * (s['current_price'] or 0.0) for s in stats.values())
    total_unreal = sum((s['unrealized_value'] or 0.0) for s in stats.values())
    total_unreal_pct = (total_unreal / total_value * 100.0) if total_value else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total value", f"${total_value:,.2f}")
    c2.metric("Unrealized P/L", f"${total_unreal:,.2f}", f"{total_unreal_pct:.2f}%")
    c3.metric("24h change", "—")  # aggregate needs history
    c4.metric("Fear & Greed", f"{fear_greed.get('value','—')} ({fear_greed.get('classification','—')})")

    st.subheader("Positions")
    table_rows = []
    for sym, s in stats.items():
        qty = s['remaining_qty'] or 0.0
        avg = s['avg_buy'] or 0.0
        cur = s['current_price'] or 0.0
        unreal_d = s['unrealized_value'] or 0.0
        unreal_pct = s['unrealized_pct'] or 0.0
        total = qty * cur
        chg = s.get("change_24h")
        chg_str = f"{chg:.2f}%" if isinstance(chg, (int,float)) else "—"
        signal, qty_to_sell = profit_take_signal(s, profit_pct=profit_pct)
        note = f"Take-profit: sell {qty_to_sell:.6f}" if signal else ""
        table_rows.append({
            "asset": sym, "qty": qty, "avg_cost": avg, "cur_price": cur,
            "chg_24h": chg_str, "total_value": total, "unreal_d": unreal_d,
            "unreal_pct": unreal_pct, "exchange": s.get("exchange","—"), "note": note
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

    st.subheader("Charts")
    colA, colB = st.columns(2)
    with colA:
        st.plotly_chart(fig_distribution_pie(stats), use_container_width=True)
    with colB:
        st.plotly_chart(fig_unrealized_bar(stats), use_container_width=True)

# --- Whale tab ---
with tab_whales:
    st.subheader("BTC/ETH Top Addresses (tracked)")
    if whale_lines:
        st.text("\n".join(whale_lines))
    else:
        st.info("No whale activity to display. Add addresses in the sidebar.")

# --- Orders tab ---
with tab_orders:
    st.subheader("Orders")
    orders_df = pd.DataFrame(store.get("orders", []))
    if orders_df.empty:
        st.info("No orders yet. Add one below.")
    else:
        st.dataframe(orders_df, use_container_width=True)

    st.divider()
    st.subheader("Add order")
    with st.form("add_order_form", clear_on_submit=True):
        asset = st.text_input("Asset (e.g., XRP/USDT)")
        side = st.selectbox("Side", ["buy","sell"])
        amount = st.number_input("Amount", min_value=0.0, step=0.000001, format="%.6f")
        price = st.number_input("Price", min_value=0.0, step=0.000001, format="%.6f")
        exchange = st.text_input("Exchange")
        note = st.text_input("Note")
        submitted = st.form_submit_button("Add order")
        if submitted:
            if not asset or not side or amount <= 0:
                st.error("asset, side and amount required")
            else:
                store.setdefault("orders", []).append({
                    "id": int(pd.Timestamp.now().timestamp()),
                    "asset": asset,
                    "side": side,
                    "amount": float(amount),
                    "price": float(price),
                    "exchange": exchange,
                    "timestamp": pd.Timestamp.utcnow().isoformat(),
                    "note": note,
                    "status": "recorded"
                })
                save_store(store)
                st.success("Order added")
                st.experimental_rerun()

    st.divider()
    st.subheader("Delete orders")
    if not orders_df.empty:
        ids = st.multiselect("Select IDs to delete", orders_df["id"].tolist())
        if st.button("Delete selected"):
            store["orders"] = [o for o in store.get("orders", []) if o.get("id") not in ids]
            save_store(store)
            st.success(f"Deleted {len(ids)} order(s)")
            st.experimental_rerun()

# --- Status tab ---
with tab_status:
    st.subheader("App status")
    st.write(f"Default quote: {default_quote}")
    st.write(f"Profit threshold: {profit_pct}%")
    st.write(f"Tracked BTC: {len(store.get('tracked_addresses', {}).get('btc', []))}")
    st.write(f"Tracked ETH: {len(store.get('tracked_addresses', {}).get('eth', []))}")
    st.write("Note: This app is advisory-only. No auto-trading unless explicitly integrated.")
