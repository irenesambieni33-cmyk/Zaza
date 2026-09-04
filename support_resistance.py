"""Support/resistance zones built from confirmed swings and clustered by ATR distance."""

from __future__ import annotations
from typing import Dict, List
import numpy as np
import pandas as pd
from config import SR_LOOKBACK, SR_MIN_TOUCHES, SR_TOLERANCE_ATR


def _cluster(levels: List[float], tolerance: float) -> List[Dict]:
    if not levels or tolerance <= 0:
        return []
    clusters: List[List[float]] = []
    for level in sorted(levels):
        if not clusters or abs(level - np.mean(clusters[-1])) > tolerance:
            clusters.append([level])
        else:
            clusters[-1].append(level)
    result = []
    for vals in clusters:
        if len(vals) >= SR_MIN_TOUCHES:
            result.append({"low": float(min(vals)), "high": float(max(vals)), "price": float(np.mean(vals)), "touches": len(vals)})
    return result


def detect_zones(df: pd.DataFrame) -> Dict[str, List[Dict]]:
    if df.empty or "swing_high" not in df.columns or "swing_low" not in df.columns:
        return {"supports": [], "resistances": [], "tolerance": None}
    atr_series = df.get("atr14", pd.Series(dtype=float)).dropna()
    atr = float(atr_series.iloc[-1]) if not atr_series.empty else float((df["high"] - df["low"]).median())
    if not np.isfinite(atr) or atr <= 0:
        return {"supports": [], "resistances": [], "tolerance": None}
    tolerance = max(atr * SR_TOLERANCE_ATR, 1e-12)
    work = df.tail(SR_LOOKBACK)
    highs = work.loc[work["swing_high"], "high"].dropna().tolist()
    lows = work.loc[work["swing_low"], "low"].dropna().tolist()
    price = float(df["close"].iloc[-1])
    supports = [z for z in _cluster(lows, tolerance) if z["price"] < price]
    resistances = [z for z in _cluster(highs, tolerance) if z["price"] > price]
    supports.sort(key=lambda z: z["price"], reverse=True)
    resistances.sort(key=lambda z: z["price"])
    return {"supports": supports[:6], "resistances": resistances[:6], "tolerance": tolerance}
