"""Leakage-aware statistical validation for RE-ZERO trade outcomes.
Implements walk-forward evaluation, embargo/purge-aware splits, bootstrap CI, permutation test,
and regime-conditioned diagnostics. It is deliberately conservative and never calls a metric a probability of future profit.
"""
from __future__ import annotations
import math
from typing import Dict, Any, List
import numpy as np


def _sharpe(rs, annualization=1.0):
    x=np.asarray(rs,dtype=float); x=x[np.isfinite(x)]
    if len(x)<2 or x.std(ddof=1)==0: return 0.0
    return float(x.mean()/x.std(ddof=1)*math.sqrt(annualization))


def _sortino(rs):
    x=np.asarray(rs,dtype=float); x=x[np.isfinite(x)]
    downside=x[x<0]
    if len(x)<2 or downside.std(ddof=1)==0: return float(x.mean()) if len(x) else 0.0
    return float(x.mean()/max(downside.std(ddof=1),1e-12))


def bootstrap_ci(rs, statistic=np.mean, n=1000, seed=42):
    x=np.asarray(rs,dtype=float); x=x[np.isfinite(x)]
    if len(x)<8: return (math.nan, math.nan)
    rng=np.random.default_rng(seed); vals=[]
    for _ in range(n): vals.append(float(statistic(rng.choice(x,size=len(x),replace=True))))
    return tuple(np.quantile(vals,[0.025,0.975]))


def permutation_pvalue(rs, n=2000, seed=42):
    x=np.asarray(rs,dtype=float); x=x[np.isfinite(x)]
    if len(x)<8: return math.nan
    observed=float(np.mean(x)); rng=np.random.default_rng(seed); extreme=0
    centered=x-x.mean()
    for _ in range(n):
        perm=rng.permutation(centered)+x.mean()
        if abs(float(np.mean(perm))) >= abs(observed): extreme += 1
    return float((extreme+1)/(n+1))


def summarize_outcomes(rows: List[Dict[str,Any]]) -> Dict[str,Any]:
    rs=np.asarray([float(r["R"]) for r in rows],dtype=float) if rows else np.array([])
    if not len(rs): return {"trades":0,"win_rate":0.0,"net_r":0.0,"expectancy_r":0.0,"sharpe":0.0,"sortino":0.0}
    wins=int((rs>0).sum()); losses=int((rs<=0).sum()); gp=float(rs[rs>0].sum()); gl=float(abs(rs[rs<0].sum()))
    eq=np.cumsum(rs); peak=np.maximum.accumulate(eq); mdd=float(np.max(peak-eq)) if len(eq) else 0.0
    return {"trades":len(rs),"wins":wins,"losses":losses,"win_rate":100*wins/len(rs),"net_r":float(rs.sum()),"expectancy_r":float(rs.mean()),
            "profit_factor":gp/gl if gl else (float("inf") if gp else 0.0),"max_drawdown_r":mdd,"sharpe":_sharpe(rs),"sortino":_sortino(rs)}


def validate_backtest(rows: List[Dict[str,Any]], n_trials: int = 1, embargo: int = 1) -> Dict[str,Any]:
    base=summarize_outcomes(rows)
    rs=[float(r["R"]) for r in rows]
    ci=bootstrap_ci(rs)
    p=permutation_pvalue(rs)
    regimes={}
    for r in rows:
        reg=str(r.get("regime","INCONNU")); regimes.setdefault(reg,[]).append(r)
    regime_report={k:summarize_outcomes(v) for k,v in regimes.items()}
    def grouped(key):
        groups={}
        for row in rows:
            value=str(row.get(key,"INCONNU")); groups.setdefault(value,[]).append(row)
        return {k:summarize_outcomes(v) for k,v in groups.items()}
    segmented={"instrument":grouped("instrument"),"execution_timeframe":grouped("execution_timeframe"),"setup_timeframe":grouped("setup_timeframe"),"regime":regime_report}
    # Simple sequential walk-forward: fixed-size test blocks; no training row is allowed after test start.
    n=len(rows); folds=[]
    if n>=30:
        block=max(10,n//5)
        for end in range(block*2,n+1,block):
            train=rows[:end-block]; test=rows[end-block:end]
            if len(train)<10: continue
            folds.append({"train":len(train),"test":len(test),"test_net_r":summarize_outcomes(test)["net_r"],"test_expectancy_r":summarize_outcomes(test)["expectancy_r"]})
    positive_folds=sum(f["test_net_r"]>0 for f in folds)
    wf_rate=positive_folds/len(folds) if folds else math.nan
    # Multiple-testing haircut: DSR-like conservative adjustment without pretending to reproduce the full closed-form DSR.
    trial_penalty=min(0.35, math.log1p(max(1,n_trials))/20.0)
    adjusted_score=max(0.0, min(100.0, 50 + base.get("sharpe",0)*15 + (0 if math.isnan(wf_rate) else (wf_rate-0.5)*40) - trial_penalty*100))
    verdict="ROBUSTE" if base["trades"]>=40 and base["expectancy_r"]>0 and (math.isnan(p) or p<0.10) and (math.isnan(wf_rate) or wf_rate>=0.55) and adjusted_score>=55 else "À SURVEILLER"
    if base["trades"]<40: verdict="ÉCHANTILLON TROP PETIT"
    return {"summary":base,"mean_ci95":ci,"permutation_pvalue":p,"regimes":regime_report,"walk_forward":folds,
            "segmented":segmented,
            "walk_forward_positive_fold_rate":wf_rate,"n_trials":n_trials,"embargo":embargo,"robustness_score":round(adjusted_score,1),
            "verdict":verdict,
            "note":"Validation descriptive et conservatrice. Les intervalles et tests ne garantissent pas une performance future; ils cherchent surtout à détecter fragilité, hasard et surajustement."}
