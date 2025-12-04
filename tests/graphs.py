import matplotlib.pyplot as plt

def build_unrealized_bar(stats: dict):
    labels = []
    vals = []
    for sym, s in stats.items():
        labels.append(sym)
        vals.append(s.get("unrealized_pct", 0.0))
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.barh(labels, vals, color=["#2ca02c" if v >= 0 else "#d62728" for v in vals])
    ax.set_xlabel("% unrealized")
    ax.set_ylabel("Asset")
    ax.grid(True, axis="x", linestyle="--", alpha=0.3)
    fig.tight_layout()
    return fig

def build_distribution_pie(stats: dict):
    labels = []
    sizes = []
    for sym, s in stats.items():
        qty = s.get("remaining_qty", 0.0) or 0.0
        cur = s.get("current_price", 0.0) or 0.0
        val = qty * cur
        if val > 0:
            labels.append(sym)
            sizes.append(val)
    fig, ax = plt.subplots(figsize=(4.5, 3.5))
    if sizes:
        ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.axis("equal")
    fig.tight_layout()
    return fig
