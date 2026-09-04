"""Final safety gate before any future broker order."""
from __future__ import annotations
from typing import Dict, Any
import math
from config import MAX_OPEN_RISK, MIN_RR, RISK_PER_TRADE


def safety_gate(setup: Dict[str, Any] | None, quality: Dict[str, Any] | None, capital: float,
                daily_loss: float = 0.0, open_risk_fraction: float = 0.0,
                spread_pct: float | None = None, max_spread_pct: float = 0.0025) -> Dict[str, Any]:
    checks = {}
    setup_ok = bool(setup and setup.get("valid"))
    checks["setup_valide"] = setup_ok
    checks["qualite_minimale"] = bool(quality and quality.get("approved"))
    checks["capital_positif"] = float(capital or 0) > 0
    checks["rr_minimum"] = bool(setup and float(setup.get("rr1", 0)) >= MIN_RR)
    checks["risque_trade_max_1pct"] = RISK_PER_TRADE <= 0.01
    checks["risque_ouvert_max_2pct"] = open_risk_fraction + RISK_PER_TRADE <= MAX_OPEN_RISK
    checks["perte_journaliere_non_depassee"] = daily_loss < float(capital or 0) * MAX_OPEN_RISK
    checks["prix_et_niveaux_finis"] = bool(setup and all(math.isfinite(float(setup.get(k, 0))) for k in ("entry", "sl", "tp1", "tp2")))
    checks["spread"] = spread_pct is None or (math.isfinite(float(spread_pct)) and float(spread_pct) <= max_spread_pct)
    checks["execution_desactivee_par_defaut"] = True
    return {
        "approved": all(checks.values()),
        "checks": checks,
        "mode": "ANALYSE",
        "message": "Safety Gate : aucune exécution broker n'est autorisée par défaut.",
    }
