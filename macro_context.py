"""Macro/news context engine for RE-ZERO RE-ZERO.
Uses public official calendars where possible and degrades safely when unavailable.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import json, re
from typing import Any, Dict, List
import requests

TIMEOUT=8
BENIN=timezone(timedelta(hours=1))

EVENT_WEIGHTS={
    "NFP":10,"EMPLOYMENT SITUATION":10,"NONFARM":10,
    "CPI":9,"CONSUMER PRICE INDEX":9,"PPI":7,"FOMC":10,
    "FED":8,"ECB":10,"INTEREST RATE":10,"GDP":7,"PMI":6,
    "RETAIL SALES":6,"JOLTS":6,"POWELL":8,"LAGARDE":8,
}

def _impact(title:str)->int:
    u=title.upper()
    for k,w in EVENT_WEIGHTS.items():
        if k in u:return w
    return 3

def _assets(title:str)->List[str]:
    u=title.upper(); out=[]
    if any(k in u for k in ["NFP","EMPLOYMENT","CPI","PPI","FOMC","FED","POWELL","JOLTS","RETAIL SALES"]): out += ["EUR/USD","XAU/USD","BTC/USD"]
    if any(k in u for k in ["ECB","LAGARDE","EURO AREA","EUROZONE"]): out += ["EUR/USD"]
    return list(dict.fromkeys(out))

def _parse_bls_ics(text:str)->List[Dict[str,Any]]:
    events=[]
    blocks=text.replace("\r\n","\n").split("BEGIN:VEVENT")
    for b in blocks[1:]:
        title=re.search(r"SUMMARY:(.*)",b); dt=re.search(r"DTSTART(?:;[^:]+)?:([0-9TZ]+)",b)
        if not title or not dt: continue
        raw=dt.group(1)
        try:
            if raw.endswith('Z'): when=datetime.strptime(raw,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
            else: when=datetime.strptime(raw,'%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
        except Exception: continue
        title=title.group(1).strip()
        events.append({"title":title,"when":when,"impact":_impact(title),"assets":_assets(title),"source":"U.S. BLS"})
    return events

def fetch_macro_events(days:int=7)->Dict[str,Any]:
    now=datetime.now(timezone.utc); events=[]; sources=[]
    try:
        r=requests.get("https://www.bls.gov/schedule/news_release/bls.ics",timeout=TIMEOUT,headers={"User-Agent":"RE-ZERO/8.0"})
        if r.ok:
            events += _parse_bls_ics(r.text); sources.append("BLS")
    except Exception: pass
    # FOMC 2026 official schedule, with dates expressed in UTC for the application clock.
    fomc_2026=[(1,28),(3,18),(4,29),(6,17),(7,29),(9,16),(10,28),(12,9)]
    for m,d in fomc_2026:
        when=datetime(2026,m,d,18,0,tzinfo=timezone.utc)
        events.append({"title":"FOMC — décision de politique monétaire","when":when,"impact":10,"assets":["EUR/USD","XAU/USD","BTC/USD"],"source":"Federal Reserve"})
    end=now+timedelta(days=days)
    clean=[]
    seen=set()
    for e in sorted(events,key=lambda x:x["when"]):
        if now-timedelta(hours=2) <= e["when"] <= end:
            key=(e["title"],e["when"].isoformat())
            if key in seen: continue
            seen.add(key); e=dict(e); e["when_utc"]=e["when"].isoformat(); e["when_benin"]=e["when"].astimezone(BENIN).strftime("%Y-%m-%d %H:%M"); clean.append(e)
    return {"ok":bool(clean),"events":clean,"sources":sources+["Federal Reserve"],"updated_utc":now.isoformat()}

def macro_assessment(instrument:str, events:Dict[str,Any], now:datetime|None=None)->Dict[str,Any]:
    now=now or datetime.now(timezone.utc); relevant=[]
    for e in events.get("events",[]):
        if instrument not in e.get("assets",[]): continue
        dt=datetime.fromisoformat(e["when_utc"]); mins=(dt-now).total_seconds()/60
        if -120 <= mins <= 1440: relevant.append((e,mins))
    nearest=min(relevant,key=lambda x:abs(x[1])) if relevant else None
    risk="NORMAL"; score=0.0; reasons=[]
    if nearest:
        e,mins=nearest; imp=e["impact"]
        if abs(mins)<=15 and imp>=8: risk="BLOQUÉ / CHOC MACRO"; score=0; reasons.append(f"Annonce majeure imminente : {e['title']}")
        elif abs(mins)<=60 and imp>=8: risk="TRÈS ÉLEVÉ"; score=0; reasons.append(f"Fenêtre macro sensible : {e['title']}")
        elif mins>0 and mins<=240 and imp>=7: risk="ÉLEVÉ"; reasons.append(f"Annonce importante dans {mins:.0f} min : {e['title']}")
        else: reasons.append(f"Prochaine annonce : {e['title']}")
    return {"risk":risk,"score":score,"nearest":nearest[0] if nearest else None,"minutes_to_event":nearest[1] if nearest else None,"reasons":reasons,"note":"Le moteur macro filtre le risque d'annonce; il ne prétend pas connaître à l'avance le résultat d'une publication."}
