from matplotlib.figure import Figure
from typing import Dict, List

def build_unrealized_bar(stats: Dict[str, dict]) -> Figure:
    fig = Figure(figsize=(6,3))
    ax = fig.add_subplot(111)
    syms = []
    vals = []
    for sym, s in stats.items():
        syms.append(sym)
        vals.append(s.get("unrealized_pct") or 0)
    if syms:
        bars = ax.bar(range(len(syms)), vals)
        ax.set_xticks(range(len(syms)))
        ax.set_xticklabels(syms, rotation=30, ha='right')
        ax.set_ylabel("% Unrealized")
        for b, v in zip(bars, vals):
            b.set_color("green" if v >= 0 else "red")
        ax.axhline(0, color="black", linewidth=0.6)
    else:
        ax.text(0.5, 0.5, "No positions", ha='center')
    fig.tight_layout()
    return fig
