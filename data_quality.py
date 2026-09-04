"""Market-data quality audit. Bad data must reduce confidence rather than disappear silently."""
from __future__ import annotations
import math
from typing import Dict, Any
import pandas as pd


def audit_ohlcv(df: pd.DataFrame, timeframe: str = "") -> Dict[str, Any]:
    if df is None or df.empty:
        return {"ok": False, "score": 0.0, "grade": "F", "issues": ["Aucune donnée."], "stats": {}}
    x = df.copy()
    issues=[]; penalties=0.0
    required=["open","high","low","close"]
    missing=[c for c in required if c not in x.columns]
    if missing: return {"ok": False, "score": 0.0, "grade": "F", "issues":[f"Colonnes manquantes: {missing}"], "stats": {}}
    if not x.index.is_monotonic_increasing: issues.append("Index temporel non croissant."); penalties += 15
    dup=int(x.index.duplicated().sum())
    if dup: issues.append(f"{dup} timestamps dupliqués."); penalties += min(20, dup*2)
    for c in required:
        bad=int(pd.to_numeric(x[c], errors="coerce").isna().sum())
        if bad: issues.append(f"{bad} valeurs non numériques/NaN dans {c}."); penalties += min(20, bad/max(len(x),1)*100)
    h=x["high"]; l=x["low"]; o=x["open"]; c=x["close"]
    bad_ohl=((h < pd.concat([o,c],axis=1).max(axis=1)) | (l > pd.concat([o,c],axis=1).min(axis=1)) | (h<l))
    nbad=int(bad_ohl.sum())
    if nbad: issues.append(f"{nbad} bougies OHLC incohérentes."); penalties += min(30, nbad/max(len(x),1)*100)
    ret=c.pct_change().abs().dropna()
    if len(ret):
        extreme=int((ret > ret.median()*25).sum()) if ret.median()>0 else 0
        if extreme: issues.append(f"{extreme} mouvements extrêmes à examiner."); penalties += min(15, extreme/max(len(ret),1)*100)
    gaps=0
    if isinstance(x.index, pd.DatetimeIndex) and len(x)>3:
        delta=x.index.to_series().diff().dropna().dt.total_seconds()
        med=delta.median()
        if med and math.isfinite(float(med)):
            gaps=int((delta > med*3.5).sum())
            if gaps: issues.append(f"{gaps} grands gaps temporels détectés."); penalties += min(15, gaps/max(len(delta),1)*100)
    volume_missing = "volume" not in x.columns
    if volume_missing: issues.append("Volume absent: les métriques volume/flow sont limitées."); penalties += 4
    score=max(0.0,100.0-penalties)
    grade="A" if score>=90 else "B" if score>=80 else "C" if score>=70 else "D" if score>=55 else "F"
    return {"ok": score>=55, "score": round(score,1), "grade": grade, "issues": issues or ["Aucun défaut majeur détecté."],
            "stats": {"bars":len(x), "duplicates":dup, "ohlc_errors":nbad, "gaps":gaps, "timeframe":timeframe},
            "note":"Le score mesure la qualité des données reçues, pas la qualité d'un trade."}
