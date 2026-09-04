"""Confirmed market-structure detection: swings, HH/HL/LH/LL, BOS and CHoCH."""

from __future__ import annotations

from typing import Dict, List
import numpy as np
import pandas as pd
from config import SWING_LEFT, SWING_RIGHT, MIN_SWING_ATR


def detect_swings(df: pd.DataFrame, left: int = SWING_LEFT, right: int = SWING_RIGHT) -> pd.DataFrame:
    out = df.copy()
    out["swing_high"] = False
    out["swing_low"] = False
    if len(out) < left + right + 3:
        return out
    highs, lows = out["high"].to_numpy(), out["low"].to_numpy()
    atr = out.get("atr14", pd.Series(np.nan, index=out.index)).to_numpy()
    sh = np.zeros(len(out), dtype=bool)
    sl = np.zeros(len(out), dtype=bool)
    for i in range(left, len(out) - right):
        h_window = highs[i-left:i+right+1]
        l_window = lows[i-left:i+right+1]
        h = highs[i]
        l = lows[i]
        if h >= np.nanmax(h_window) and np.sum(h == h_window) == 1:
            sh[i] = True
        if l <= np.nanmin(l_window) and np.sum(l == l_window) == 1:
            sl[i] = True
    # A swing must have meaningful range when ATR is available. This filters micro-noise.
    if np.isfinite(atr).any():
        for i in range(len(out)):
            if sh[i]:
                local_range = highs[i] - np.nanmin(lows[max(0, i-left):min(len(out), i+right+1)])
                if np.isfinite(atr[i]) and local_range < MIN_SWING_ATR * atr[i]:
                    sh[i] = False
            if sl[i]:
                local_range = np.nanmax(highs[max(0, i-left):min(len(out), i+right+1)]) - lows[i]
                if np.isfinite(atr[i]) and local_range < MIN_SWING_ATR * atr[i]:
                    sl[i] = False
    out["swing_high"], out["swing_low"] = sh, sl
    return out


def classify_swings(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["swing_label"] = ""
    last_high = last_low = None
    for i in range(len(out)):
        if bool(out["swing_high"].iloc[i]):
            price = float(out["high"].iloc[i])
            if last_high is not None:
                out.iat[i, out.columns.get_loc("swing_label")] = "HH" if price > last_high else "LH"
            last_high = price
        if bool(out["swing_low"].iloc[i]):
            price = float(out["low"].iloc[i])
            label = "HL" if last_low is not None and price > last_low else "LL" if last_low is not None else ""
            if not out.iat[i, out.columns.get_loc("swing_label")]:
                out.iat[i, out.columns.get_loc("swing_label")] = label
            last_low = price
    return out


def _pivot_lists(df: pd.DataFrame) -> Dict[str, List[Dict]]:
    highs = [{"time": idx, "price": float(row.high), "label": row.swing_label}
             for idx, row in df[df["swing_high"]].iterrows()]
    lows = [{"time": idx, "price": float(row.low), "label": row.swing_label}
            for idx, row in df[df["swing_low"]].iterrows()]
    return {"highs": highs, "lows": lows}


def add_structure_events(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["bos"], out["choch"] = "", ""
    out["structure_trend"] = "RANGE / NEUTRE"
    last_high = last_low = None
    broken_high = broken_low = None
    trend = "RANGE / NEUTRE"
    for i in range(len(out)):
        row = out.iloc[i]
        if bool(row.swing_high):
            last_high = float(row.high)
            broken_high = False
        if bool(row.swing_low):
            last_low = float(row.low)
            broken_low = False
        close = float(row.close)
        if last_high is not None and broken_high is False and close > last_high:
            col = "choch" if trend == "BAISSIÈRE" else "bos"
            out.iat[i, out.columns.get_loc(col)] = "CHoCH HAUSSIER" if col == "choch" else "BOS HAUSSIER"
            trend = "HAUSSIÈRE"
            broken_high = True
        if last_low is not None and broken_low is False and close < last_low:
            col = "choch" if trend == "HAUSSIÈRE" else "bos"
            out.iat[i, out.columns.get_loc(col)] = "CHoCH BAISSIER" if col == "choch" else "BOS BAISSIER"
            trend = "BAISSIÈRE"
            broken_low = True
        out.iat[i, out.columns.get_loc("structure_trend")] = trend
    return out


def analyze_structure(df: pd.DataFrame) -> Dict:
    if df.empty:
        return {"trend": "RANGE / NEUTRE", "hh": 0, "hl": 0, "lh": 0, "ll": 0, "bos": [], "choch": [], "recent_events": [], "swings": {"highs": [], "lows": []}, "data": df}
    work = add_structure_events(classify_swings(detect_swings(df)))
    labels = work["swing_label"]
    pivots = _pivot_lists(work)
    recent_bos = work.loc[work["bos"] != "", "bos"].tail(5).tolist()
    recent_choch = work.loc[work["choch"] != "", "choch"].tail(5).tolist()
    events = work.loc[(work["bos"] != "") | (work["choch"] != ""), ["bos", "choch"]].tail(8)
    recent_events = [a or b for a, b in events.itertuples(index=False, name=None)]

    # Current structure is based on the most recent classified pivots, while BOS/CHoCH can override it.
    trend = str(work["structure_trend"].iloc[-1])
    recent_high_labels = [x["label"] for x in pivots["highs"][-4:] if x["label"]]
    recent_low_labels = [x["label"] for x in pivots["lows"][-4:] if x["label"]]
    if not recent_bos and not recent_choch:
        bull = recent_high_labels.count("HH") >= 1 and recent_low_labels.count("HL") >= 1
        bear = recent_high_labels.count("LH") >= 1 and recent_low_labels.count("LL") >= 1
        trend = "HAUSSIÈRE" if bull and not bear else "BAISSIÈRE" if bear and not bull else "RANGE / NEUTRE"
    return {
        "data": work, "trend": trend,
        "hh": int((labels == "HH").sum()), "hl": int((labels == "HL").sum()),
        "lh": int((labels == "LH").sum()), "ll": int((labels == "LL").sum()),
        "bos": recent_bos, "choch": recent_choch, "recent_events": recent_events,
        "swings": pivots,
    }
