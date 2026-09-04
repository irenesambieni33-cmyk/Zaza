"""Safety gates for RE-ZERO. No broker credentials or order execution are implemented."""
from __future__ import annotations
from typing import Dict
from config import MAX_OPEN_RISK, MIN_RR, RISK_PER_TRADE

SAFE_MODES = ("ANALYSE", "PAPER", "DEMO", "LIVE")

def validate_setup(setup: Dict, capital: float) -> Dict:
    checks = {
        "setup_valide": bool(setup and setup.get("valid")),
        "capital_positif": float(capital or 0) > 0,
        "rr_minimum": bool(setup and setup.get("rr1", 0) >= MIN_RR),
        "risque_par_trade_limite": RISK_PER_TRADE <= 0.01,
        "risque_ouvert_limite": MAX_OPEN_RISK <= 0.02,
        "execution_broker_desactivee": True,
    }
    return {"approved": all(checks.values()), "checks": checks, "mode": "ANALYSE", "message": "Barrière de sécurité RE-ZERO : aucune exécution broker n'est autorisée dans cette version."}
