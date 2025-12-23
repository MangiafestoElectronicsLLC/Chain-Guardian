import streamlit as st
import pandas as pd
import json
from datetime import timedelta
import plotly.express as px
from chainguardian.storage import load_store, save_store
from chainguardian.portfolio import Portfolio
from chainguardian.market_data import prices_coingecko, fetch_fear_greed, historical_prices_coingecko, calculate_rsi, calculate_macd, calculate_sma, calculate_ema
from chainguardian.thresholds import profit_take_signal, fear_buy_signal
from chainguardian.top_wallets import get_whale_activity, get_top_btc_addresses, get_top_eth_addresses, get_top_xrp_addresses, get_top_bnb_addresses, get_top_ada_addresses, _blockchair_balance_btc, _blockchair_balance_eth, _blockchair_balance_xrp, _blockchair_balance_bnb, _blockchair_balance_ada
from chainguardian.graphs import fig_distribution_pie, fig_unrealized_bar
from chainguardian.config import DEFAULT_QUOTE, PROFIT_PCT_DEFAULT
from chainguardian.rtc import now_str

st.set_page_config(page_title="Chain Guardian", layout="wide")

# Profile selection
with st.sidebar.expander("👤 Profile", expanded=True):
    profile = st.sidebar.text_input("Profile name", value="default", help="Switch profiles to manage multiple users/portfolios")

# Load encrypted store
store = load_store(profile)

# Migrate to accounts structure if needed
if "accounts" not in store:
    store["accounts"] = {"main": {k: v for k, v in store.items() if k not in ["accounts"]}}
    save_store(store, profile)

accounts = store["accounts"]

# Account selection
account_options = list(accounts.keys())
if "main" not in account_options:
    account_options.insert(0, "main")
    accounts["main"] = {"orders": [], "tracked_addresses": {"btc": [], "eth": []}}

account = st.sidebar.selectbox("Account", account_options, index=0, help="Switch between different accounts/portfolios")

new_account = st.sidebar.text_input("New Account Name", help="Enter name to create a new account")
if st.sidebar.button("➕ Add Account") and new_account.strip():
    if new_account not in accounts:
        accounts[new_account] = {"orders": [], "tracked_addresses": {"btc": [], "eth": []}}
        store["accounts"] = accounts
        save_store(store, profile)
        st.sidebar.success(f"✅ Account '{new_account}' created")
        st.rerun()
    else:
        st.sidebar.error("Account already exists")

# Edit Account
edit_account_name = st.sidebar.text_input("Rename Account To", help="Enter new name to rename the selected account")
if st.sidebar.button("✏️ Rename Account") and edit_account_name.strip():
    if edit_account_name != account and edit_account_name not in accounts:
        accounts[edit_account_name] = accounts.pop(account)
        store["accounts"] = accounts
        save_store(store, profile)
        st.sidebar.success(f"✅ Account renamed to '{edit_account_name}'")
        st.rerun()
    elif edit_account_name == account:
        st.sidebar.info("Name is the same")
    else:
        st.sidebar.error("Account name already exists")

# Remove Account
if len(accounts) > 1:
    with st.sidebar.form("delete_account_form"):
        confirm_delete = st.checkbox("Confirm deletion of selected account")
        submitted = st.form_submit_button("🗑️ Delete Account")
        if submitted and confirm_delete:
            del accounts[account]
            store["accounts"] = accounts
            save_store(store, profile)
            st.sidebar.success(f"✅ Account '{account}' deleted")
            st.rerun()
else:
    st.sidebar.write("Cannot delete the only account")

account_data = accounts.get(account, {"orders": [], "tracked_addresses": {"btc": [], "eth": []}})

# Get assets from orders for custom thresholds
assets_from_orders = set()
for order in account_data.get("orders", []):
    asset = order.get("asset", "").split("/")[0].upper()
    assets_from_orders.add(asset)
assets_list = list(assets_from_orders)

portfolio = Portfolio(account_data)

# Sidebar: Settings
with st.sidebar.expander("⚙️ Settings", expanded=False):
    refresh_seconds = st.number_input(
        "Refresh seconds",
        min_value=10,
        max_value=3600,
        value=int(store.get("settings", {}).get("refresh_seconds", 60)),
        help="How often to refresh data (manual or via rerun)"
    )
    default_quote = st.text_input(
        "Default quote (e.g., USD)",
        value=store.get("settings", {}).get("default_quote", DEFAULT_QUOTE)
    ).upper()
    profit_pct = st.number_input(
        "Profit % threshold",
        min_value=10.0,
        max_value=1000.0,
        value=float(store.get("settings", {}).get("profit_pct_to_take", PROFIT_PCT_DEFAULT)),
        help="Trigger a profit-take suggestion"
    )

    # Custom thresholds per asset
    st.subheader("Custom Thresholds per Asset")
    custom_thresholds = account_data.get("custom_thresholds", {})
    updated = False
    for asset in assets_list:
        key = f"thresh_{asset}"
        current = custom_thresholds.get(asset, profit_pct)
        new_val = st.number_input(f"{asset} threshold %", min_value=10.0, max_value=1000.0, value=float(current), key=key)
        if new_val != current:
            custom_thresholds[asset] = new_val
            updated = True
    if updated:
        account_data["custom_thresholds"] = custom_thresholds
        accounts[account] = account_data
        store["accounts"] = accounts
        save_store(store, profile)

# Sidebar: API keys
# Removed - using free APIs now

# Sidebar: Manage addresses
# Moved to Status tab

st.title("🛡️ Chain Guardian - Crypto Portfolio Tracker")
st.caption(f"Refreshed at {now_str()}")

# Tabs
tab_dashboard, tab_portfolio, tab_whales, tab_orders, tab_signals, tab_markets, tab_status = st.tabs(["📊 Dashboard", "💼 Portfolio", "🐋 Whale Watch", "📝 Orders", "📈 Signals", "🌍 Markets", "ℹ️ Status"])

# Refresh controls
colR1, colR2 = st.columns([1,1])
if colR1.button("Refresh data", use_container_width=True):
    st.rerun()
colR2.write(f"Auto-refresh: set via sidebar ({refresh_seconds}s).")

# Data fetch
df = portfolio.df
bases = list({ (a.split("/")[0].split()[0].upper() if "/" in a else a.split()[0].upper()) for a in df["asset"].astype(str).unique() }) if not df.empty else []
bases_lower = [b.lower() for b in bases]

price_provider = lambda syms: prices_coingecko(syms, quote=default_quote)
stats = portfolio.compute_stats(price_provider, default_quote=default_quote)
fear_greed = fetch_fear_greed()
whale_lines = get_whale_activity(account_data)

# Add 7-day change for each asset
for sym in stats:
    hist = historical_prices_coingecko(sym, days=7, quote=default_quote.lower())
    if hist and len(hist) >= 2:
        start_price = hist[0][1]
        end_price = hist[-1][1]
        if start_price > 0:
            change_7d = (end_price - start_price) / start_price * 100
            stats[sym]['change_7d'] = change_7d
        else:
            stats[sym]['change_7d'] = None
    else:
        stats[sym]['change_7d'] = None

# Add longer term changes
for sym in stats:
    # 30d
    hist = historical_prices_coingecko(sym, days=30, quote=default_quote.lower())
    if hist and len(hist) >= 2:
        start_price = hist[0][1]
        end_price = hist[-1][1]
        if start_price > 0:
            change_30d = (end_price - start_price) / start_price * 100
            stats[sym]['change_30d'] = change_30d
        else:
            stats[sym]['change_30d'] = None
    else:
        stats[sym]['change_30d'] = None
    # 90d
    hist = historical_prices_coingecko(sym, days=90, quote=default_quote.lower())
    if hist and len(hist) >= 2:
        start_price = hist[0][1]
        end_price = hist[-1][1]
        if start_price > 0:
            change_90d = (end_price - start_price) / start_price * 100
            stats[sym]['change_90d'] = change_90d
        else:
            stats[sym]['change_90d'] = None
    else:
        stats[sym]['change_90d'] = None
    # 365d
    hist = historical_prices_coingecko(sym, days=365, quote=default_quote.lower())
    if hist and len(hist) >= 2:
        start_price = hist[0][1]
        end_price = hist[-1][1]
        if start_price > 0:
            change_365d = (end_price - start_price) / start_price * 100
            stats[sym]['change_365d'] = change_365d
        else:
            stats[sym]['change_365d'] = None
    else:
        stats[sym]['change_365d'] = None

# --- Dashboard tab ---
with tab_dashboard:
    st.header("📊 Portfolio Dashboard")
    
    # Summary metrics
    total_value = sum((s['remaining_qty'] or 0.0) * (s['current_price'] or 0.0) for s in stats.values())
    total_unreal = sum((s['unrealized_value'] or 0.0) for s in stats.values())
    total_unreal_pct = (total_unreal / total_value * 100.0) if total_value else 0.0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Portfolio Value", f"${total_value:,.2f}")
    with col2:
        st.metric("Unrealized P/L", f"${total_unreal:,.2f}", f"{total_unreal_pct:.2f}%")
    with col3:
        st.metric("Assets Tracked", len(stats))
    with col4:
        fg_value = fear_greed.get('value')
        fg_class = fear_greed.get('classification', '—')
        st.metric("Fear & Greed Index", f"{fg_value} ({fg_class})" if fg_value is not None else "—")
    
    st.divider()
    
    # Top holdings
    st.subheader("🏆 Top Holdings")
    if stats:
        top_holdings = sorted(stats.items(), key=lambda x: (x[1]['remaining_qty'] or 0) * (x[1]['current_price'] or 0), reverse=True)[:5]
        for sym, s in top_holdings:
            qty = s['remaining_qty'] or 0.0
            cur = s['current_price'] or 0.0
            value = qty * cur
            unreal = s['unrealized_value'] or 0.0
            st.metric(f"{sym.upper()}", f"${value:,.2f}", f"P/L: ${unreal:,.2f}")
    else:
        st.info("No holdings to display. Add some orders in the Portfolio tab.")
    
    # Recent activity
    st.subheader("📈 Recent Orders")
    orders_df = pd.DataFrame(account_data.get("orders", []))
    if not orders_df.empty:
        recent_orders = orders_df.tail(5).sort_values("timestamp", ascending=False)
        for _, row in recent_orders.iterrows():
            st.write(f"• {row['side'].upper()} {row['amount']} {row['asset']} @ ${row['price']} ({row['exchange']})")
    else:
        st.info("No recent orders.")

# --- Portfolio tab ---
with tab_portfolio:
    st.subheader("📊 Positions")
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
        chg_7d = s.get("change_7d")
        chg_7d_str = f"{chg_7d:.2f}%" if isinstance(chg_7d, (int,float)) else "—"
        signal, qty_to_sell = profit_take_signal(s, profit_pct=custom_thresholds.get(sym, profit_pct))
        if signal:
            proceeds = qty_to_sell * cur
            original_for_sold = qty_to_sell * avg
            profit_from_sold = proceeds - original_for_sold
            remaining_qty = qty - qty_to_sell
            remaining_value = remaining_qty * cur
            note = f"Sell {qty_to_sell:.6f} for ${proceeds:.2f} (recover ${original_for_sold:.2f} + ${profit_from_sold:.2f} profit), keep {remaining_qty:.6f} worth ${remaining_value:.2f}"
        else:
            note = ""
        table_rows.append({
            "asset": sym, "qty": qty, "avg_cost": avg, "cur_price": cur,
            "chg_24h": chg_str, "chg_7d": chg_7d_str, "total_value": total, "unreal_d": unreal_d,
            "unreal_pct": unreal_pct, "exchange": s.get("exchange","—"), "note": note
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True)

    st.subheader(" Charts")
    colA, colB = st.columns(2)
    with colA:
        st.plotly_chart(fig_distribution_pie(stats), use_container_width=True)
    with colB:
        st.plotly_chart(fig_unrealized_bar(stats), use_container_width=True)

    st.subheader("📈 Asset Price Charts")
    asset_options = list(stats.keys())
    selected_asset = st.selectbox("Select asset for price chart", asset_options, key="asset_chart")
    if selected_asset:
        hist = historical_prices_coingecko(selected_asset, days=30, quote=default_quote.lower())
        if hist:
            df_hist = pd.DataFrame(hist, columns=["timestamp", "price"])
            df_hist["date"] = pd.to_datetime(df_hist["timestamp"], unit="ms")
            fig = px.line(df_hist, x="date", y="price", title=f"{selected_asset.upper()} Price (30 days)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical data available for this asset")

    st.divider()
    st.subheader("⚖️ Portfolio Rebalancing")
    st.write("Set target allocations (%) for each asset. The tool will suggest buys/sells to reach these targets.")
    
    total_value = sum((s['remaining_qty'] or 0.0) * (s['current_price'] or 0.0) for s in stats.values())
    if total_value > 0:
        saved_targets = account_data.get("rebalance_targets", {})
        targets = {}
        cols = st.columns(len(stats))
        for i, (sym, s) in enumerate(stats.items()):
            with cols[i]:
                current_pct = ((s['remaining_qty'] or 0.0) * (s['current_price'] or 0.0) / total_value * 100) if total_value else 0
                default_target = saved_targets.get(sym, round(current_pct, 1))
                target = st.number_input(f"{sym.upper()} target %", min_value=0.0, max_value=100.0, value=default_target, step=1.0, key=f"target_{sym}")
                targets[sym] = target
        
        # Save targets
        if targets != saved_targets:
            account_data["rebalance_targets"] = targets
            accounts[account] = account_data
            store["accounts"] = accounts
            save_store(store, profile)
        
        total_target = sum(targets.values())
        if abs(total_target - 100.0) > 0.1:
            st.error(f"Targets must sum to 100%. Current sum: {total_target:.1f}%")
        else:
            st.subheader("Rebalancing Suggestions")
            suggestions = []
            for sym, target_pct in targets.items():
                s = stats[sym]
                current_value = (s['remaining_qty'] or 0.0) * (s['current_price'] or 0.0)
                target_value = total_value * (target_pct / 100.0)
                diff_value = target_value - current_value
                cur_price = s['current_price'] or 0.0
                if cur_price > 0:
                    diff_qty = diff_value / cur_price
                    if diff_qty > 0.000001:
                        suggestions.append(f"**{sym.upper()}**: Buy {diff_qty:.6f} units (${diff_value:.2f})")
                    elif diff_qty < -0.000001:
                        suggestions.append(f"**{sym.upper()}**: Sell {abs(diff_qty):.6f} units (${abs(diff_value):.2f})")
                    else:
                        suggestions.append(f"**{sym.upper()}**: Balanced")
                else:
                    suggestions.append(f"**{sym.upper()}**: No price data")
            
            for sug in suggestions:
                st.write(sug)
    else:
        st.info("No portfolio value to rebalance.")

# --- Whale tab ---
with tab_whales:
    st.subheader("🐋 BTC/ETH Top Addresses (tracked)")
    if whale_lines:
        st.text("\n".join(whale_lines))
    else:
        st.info("No whale activity to display. Add addresses in the sidebar.")

    st.divider()
    st.subheader("➕ Add Top Wallets")
    btc_top = st.text_area("Top BTC addresses (one per line)", height=100, help="Paste known top BTC wallet addresses here")
    eth_top = st.text_area("Top ETH addresses (one per line)", height=100, help="Paste known top ETH wallet addresses here")
    xrp_top = st.text_area("Top XRP addresses (one per line)", height=100, help="Paste known top XRP wallet addresses here")
    bnb_top = st.text_area("Top BNB addresses (one per line)", height=100, help="Paste known top BNB wallet addresses here")
    ada_top = st.text_area("Top ADA addresses (one per line)", height=100, help="Paste known top ADA wallet addresses here")
    if st.button("Add to Tracked"):
        btc_list = [l.strip() for l in btc_top.splitlines() if l.strip()]
        eth_list = [l.strip() for l in eth_top.splitlines() if l.strip()]
        xrp_list = [l.strip() for l in xrp_top.splitlines() if l.strip()]
        bnb_list = [l.strip() for l in bnb_top.splitlines() if l.strip()]
        ada_list = [l.strip() for l in ada_top.splitlines() if l.strip()]
        account_data.setdefault("tracked_addresses", {})
        account_data["tracked_addresses"].setdefault("btc", []).extend(btc_list)
        account_data["tracked_addresses"].setdefault("eth", []).extend(eth_list)
        account_data["tracked_addresses"].setdefault("xrp", []).extend(xrp_list)
        account_data["tracked_addresses"].setdefault("bnb", []).extend(bnb_list)
        account_data["tracked_addresses"].setdefault("ada", []).extend(ada_list)
        # remove duplicates
        account_data["tracked_addresses"]["btc"] = list(set(account_data["tracked_addresses"]["btc"]))
        account_data["tracked_addresses"]["eth"] = list(set(account_data["tracked_addresses"]["eth"]))
        account_data["tracked_addresses"]["xrp"] = list(set(account_data["tracked_addresses"]["xrp"]))
        account_data["tracked_addresses"]["bnb"] = list(set(account_data["tracked_addresses"]["bnb"]))
        account_data["tracked_addresses"]["ada"] = list(set(account_data["tracked_addresses"]["ada"]))
        accounts[account] = account_data
        store["accounts"] = accounts
        save_store(store, profile)
        st.success("Added top wallets to tracked")
        st.rerun()

    st.divider()
    st.subheader("🤖 Auto-add Top Wallets")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("₿ Auto-add Top 100 BTC", use_container_width=True):
            top_btc = get_top_btc_addresses(100)
            if top_btc:
                account_data.setdefault("tracked_addresses", {})
                account_data["tracked_addresses"].setdefault("btc", []).extend(top_btc)
                account_data["tracked_addresses"]["btc"] = list(set(account_data["tracked_addresses"]["btc"]))
                accounts[account] = account_data
                store["accounts"] = accounts
                save_store(store, profile)
                st.success(f"Added {len(top_btc)} top BTC wallets")
                st.rerun()
            else:
                st.error("Failed to fetch top BTC wallets")
    with col2:
        if st.button("Ξ Auto-add Top 100 ETH", use_container_width=True):
            top_eth = get_top_eth_addresses(100)
            if top_eth:
                account_data.setdefault("tracked_addresses", {})
                account_data["tracked_addresses"].setdefault("eth", []).extend(top_eth)
                account_data["tracked_addresses"]["eth"] = list(set(account_data["tracked_addresses"]["eth"]))
                accounts[account] = account_data
                store["accounts"] = accounts
                save_store(store, profile)
                st.success(f"Added {len(top_eth)} top ETH wallets")
                st.rerun()
            else:
                st.error("Failed to fetch top ETH wallets")
    with col3:
        if st.button("💧 Auto-add Top 100 XRP", use_container_width=True):
            top_xrp = get_top_xrp_addresses(100)
            if top_xrp:
                account_data.setdefault("tracked_addresses", {})
                account_data["tracked_addresses"].setdefault("xrp", []).extend(top_xrp)
                account_data["tracked_addresses"]["xrp"] = list(set(account_data["tracked_addresses"]["xrp"]))
                accounts[account] = account_data
                store["accounts"] = accounts
                save_store(store, profile)
                st.success(f"Added {len(top_xrp)} top XRP wallets")
                st.rerun()
            else:
                st.error("Failed to fetch top XRP wallets")
    
    col4, col5, col6 = st.columns(3)
    with col4:
        if st.button("🟡 Auto-add Top 100 BNB", use_container_width=True):
            top_bnb = get_top_bnb_addresses(100)
            if top_bnb:
                account_data.setdefault("tracked_addresses", {})
                account_data["tracked_addresses"].setdefault("bnb", []).extend(top_bnb)
                account_data["tracked_addresses"]["bnb"] = list(set(account_data["tracked_addresses"]["bnb"]))
                accounts[account] = account_data
                store["accounts"] = accounts
                save_store(store, profile)
                st.success(f"Added {len(top_bnb)} top BNB wallets")
                st.rerun()
            else:
                st.error("Failed to fetch top BNB wallets")
    with col5:
        if st.button("₳ Auto-add Top 100 ADA", use_container_width=True):
            top_ada = get_top_ada_addresses(100)
            if top_ada:
                account_data.setdefault("tracked_addresses", {})
                account_data["tracked_addresses"].setdefault("ada", []).extend(top_ada)
                account_data["tracked_addresses"]["ada"] = list(set(account_data["tracked_addresses"]["ada"]))
                accounts[account] = account_data
                store["accounts"] = accounts
                save_store(store, profile)
                st.success(f"Added {len(top_ada)} top ADA wallets")
                st.rerun()
            else:
                st.error("Failed to fetch top ADA wallets")
    with col6:
        st.button("☀️ SOL Top Wallets (Coming Soon)", disabled=True, use_container_width=True)
        st.caption("Free SOL top holders API not available yet")

# --- Orders tab ---
with tab_orders:
    st.subheader("📝 Orders")
    orders_df = pd.DataFrame(account_data.get("orders", []))
    if orders_df.empty:
        st.info("No orders yet. Add one below.")
    else:
        st.dataframe(orders_df, use_container_width=True)

    st.divider()
    st.subheader("➕ Add Order")
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
                account_data.setdefault("orders", []).append({
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
                accounts[account] = account_data
                store["accounts"] = accounts
                save_store(store, profile)
                st.success("Order added")
                st.rerun()

    st.divider()
    st.subheader("🗑️ Delete Orders")
    if not orders_df.empty:
        ids = st.multiselect("Select IDs to delete", orders_df["id"].tolist())
        if st.button("Delete selected"):
            account_data["orders"] = [o for o in account_data.get("orders", []) if o.get("id") not in ids]
            accounts[account] = account_data
            store["accounts"] = accounts
            save_store(store, profile)
            st.success(f"Deleted {len(ids)} order(s)")
            st.rerun()

    st.divider()
    st.subheader("📥📤 Export/Import Orders")
    colE1, colE2 = st.columns(2)
    with colE1:
        if not orders_df.empty:
            csv = orders_df.to_csv(index=False)
            st.download_button("Download Orders as CSV", csv, "orders.csv", "text/csv", use_container_width=True)
    with colE2:
        uploaded_file = st.file_uploader("Upload Orders CSV", type="csv")
        if uploaded_file:
            try:
                new_orders = pd.read_csv(uploaded_file)
                # Validate columns
                required = ["asset", "side", "amount", "price"]
                if all(col in new_orders.columns for col in required):
                    for _, row in new_orders.iterrows():
                        store.setdefault("orders", []).append({
                            "id": int(pd.Timestamp.now().timestamp() + _),
                            "asset": row["asset"],
                            "side": row["side"],
                            "amount": float(row["amount"]),
                            "price": float(row["price"]),
                            "exchange": row.get("exchange", ""),
                            "timestamp": pd.Timestamp.utcnow().isoformat(),
                            "note": row.get("note", ""),
                            "status": "imported"
                        })
                    save_store(store, profile)
                    st.success("Orders imported successfully")
                    st.rerun()
                else:
                    st.error("CSV must have columns: asset, side, amount, price")
            except Exception as e:
                st.error(f"Import failed: {e}")

# --- Signals tab ---
with tab_signals:
    st.header("📈 Market Signals")
    
    # Fear & Greed Index Signals
    st.subheader("😨 Fear & Greed Index")
    fg_value = fear_greed.get('value')
    fg_class = fear_greed.get('classification', '—')
    st.metric("Current Index", f"{fg_value} ({fg_class})" if fg_value is not None else "—")
    
    if fg_value is not None and isinstance(fg_value, int):
        if fg_value <= 25:
            st.success("🟢 BUY OPPORTUNITY: Extreme Fear indicates market bottom")
        elif fg_value <= 45:
            st.info("🟡 CAUTION: Fear present, consider buying")
        elif fg_value <= 54:
            st.write("⚪ NEUTRAL: Balanced market sentiment")
        elif fg_value <= 75:
            st.warning("🟠 CAUTION: Greed present, consider selling")
        else:
            st.error("🔴 SELL OPPORTUNITY: Extreme Greed indicates market top")
    else:
        st.write("Fear & Greed data unavailable")
    
    st.write("**Fear & Greed Ranges:**")
    st.write("• 0-25: Extreme Fear (Strong BUY signal)")
    st.write("• 26-45: Fear (BUY opportunity)")
    st.write("• 46-54: Neutral (Hold)")
    st.write("• 55-75: Greed (SELL opportunity)")
    st.write("• 76-100: Extreme Greed (Strong SELL signal)")
    
    st.divider()
    
    # Profit Taking Alerts
    st.subheader("🚨 Profit Taking Alerts")
    alerts = []
    for sym, s in stats.items():
        qty = s['remaining_qty'] or 0.0
        avg = s['avg_buy'] or 0.0
        cur = s['current_price'] or 0.0
        signal, qty_to_sell = profit_take_signal(s, profit_pct=custom_thresholds.get(sym, profit_pct))
        if signal:
            proceeds = qty_to_sell * cur
            original_for_sold = qty_to_sell * avg
            profit_from_sold = proceeds - original_for_sold
            remaining_qty = qty - qty_to_sell
            remaining_value = remaining_qty * cur
            alert = f"**{sym.upper()}**: Sell {qty_to_sell:.6f} units for ${proceeds:.2f} (recovers ${original_for_sold:.2f} investment + ${profit_from_sold:.2f} profit). Keep {remaining_qty:.6f} coins worth ${remaining_value:.2f} for continued growth."
            alerts.append(alert)
    if alerts:
        for alert in alerts:
            st.warning(alert)
    else:
        st.info("No profit-taking opportunities at current thresholds")

    st.divider()
    st.subheader("📊 Technical Indicators")
    st.write("RSI, MACD, and Moving Averages for your portfolio assets (based on 100-day history).")
    
    indicator_data = []
    for sym in stats.keys():
        hist = historical_prices_coingecko(sym, days=100, quote=default_quote.lower())
        if hist and len(hist) > 50:  # Need enough data
            prices = [p[1] for p in hist]
            rsi = calculate_rsi(prices)
            macd, signal, histo = calculate_macd(prices)
            sma20 = calculate_sma(prices, 20)
            ema20 = calculate_ema(prices, 20)
            current_price = stats[sym]['current_price'] or 0.0
            indicator_data.append({
                "Asset": sym.upper(),
                "RSI (14)": f"{rsi:.1f}" if rsi else "—",
                "MACD": f"{macd:.6f}" if macd else "—",
                "Signal": f"{signal:.6f}" if signal else "—",
                "SMA (20)": f"${sma20:.2f}" if sma20 else "—",
                "EMA (20)": f"${ema20:.2f}" if ema20 else "—",
                "Current Price": f"${current_price:.2f}"
            })
    
    if indicator_data:
        df_indicators = pd.DataFrame(indicator_data)
        st.dataframe(df_indicators, use_container_width=True)
    else:
        st.info("Not enough historical data for indicators.")

# --- Markets tab ---
with tab_markets:
    st.header("🌍 Markets Overview")
    
    st.subheader("📈 Asset Price Changes")
    market_data = []
    for sym, s in stats.items():
        cur = s['current_price'] or 0.0
        chg_24h = s.get('change_24h')
        chg_7d = s.get('change_7d')
        chg_30d = s.get('change_30d')
        chg_90d = s.get('change_90d')
        chg_365d = s.get('change_365d')
        market_data.append({
            "Asset": sym.upper(),
            "Live Price": f"${cur:.2f}",
            "24h Change": f"{chg_24h:.2f}%" if isinstance(chg_24h, (int,float)) else "—",
            "7d Change": f"{chg_7d:.2f}%" if isinstance(chg_7d, (int,float)) else "—",
            "30d Change": f"{chg_30d:.2f}%" if isinstance(chg_30d, (int,float)) else "—",
            "90d Change": f"{chg_90d:.2f}%" if isinstance(chg_90d, (int,float)) else "—",
            "1y Change": f"{chg_365d:.2f}%" if isinstance(chg_365d, (int,float)) else "—",
            "All Time": "—"  # Placeholder, could fetch ATH if available
        })
    
    if market_data:
        df_market = pd.DataFrame(market_data)
        st.dataframe(df_market, use_container_width=True)
    else:
        st.info("No market data available.")
    
    st.divider()
    st.subheader("🔍 Search Asset")
    search_sym = st.text_input("Enter asset symbol (e.g., BTC, ETH, ADA)", key="search_sym").strip().upper()
    if search_sym:
        # Fetch price for searched asset
        try:
            price_data = prices_coingecko([search_sym.lower()], quote=default_quote)
            if search_sym.lower() in price_data:
                p = price_data[search_sym.lower()]
                st.metric(f"{search_sym} Price", f"${p['price']:.2f}", f"{p['change_24h']:.2f}%" if p['change_24h'] else "—")
                # Fetch longer changes
                hist_7d = historical_prices_coingecko(search_sym, days=7, quote=default_quote.lower())
                hist_30d = historical_prices_coingecko(search_sym, days=30, quote=default_quote.lower())
                hist_90d = historical_prices_coingecko(search_sym, days=90, quote=default_quote.lower())
                hist_365d = historical_prices_coingecko(search_sym, days=365, quote=default_quote.lower())
                
                changes = {}
                for label, hist, days in [("7d", hist_7d, 7), ("30d", hist_30d, 30), ("90d", hist_90d, 90), ("1y", hist_365d, 365)]:
                    if hist and len(hist) >= 2:
                        start_price = hist[0][1]
                        end_price = hist[-1][1]
                        if start_price > 0:
                            changes[label] = (end_price - start_price) / start_price * 100
                        else:
                            changes[label] = None
                    else:
                        changes[label] = None
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("7-Day Change", f"{changes['7d']:.2f}%" if changes['7d'] is not None else "—")
                with col2:
                    st.metric("30-Day Change", f"{changes['30d']:.2f}%" if changes['30d'] is not None else "—")
                with col3:
                    st.metric("90-Day Change", f"{changes['90d']:.2f}%" if changes['90d'] is not None else "—")
                with col4:
                    st.metric("1-Year Change", f"{changes['1y']:.2f}%" if changes['1y'] is not None else "—")
            else:
                st.error("Asset not found or no price data available.")
        except Exception as e:
            st.error(f"Error fetching data for {search_sym}: {e}")

# --- Status tab ---
with tab_status:
    st.subheader("ℹ️ App Status")
    st.write(f"Default quote: {default_quote}")
    st.write(f"Profit threshold: {profit_pct}%")
    st.write(f"Tracked BTC: {len(account_data.get('tracked_addresses', {}).get('btc', []))}")
    st.write(f"Tracked ETH: {len(account_data.get('tracked_addresses', {}).get('eth', []))}")
    st.write(f"Tracked XRP: {len(account_data.get('tracked_addresses', {}).get('xrp', []))}")
    st.write(f"Tracked BNB: {len(account_data.get('tracked_addresses', {}).get('bnb', []))}")
    st.write(f"Tracked ADA: {len(account_data.get('tracked_addresses', {}).get('ada', []))}")
    
    st.subheader("📍 Tracked Wallets")
    btc_tracked = account_data.get('tracked_addresses', {}).get('btc', [])
    eth_tracked = account_data.get('tracked_addresses', {}).get('eth', [])
    xrp_tracked = account_data.get('tracked_addresses', {}).get('xrp', [])
    bnb_tracked = account_data.get('tracked_addresses', {}).get('bnb', [])
    ada_tracked = account_data.get('tracked_addresses', {}).get('ada', [])
    if btc_tracked:
        st.write("**BTC Wallets:**")
        for addr in btc_tracked[:10]:
            st.code(addr, language=None)
        if len(btc_tracked) > 10:
            st.write(f"... and {len(btc_tracked) - 10} more")
    if eth_tracked:
        st.write("**ETH Wallets:**")
        for addr in eth_tracked[:10]:
            st.code(addr, language=None)
        if len(eth_tracked) > 10:
            st.write(f"... and {len(eth_tracked) - 10} more")
    if xrp_tracked:
        st.write("**XRP Wallets:**")
        for addr in xrp_tracked[:10]:
            st.code(addr, language=None)
        if len(xrp_tracked) > 10:
            st.write(f"... and {len(xrp_tracked) - 10} more")
    if bnb_tracked:
        st.write("**BNB Wallets:**")
        for addr in bnb_tracked[:10]:
            st.code(addr, language=None)
        if len(bnb_tracked) > 10:
            st.write(f"... and {len(bnb_tracked) - 10} more")
    if ada_tracked:
        st.write("**ADA Wallets:**")
        for addr in ada_tracked[:10]:
            st.code(addr, language=None)
        if len(ada_tracked) > 10:
            st.write(f"... and {len(ada_tracked) - 10} more")
    
    st.subheader("🐋 Top Tracked Wallets by Balance")
    top_wallets = []
    for coin, addrs in account_data.get('tracked_addresses', {}).items():
        for addr in addrs:
            if coin == "btc":
                bal = _blockchair_balance_btc(addr)
                unit = "BTC"
            elif coin == "eth":
                bal = _blockchair_balance_eth(addr)
                unit = "ETH"
            elif coin == "xrp":
                bal = _blockchair_balance_xrp(addr)
                unit = "XRP"
            elif coin == "bnb":
                bal = _blockchair_balance_bnb(addr)
                unit = "BNB"
            elif coin == "ada":
                bal = _blockchair_balance_ada(addr)
                unit = "ADA"
            else:
                continue
            if bal and bal > 0:
                top_wallets.append((f"{coin.upper()} {addr[:8]}…", bal, unit))
    
    if top_wallets:
        top_wallets.sort(key=lambda x: x[1], reverse=True)
        for name, bal, unit in top_wallets[:10]:
            st.metric(name, f"{bal:.4f} {unit}")
    else:
        st.info("No wallet balances available or tracked.")
    
    st.write("Note: This app is advisory-only. No auto-trading unless explicitly integrated.")
