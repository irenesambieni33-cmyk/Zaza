"""Performance analytics for paper trades and historical plan validation."""
from __future__ import annotations
from typing import Iterable, Dict, Any
import numpy as np
import pandas as pd
from analysis import analyze_timeframe
from risk import build_setup


def _value(obj, key, default=None):
    if isinstance(obj, dict): return obj.get(key, default)
    return getattr(obj, key, default)


def summarize_trades(trades: Iterable[Any]) -> Dict[str, Any]:
    rows = []
    for t in trades:
        if _value(t, "status", "CLOSED") == "CLOSED" and _value(t, "pnl", None) is not None:
            rows.append(float(_value(t, "pnl")))
    wins = sum(x > 0 for x in rows); losses = sum(x <= 0 for x in rows)
    gross_profit = sum(x for x in rows if x > 0); gross_loss = abs(sum(x for x in rows if x < 0))
    equity = np.cumsum(rows) if rows else np.array([])
    peak = np.maximum.accumulate(equity) if rows else np.array([])
    dd = equity - peak if rows else np.array([])
    return {"trades": len(rows), "wins": wins, "losses": losses, "win_rate": 100*wins/len(rows) if rows else 0.0,
            "net_pnl": float(sum(rows)), "profit_factor": gross_profit/gross_loss if gross_loss else (float("inf") if gross_profit else 0.0),
            "max_drawdown": abs(float(dd.min())) if len(dd) else 0.0, "expectancy": float(np.mean(rows)) if rows else 0.0}


def backtest_trade_plans(df: pd.DataFrame, timeframe: str = "M15", horizon: int = 16, max_samples: int = 160, step: int = 4,
                         spread_bps: float = 1.0, slippage_bps: float = 1.0, fee_bps: float = 0.0, min_confidence: float = 55.0, instrument: str = "INCONNU") -> Dict[str, Any]:
    if df is None or len(df) < 260:
        return {"ok": False, "reason": "Pas assez de données historiques pour une validation robuste."}
    df = df.copy().sort_index(); start = max(180, len(df) - (max_samples * step + horizon + 10))
    outcomes=[]; equity=peak=max_dd=0.0
    for i in range(start, len(df)-horizon, step):
        hist=df.iloc[:i]
        try: r=analyze_timeframe(hist,timeframe)
        except Exception: continue
        if not r.get("available") or r.get("direction") not in {"ACHAT","VENTE"}: continue
        setup=build_setup(float(hist["close"].iloc[-1]),r.get("indicators",{}).get("atr14"),r.get("structure_data",{}),r["direction"],r.get("zones",{}))
        if not setup.get("valid") or float(r.get("confidence",0)) < min_confidence: continue
        future=df.iloc[i:i+horizon]; entry=float(setup["entry"]); sl=float(setup["sl"]); tp2=float(setup["tp2"]); direction=setup["direction"]; sign=1 if direction=="ACHAT" else -1
        spread=entry*spread_bps/10000.0; slip=entry*slippage_bps/10000.0; exec_entry=entry+sign*(spread/2+slip)
        outcome="TIMEOUT"; exit_price=float(future["close"].iloc[-1]); r_mult=sign*(exit_price-exec_entry)/abs(entry-sl)
        for _,bar in future.iterrows():
            hi,lo=float(bar["high"]),float(bar["low"])
            hit_sl=(lo<=sl) if direction=="ACHAT" else (hi>=sl); hit_tp=(hi>=tp2) if direction=="ACHAT" else (lo<=tp2)
            if hit_sl: exit_price=sl; outcome="LOSS"; r_mult=-1.0; break
            if hit_tp: exit_price=tp2; outcome="WIN"; r_mult=abs(tp2-entry)/abs(entry-sl); break
        cost_r=((spread+slip)+entry*fee_bps/10000.0)/abs(entry-sl); r_mult-=cost_r
        equity+=r_mult; peak=max(peak,equity); max_dd=max(max_dd,peak-equity)
        outcomes.append({"timestamp":str(future.index[0]),"instrument":instrument,"execution_timeframe":timeframe,"setup_timeframe":timeframe,"direction":direction,"quality":float(r.get("confidence",0)),"outcome":outcome,"R":r_mult,"regime":(r.get("regime") or {}).get("label","INCONNU"),"data_quality":(r.get("data_quality") or {}).get("score",0)})
    if not outcomes:
        return {"ok":True,"trades":0,"wins":0,"losses":0,"win_rate":0.0,"net_r":0.0,"profit_factor":0.0,"max_drawdown_r":0.0,"expectancy_r":0.0,"rows":[],"note":"Aucun setup suffisamment sélectif n'a été validé sur l'échantillon."}
    rs=[x["R"] for x in outcomes]; wins=sum(x>0 for x in rs); losses=sum(x<=0 for x in rs); gp=sum(x for x in rs if x>0); gl=abs(sum(x for x in rs if x<0))
    return {"ok":True,"trades":len(rs),"wins":wins,"losses":losses,"win_rate":100*wins/len(rs),"net_r":sum(rs),"profit_factor":gp/gl if gl else float("inf"),"max_drawdown_r":max_dd,"expectancy_r":float(np.mean(rs)),"rows":outcomes,"note":"Backtest du plan Entry/SL/TP avec spread, slippage et règle conservatrice si SL et TP2 sont touchés dans la même bougie. Il ne prouve pas la rentabilité future."}


def performance_report(result: Dict[str, Any]) -> Dict[str, Any]:
    if not result.get("ok"): return result
    return {k:result.get(k) for k in ["trades","wins","losses","win_rate","net_r","profit_factor","max_drawdown_r","expectancy_r","note"]}
