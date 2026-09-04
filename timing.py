"""Timing/session and volatility engine, relative to the selected execution timeframe."""
from __future__ import annotations
from datetime import datetime, time
from zoneinfo import ZoneInfo
from typing import Dict, Any
import math
LOCAL_TZ="Africa/Porto-Novo"
DEFAULT_WINDOWS={"Londres":("08:00","11:00"),"Ouverture New York":("14:00","17:00"),"Chevauchement Londres/NY":("14:00","16:00"),"BTC US":("14:00","18:00")}
def _parse_hhmm(value): h,m=[int(x) for x in value.split(":")]; return time(h,m)
def in_window(now,start,end):
    t=now.time(); a,b=_parse_hhmm(start),_parse_hhmm(end); return a<=t<b if a<=b else (t>=a or t<b)
def current_windows(now=None):
    now=now or datetime.now(ZoneInfo(LOCAL_TZ)); return [n for n,w in DEFAULT_WINDOWS.items() if in_window(now,*w)]
def volatility_profile(df):
    if df is None or len(df)<40:return {"ok":False,"score":0.,"ratio":math.nan,"percentile":math.nan,"regime":"DONNÉES INSUFFISANTES"}
    d=df.copy(); close=d.close.astype(float); ret=close.pct_change().abs(); recent=ret.rolling(4).mean().iloc[-1]; base=ret.rolling(40).mean().iloc[-1]; ratio=float(recent/base) if base and math.isfinite(float(base)) else math.nan; hist=ret.rolling(4).mean().dropna(); pct=float((hist<=recent).mean()*100) if not hist.empty and math.isfinite(float(recent)) else math.nan
    if not math.isfinite(ratio): regime="INCONNU"; score=0.
    elif ratio<.65: regime="FAIBLE"; score=25.
    elif ratio<=1.25: regime="NORMALE"; score=65.
    elif ratio<=2.: regime="EXPANSION"; score=90.
    elif ratio<=2.6: regime="FORTE"; score=70.
    else: regime="EXTRÊME"; score=20.
    return {"ok":True,"score":score,"ratio":ratio,"percentile":pct,"regime":regime}
def timing_assessment(instrument, execution_result, execution_df, now=None, custom_window=None, execution_tf="M15"):
    now=now or datetime.now(ZoneInfo(LOCAL_TZ)); windows=current_windows(now)
    if custom_window:
        if in_window(now,*custom_window): windows.append(f"Fenêtre personnalisée {custom_window[0]}-{custom_window[1]}")
    profile=volatility_profile(execution_df); ind=(execution_result or {}).get("indicators",{}); adx=ind.get("adx14",math.nan); adx=float(adx) if adx is not None else math.nan
    session_score=90. if windows else 35.; trend_score=80. if math.isfinite(adx) and adx>=20 else 55. if math.isfinite(adx) and adx>=15 else 25.; total=round(.45*profile.get("score",0)+.30*session_score+.25*trend_score,1)
    status="ATTENTE" if not profile.get("ok") else "RISQUE ÉLEVÉ" if profile.get("regime")=="EXTRÊME" else "FENÊTRE FAVORABLE" if total>=72 else "SURVEILLER" if total>=55 else "ATTENTE"
    return {"local_time":now.strftime("%H:%M:%S"),"timezone":"Bénin (UTC+1)","windows":windows,"profile":profile,"adx":adx,"score":total,"status":status,"execution_timeframe":execution_tf,"note":f"Fenêtre évaluée pour {execution_tf}. Les horaires sont des fenêtres de surveillance, pas des heures magiques."}
