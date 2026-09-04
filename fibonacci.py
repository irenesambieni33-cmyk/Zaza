"""Fibonacci retracement/extension using the latest meaningful swing pair."""

from __future__ import annotations
from typing import Dict, Optional
import numpy as np
import pandas as pd
from config import FIB_LEVELS, FIB_CONFLUENCE_ATR


def _choose_impulse(structure: Dict) -> Optional[tuple]:
    highs = structure.get("swings", {}).get("highs", [])
    lows = structure.get("swings", {}).get("lows", [])
    if not highs or not lows:
        return None
    trend = structure.get("trend", "RANGE / NEUTRE")
    if trend == "HAUSSIÈRE":
        candidates = [(lo, hi) for lo in lows for hi in highs if lo["time"] < hi["time"]]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p[1]["time"])
    if trend == "BAISSIÈRE":
        candidates = [(hi, lo) for hi in highs for lo in lows if hi["time"] < lo["time"]]
        if not candidates:
            return None
        return max(candidates, key=lambda p: p[1]["time"])
    # In a range, use the most recent alternating pair, without inventing a direction.
    pairs = [(lo, hi, "up") for lo in lows for hi in highs if lo["time"] < hi["time"]]
    pairs += [(hi, lo, "down") for hi in highs for lo in lows if hi["time"] < lo["time"]]
    if not pairs:
        return None
    a, b, _direction = max(pairs, key=lambda p: p[1]["time"])
    return a, b


def calculate_fibonacci(df: pd.DataFrame, structure: Dict) -> Dict:
    empty = {"levels": {}, "direction": None, "nearest": None, "swing_high": None, "swing_low": None, "anchor_times": None}
    if df.empty:
        return empty
    pair = _choose_impulse(structure)
    if not pair:
        return empty
    a, b = pair
    low_price = min(float(a["price"]), float(b["price"]))
    high_price = max(float(a["price"]), float(b["price"]))
    if not np.isfinite(high_price-low_price) or high_price <= low_price:
        return empty
    direction = "up" if float(b["price"]) > float(a["price"]) else "down"
    if direction == "up":
        levels = {f"{p*100:.1f}%": low_price + (high_price-low_price)*p for p in FIB_LEVELS}
    else:
        levels = {f"{p*100:.1f}%": high_price - (high_price-low_price)*p for p in FIB_LEVELS}
    price = float(df["close"].iloc[-1])
    nearest_name = min(levels, key=lambda k: abs(levels[k]-price))
    return {**empty, "levels": levels, "direction": direction, "nearest": (nearest_name, levels[nearest_name]),
            "swing_high": high_price, "swing_low": low_price, "anchor_times": (a["time"], b["time"])}


def confluence(fib: Dict, zones: Dict, price: float, atr: Optional[float] = None) -> Dict:
    tolerance = max((atr or 0) * FIB_CONFLUENCE_ATR, abs(price)*0.0005, 1e-12)
    supports = zones.get("supports", [])
    resistances = zones.get("resistances", [])
    near_support = any(abs(z["price"]-price) <= tolerance for z in supports)
    near_resistance = any(abs(z["price"]-price) <= tolerance for z in resistances)
    nearest = fib.get("nearest")
    near_fib = nearest is not None and abs(float(nearest[1])-price) <= tolerance
    fib_price = float(nearest[1]) if nearest else None
    bull = int(near_support) + int(near_fib and fib.get("direction") == "up")
    bear = int(near_resistance) + int(near_fib and fib.get("direction") == "down")
    return {"score": float(max(bull, bear)), "bull": bull, "bear": bear,
            "near_support": near_support, "near_resistance": near_resistance,
            "near_fib": near_fib, "fib_level": nearest[0] if nearest else None,
            "fib_price": fib_price, "tolerance": tolerance}
