def profit_take_signal(stat, profit_pct=300.0):
    unreal_pct=stat.get("unrealized_pct",0.0)
    qty=stat.get("remaining_qty",0.0); avg=stat.get("avg_buy",0.0); cur=stat.get("current_price",0.0)
    if qty<=0 or avg<=0 or cur<=0: return (False,0.0)
    if unreal_pct>=profit_pct:
        cost_basis=qty*avg; qty_to_sell=min(qty,cost_basis/cur)
        return (True,qty_to_sell)
    return (False,0.0)
