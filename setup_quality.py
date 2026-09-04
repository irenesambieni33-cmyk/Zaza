"""Professional setup-quality scoring. Score is quality, never a win probability."""
from __future__ import annotations
from typing import Dict, Any
import math
from liquidity import liquidity_score


def _clip(x, lo, hi): return max(lo, min(hi, float(x)))


def evaluate_setup_quality(result: Dict[str, Any], setup: Dict[str, Any] | None, liquidity: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not setup or not setup.get("valid"):
        return {"approved":False,"score":0.0,"grade":"REJETÉ","reasons":["Setup technique invalide."],"families":{}}
    direction=setup.get("direction"); frames=result.get("timeframes",{}); signs={"ACHAT":1,"VENTE":-1}; target=signs.get(direction,0)
    exec_tf=result.get("execution_timeframe", "M15")
    policy=result.get("policy", {}) or {}
    families={}; reasons=[]
    policy_tfs=list(dict.fromkeys([*policy.get("context",()), *policy.get("structure",()), exec_tf]))
    base_weights={"D1":3,"W1":3,"H4":3,"H1":2,"M30":1.5,"M15":1,"M5":1}
    weights={tf:base_weights.get(tf,1.0) for tf in policy_tfs if tf in frames}; points=maxp=0.0
    for tf,w in weights.items():
        r=frames.get(tf,{})
        if not r.get("available"): continue
        maxp+=w; d=signs.get(r.get("direction"),0); points += w if d==target else 0.25*w if d==0 else 0
    families["tendance_MTF"]=_clip(20*points/maxp,0,20) if maxp else 0

    structure=0.0
    for tf,w in zip(policy.get("structure", ("H1","M30")), (3,2)):
        r=frames.get(tf,{})
        if not r.get("available"): continue
        sd=r.get("structure_data",{}) or {}; sdir=signs.get(r.get("direction"),0)
        structure += w*(1 if sdir==target else 0)
        events=(sd.get("bos",[])+sd.get("choch",[]))
        if target>0 and any("HAUSSIER" in x for x in events): structure+=0.5
        if target<0 and any("BAISSIER" in x for x in events): structure+=0.5
    families["structure_price_action"]=_clip(structure/7.5*20,0,20)

    m15=frames.get(exec_tf,{}); breakdown=m15.get("score_breakdown",{}) or {}; raw=float(breakdown.get("Momentum",0) or 0)
    families["momentum"]=_clip(20*raw/100.0,0,20)

    atr=(m15.get("indicators") or {}).get("atr_pct"); vol_ratio=(m15.get("indicators") or {}).get("volatility_regime_ratio"); volatility=15.0
    if atr is not None and math.isfinite(float(atr)):
        a=float(atr)
        if a>0.04: volatility-=7
        elif a>0.025: volatility-=3
        elif a<0.001: volatility-=3
    if vol_ratio is not None and math.isfinite(float(vol_ratio)):
        vr=float(vol_ratio)
        if vr>2.5: volatility-=4
        elif vr<0.45: volatility-=2
    families["volatilite"]=_clip(volatility,0,15)

    rr=float(setup.get("rr1",0) or 0); families["geometrie_RR"]=_clip(10 if rr>=2.5 else 7 if rr>=2 else 0,0,10)

    regime=(m15.get("regime") or {})
    dq=(m15.get("data_quality") or {})
    if dq.get("score",100) < 70: reasons.append(f"Qualité des données du timeframe d'exécution faible: {dq.get("score",0):.0f}/100.")
    lq=liquidity_score(liquidity or {},direction,float(setup["entry"]),float(setup["tp2"]),float(setup["sl"]))
    families["liquidite"]=_clip(lq.get("score",0),0,15)
    if lq.get("reason"): reasons.append(lq["reason"])

    score=sum(families.values()); hard=[]
    if rr<2: hard.append("R:R inférieur au minimum de 1:2.")
    if families["tendance_MTF"]<10: hard.append("Contexte multi-timeframe trop faible.")
    if families["structure_price_action"]<8: hard.append("Structure/prix insuffisamment confirmés.")
    if families["volatilite"]<5: hard.append("Régime de volatilité défavorable.")
    if families["liquidite"]<6: hard.append("Zone de liquidité exploitable insuffisamment claire.")
    if dq.get("score",100)<70: hard.append("Données du timeframe d'exécution trop fragiles pour autoriser un setup.")
    if regime.get("volatility")=="EXPANSION" and score<82: hard.append("Expansion de volatilité sans confluence suffisante.")
    approved=not hard and score>=72
    grade="A+" if score>=90 else "A" if score>=82 else "B" if score>=72 else "REJETÉ"
    if not approved: grade="REJETÉ"; reasons.extend(hard or ["Score de qualité inférieur au seuil."])
    else: reasons.append("Confluence tendance + structure + momentum + volatilité + liquidité + R:R validée.")
    return {"approved":approved,"score":round(score,1),"grade":grade,"families":{k:round(v,1) for k,v in families.items()},"reasons":reasons,"regime": regime, "data_quality": dq, "note":"Score de qualité sur 100, pas une probabilité mathématique de gain. Le régime et la qualité des données sont des garde-fous, pas des prédictions."}
