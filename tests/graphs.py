import matplotlib.pyplot as plt

def build_unrealized_bar(stats):
    labels,vals=[],[]
    for sym,s in stats.items(): labels.append(sym); vals.append(s.get("unrealized_pct",0.0))
    fig,ax=plt.subplots(figsize=(5,3)); ax.barh(labels,vals,color=["#2ca02c" if v>=0 else "#d62728" for v in vals])
    ax.set_xlabel("% unrealized"); fig.tight_layout(); return fig

def build_distribution_pie(stats):
    labels,sizes=[],[]
    for sym,s in stats.items():
        val=s["remaining_qty"]*s["current_price"]
        if val>0: labels.append(sym); sizes.append(val)
    fig,ax=plt.subplots(figsize=(4,3))
    if sizes: ax.pie(sizes,labels=labels,autopct="%1.1f%%",startangle=90)
    ax.axis("equal"); return fig
