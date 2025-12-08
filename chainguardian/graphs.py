import plotly.express as px
import pandas as pd

def _stats_to_df(stats: dict) -> pd.DataFrame:
    rows = []
    for sym, s in stats.items():
        rows.append({
            "asset": sym,
            "qty": s.get("remaining_qty", 0.0) or 0.0,
            "avg_cost": s.get("avg_buy", 0.0) or 0.0,
            "cur_price": s.get("current_price", 0.0) or 0.0,
            "unrealized_value": s.get("unrealized_value", 0.0) or 0.0,
            "unrealized_pct": s.get("unrealized_pct", 0.0) or 0.0,
            "value": (s.get("remaining_qty", 0.0) or 0.0) * (s.get("current_price", 0.0) or 0.0)
        })
    return pd.DataFrame(rows)

def fig_distribution_pie(stats: dict):
    df = _stats_to_df(stats)
    if df.empty:
        return px.pie(values=[1], names=["No data"], title="Portfolio distribution")
    df["value"] = df["value"].astype(float)
    return px.pie(df, values="value", names="asset", title="Portfolio distribution")

def fig_unrealized_bar(stats: dict):
    df = _stats_to_df(stats)
    if df.empty:
        return px.bar(x=["No data"], y=[0], title="% Unrealized by asset")
    return px.bar(df, x="asset", y="unrealized_pct", title="% Unrealized by asset")
