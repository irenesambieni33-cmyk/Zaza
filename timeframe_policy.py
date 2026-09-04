"""Relative multi-timeframe policy for RE-ZERO.
The execution timeframe is user-selected and is never silently changed.
"""
from __future__ import annotations
from typing import Dict, List

EXECUTION_TIMEFRAMES = ("M5", "M15", "M30", "H1", "H4", "D1")

POLICY = {
    "M5":  {"context": ("H1", "H4", "D1"), "structure": ("M15", "H1"), "setup": "M5",  "trigger": "M1"},
    "M15": {"context": ("H1", "H4", "D1"), "structure": ("H1", "M30"), "setup": "M15", "trigger": "M5"},
    "M30": {"context": ("H4", "D1"), "structure": ("H1",), "setup": "M30", "trigger": "M15"},
    "H1":  {"context": ("H4", "D1"), "structure": ("H4",), "setup": "H1",  "trigger": "M15"},
    "H4":  {"context": ("W1", "D1"), "structure": ("D1",), "setup": "H4",  "trigger": "H1"},
    "D1":  {"context": ("W1",), "structure": ("W1",), "setup": "D1",  "trigger": "H4"},
}

# Yahoo Finance supports these directly in the current acquisition layer.
DATA_TIMEFRAMES = ("M5", "M15", "M30", "H1", "H4", "D1")


def get_policy(execution_tf: str) -> Dict:
    execution_tf = str(execution_tf).upper()
    if execution_tf not in POLICY:
        raise ValueError(f"Timeframe d'exécution non autorisé : {execution_tf}")
    return {"execution": execution_tf, **POLICY[execution_tf]}


def required_data_timeframes(execution_tf: str) -> List[str]:
    p = get_policy(execution_tf)
    # W1 is optional for now because the current provider layer has no W1 fetch.
    ordered = list(dict.fromkeys([*p["context"], *p["structure"], p["setup"], p["trigger"]]))
    return [tf for tf in ordered if tf in DATA_TIMEFRAMES]


def profile_label(execution_tf: str) -> str:
    p = get_policy(execution_tf)
    return f"{execution_tf} | contexte {', '.join(p['context'])} | structure {', '.join(p['structure'])} | setup {p['setup']} | trigger {p['trigger']}"
