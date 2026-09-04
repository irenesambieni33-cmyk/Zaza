"""Lightweight historical validation for the RE-ZERO quality score.
This is research/simulation only. It never sends broker orders.
"""
from __future__ import annotations
import math
import pandas as pd
from analysis import analyze_timeframe


def backtest_timeframe(df: pd.DataFrame, timeframe: str = "M15", horizon: int = 12, max_samples: int = 120, step: int = 5) -> dict:
    if df is None or len(df) < 180:
        return {"ok": False, "reason": "Pas assez de données historiques."}
    df = df.copy().sort_index()
    start = max(120, len(df) - (max_samples * step + horizon + 5))
    wins = losses = neutral = 0
    returns = []
    score_buckets = {"<50": [0,0], "50-59": [0,0], "60-69": [0,0], "70-79": [0,0], "80+": [0,0]}
    evaluated = 0
    for i in range(start, len(df)-horizon, step):
        hist = df.iloc[:i]
        try:
            r = analyze_timeframe(hist, timeframe)
        except Exception:
            continue
        if not r.get("available") or r.get("direction") not in {"ACHAT","VENTE"}:
            neutral += 1
            continue
        entry = float(hist["close"].iloc[-1]); future = df["close"].iloc[i:i+horizon]
        direction = 1 if r["direction"] == "ACHAT" else -1
        move = direction * (float(future.iloc[-1]) - entry)
        if not math.isfinite(move) or entry <= 0: continue
        # Outcome uses direction over the horizon, intentionally simple and transparent.
        win = move > 0
        if win: wins += 1
        else: losses += 1
        returns.append(move/entry)
        c = float(r.get("confidence",0))
        key = "<50" if c < 50 else "50-59" if c < 60 else "60-69" if c < 70 else "70-79" if c < 80 else "80+"
        score_buckets[key][0] += 1; score_buckets[key][1] += int(win)
        evaluated += 1
    total = wins+losses
    win_rate = 100*wins/total if total else 0
    bucket_stats = {k:{"trades":v[0],"wins":v[1],"win_rate":100*v[1]/v[0] if v[0] else 0} for k,v in score_buckets.items()}
    return {"ok": True, "timeframe": timeframe, "samples": evaluated, "wins": wins, "losses": losses, "neutral": neutral, "win_rate": win_rate, "avg_directional_return": (100*sum(returns)/len(returns)) if returns else 0, "buckets": bucket_stats, "note": "Simulation historique simplifiée, sans spread/slippage ni exécution broker. Le score n'est pas une probabilité garantie."}
