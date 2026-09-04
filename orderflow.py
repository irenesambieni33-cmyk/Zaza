"""Public-data buyer/seller pressure estimator. It is an inference, not hidden order-book access."""
from __future__ import annotations
import math
import pandas as pd

def buyer_seller_pressure(df:pd.DataFrame, lookback:int=30):
    if df is None or df.empty: return {"ok":False,"buyers":50.0,"sellers":50.0,"bias":"NEUTRE","strength":0.0}
    x=df.tail(lookback).copy()
    rng=(x["high"]-x["low"]).replace(0,float("nan"))
    body=(x["close"]-x["open"])/rng
    close_pos=((x["close"]-x["low"])/rng*2-1).fillna(0)
    vol=x.get("volume",pd.Series(1,index=x.index)).fillna(1)
    vmean=vol.rolling(min(20,len(vol))).mean().replace(0,float("nan"))
    vz=(vol/vmean).clip(0.25,3).fillna(1)
    pressure=(0.65*body+0.35*close_pos)*vz
    net=float(pressure.mean()) if len(pressure) else 0
    net=max(-1,min(1,net))
    buyers=50+50*net; sellers=100-buyers
    bias="ACHETEURS" if net>0.12 else "VENDEURS" if net<-0.12 else "ÉQUILIBRE"
    return {"ok":True,"buyers":round(buyers,1),"sellers":round(sellers,1),"bias":bias,"strength":round(abs(net)*100,1),"net":round(net,3),"note":"Pression estimée à partir des bougies et du volume public. Ce n'est pas un carnet d'ordres caché."}
