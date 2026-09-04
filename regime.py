"""Market-regime detection using past-only, interpretable features.
No future labels are used. The detector classifies trend/range and volatility state.
"""
from __future__ import annotations
import math
from typing import Dict, Any
import numpy as np
import pandas as pd


def detect_regime(df: pd.DataFrame, lookback: int = 100) -> Dict[str, Any]:
    if df is None or len(df) < 60:
        return {"ok": False, "label": "DONNÉES INSUFFISANTES", "score": 0.0, "features": {}, "note": "Au moins 60 bougies sont nécessaires."}
    x = df.copy().tail(lookback)
    close = pd.to_numeric(x["close"], errors="coerce").dropna()
    if len(close) < 50:
        return {"ok": False, "label": "DONNÉES INSUFFISANTES", "score": 0.0, "features": {}, "note": "Historique trop court."}
    ret = close.pct_change().dropna()
    vol20 = float(ret.tail(20).std()) if len(ret) >= 20 else math.nan
    vol60 = float(ret.tail(60).std()) if len(ret) >= 60 else math.nan
    vol_ratio = vol20 / vol60 if vol60 and math.isfinite(vol60) and vol60 > 0 else 1.0
    x1 = close.iloc[-1]
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]
    slope = (ema20 / close.iloc[-21] - 1.0) if len(close) >= 21 and close.iloc[-21] else 0.0
    trend_strength = min(1.0, abs(slope) / max(vol20 * 3.0, 1e-9))
    direction = "HAUSSE" if slope > 0 else "BAISSE" if slope < 0 else "NEUTRE"
    compression = vol_ratio < 0.65
    expansion = vol_ratio > 1.60
    if trend_strength >= 0.75 and abs(ema20 / ema50 - 1) > max(vol20 * 0.5, 0.0001):
        base = "TENDANCE"
    elif trend_strength < 0.35:
        base = "RANGE"
    else:
        base = "TRANSITION"
    if expansion:
        vol_state = "EXPANSION"
    elif compression:
        vol_state = "COMPRESSION"
    else:
        vol_state = "NORMALE"
    label = f"{base} {direction} • VOL {vol_state}"
    confidence = 100.0 * min(1.0, 0.55 * trend_strength + 0.45 * min(1.0, abs(vol_ratio - 1.0) + 0.35))
    return {"ok": True, "label": label, "base": base, "direction": direction, "volatility": vol_state,
            "score": round(confidence, 1), "features": {"vol_ratio": round(vol_ratio, 3), "trend_strength": round(trend_strength, 3), "slope": round(slope, 6)},
            "note": "Régime calculé uniquement à partir des données disponibles avant la bougie courante. Ce n'est pas une prédiction."}
