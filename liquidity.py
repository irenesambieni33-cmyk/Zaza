"""Public-price liquidity engine: zones, sweeps, rejection/reclaim and displacement."""
from __future__ import annotations
from typing import Dict, Any, List
import math
import numpy as np
import pandas as pd

def _cluster(values, tolerance):
    values=sorted(float(v) for v in values if math.isfinite(float(v)))
    if not values:return []
    groups=[[values[0]]]
    for v in values[1:]:
        center=float(np.mean(groups[-1]))
        if abs(v-center)<=tolerance: groups[-1].append(v)
        else: groups.append([v])
    return [{"price":float(np.mean(g)),"touches":len(g),"low":min(g),"high":max(g),"strength":round(min(100.,35.+15.*len(g)),1)} for g in groups if len(g)>=2]

def build_liquidity_map(df:pd.DataFrame, structure=None, atr=None, lookback=160, execution_tf="M15"):
    if df is None or df.empty or len(df)<30:
        return {"ok":False,"pools":[],"events":[],"nearest":None,"bias":"INCONNU","note":f"Données {execution_tf} insuffisantes."}
    d=df.tail(lookback).copy(); close=float(d.close.iloc[-1])
    if atr is None or not math.isfinite(float(atr)) or atr<=0: atr=float((d.high-d.low).rolling(14).mean().iloc[-1])
    if not math.isfinite(atr) or atr<=0: return {"ok":False,"pools":[],"events":[],"nearest":None,"bias":"INCONNU","note":"ATR indisponible."}
    tolerance=max(atr*.18,close*.00035)
    h=d.high.astype(float).to_numpy(); l=d.low.astype(float).to_numpy(); c=d.close.astype(float).to_numpy()
    local_highs=[h[i] for i in range(2,len(d)-2) if h[i]>=max(h[i-2:i+3])]
    local_lows=[l[i] for i in range(2,len(d)-2) if l[i]<=min(l[i-2:i+3])]
    if structure:
        local_highs += [x["price"] for x in structure.get("swings",{}).get("highs",[])[-12:]]
        local_lows += [x["price"] for x in structure.get("swings",{}).get("lows",[])[-12:]]
    pools=[]
    for z in _cluster(local_highs,tolerance):
        if z["price"]>close: z.update({"type":"LIQUIDITÉ AU-DESSUS","side":"BUY_STOP_POOL","distance_atr":(z["price"]-close)/atr}); pools.append(z)
    for z in _cluster(local_lows,tolerance):
        if z["price"]<close: z.update({"type":"LIQUIDITÉ EN-DESSOUS","side":"SELL_STOP_POOL","distance_atr":(close-z["price"])/atr}); pools.append(z)
    rh=float(d.high.tail(24).max()); rl=float(d.low.tail(24).min())
    if rh>close and all(abs(rh-p["price"])>tolerance for p in pools): pools.append({"price":rh,"touches":1,"low":rh,"high":rh,"strength":45.,"type":"LIQUIDITÉ HAUT RÉCENT","side":"BUY_STOP_POOL","distance_atr":(rh-close)/atr})
    if rl<close and all(abs(rl-p["price"])>tolerance for p in pools): pools.append({"price":rl,"touches":1,"low":rl,"high":rl,"strength":45.,"type":"LIQUIDITÉ BAS RÉCENT","side":"SELL_STOP_POOL","distance_atr":(close-rl)/atr})
    pools.sort(key=lambda x:abs(x["price"]-close))
    events=[]
    for p in pools[:10]:
        level=float(p["price"]); side=p["side"]
        if len(d)<3: continue
        prev_close=float(c[-2]); last_high=float(h[-1]); last_low=float(l[-1]); last_close=float(c[-1])
        swept=(last_high>=level and last_close<level) if side=="BUY_STOP_POOL" else (last_low<=level and last_close>level)
        reclaimed=(last_close>=level) if side=="BUY_STOP_POOL" else (last_close<=level)
        body=abs(c[-1]-float(d.open.iloc[-1])); recent_body=float(np.mean(np.abs(c[-10:]-d.open.astype(float).tail(10).to_numpy())))
        displacement=bool(recent_body and body>1.5*recent_body)
        if swept:
            events.append({"type":"SWEEP","price":level,"side":"HAUSSIER" if side=="SELL_STOP_POOL" else "BAISSIER","reclaim":reclaimed,"displacement":displacement,"timeframe":execution_tf})
    nearest=pools[0] if pools else None
    return {"ok":True,"pools":pools[:12],"events":events,"nearest":nearest,
            "tolerance":tolerance,"current_price":close,"bias":"HAUT À SURVEILLER" if nearest and nearest["price"]>close else "BAS À SURVEILLER" if nearest else "INCONNU",
            "execution_timeframe":execution_tf,
            "note":"Carte de liquidité issue des prix publics. Un sweep est une inférence à partir d'un franchissement/rejet, pas une vision des ordres cachés."}

def liquidity_score(liquidity,direction,entry,tp,sl):
    if not liquidity.get("ok") or direction not in {"ACHAT","VENTE"}: return {"score":0.,"approved":False,"reason":"Carte de liquidité indisponible."}
    events=liquidity.get("events",[]); target_side="BUY_STOP_POOL" if direction=="ACHAT" else "SELL_STOP_POOL"
    candidates=[p for p in liquidity.get("pools",[]) if p.get("side")==target_side]
    score=3.; reasons=["Aucun sweep récent confirmé dans les données publiques."]
    if candidates: score=7.; reasons=[f"Liquidité directionnelle détectée à {_fmt_price(min(candidates,key=lambda p:abs(p['price']-entry))['price'])}."]
    matching=[e for e in events if (direction=="ACHAT" and e["side"]=="HAUSSIER") or (direction=="VENTE" and e["side"]=="BAISSIER")]
    if matching:
        score=12.; reasons.append("Sweep de liquidité compatible avec le sens du setup.")
        if matching[-1].get("reclaim"): score+=1.; reasons.append("Reclaim/rejet détecté après le sweep.")
        if matching[-1].get("displacement"): score+=2.; reasons.append("Déplacement impulsif détecté après le sweep.")
    return {"score":min(15.,score),"approved":score>=8.,"reason":" ".join(reasons)}

def _fmt_price(x): return f"{float(x):.5f}"
