import requests
from .config import COINGECKO_TIMEOUT, FEAR_GREED_TIMEOUT

def prices_coingecko(bases):
    ids = {"btc":"bitcoin","eth":"ethereum","xrp":"ripple","pol":"polygon","usdt":"tether"}
    url="https://api.coingecko.com/api/v3/simple/price"
    params={"ids":",".join([ids.get(b,b) for b in bases]),"vs_currencies":"usd","include_24hr_change":"true"}
    try:
        r=requests.get(url,params=params,timeout=COINGECKO_TIMEOUT); r.raise_for_status()
        data=r.json(); out={}
        for b in bases:
            cid=ids.get(b,b)
            if cid in data: out[b]={"price":data[cid]["usd"],"change_24h":data[cid].get("usd_24h_change")}
        return out
    except: return {b:{"price":0.0,"change_24h":None} for b in bases}

def fetch_fear_greed():
    try:
        r=requests.get("https://api.alternative.me/fng/",timeout=FEAR_GREED_TIMEOUT); r.raise_for_status()
        d=r.json()["data"][0]; return {"value":d["value"],"classification":d["value_classification"]}
    except: return {"value":None,"classification":None}
