"""Hierarchical decision engine. Direction is a scenario, not a price prediction."""
from __future__ import annotations
from typing import Dict, Any


def decide(result: Dict[str,Any], regime: Dict[str,Any], data_quality: Dict[str,Any], macro_risk: str = "NORMAL", liquidity: Dict[str,Any] | None = None) -> Dict[str,Any]:
    direction=result.get("decision", result.get("direction","NEUTRE"))
    hard=[]; soft=[]
    if not data_quality.get("ok",False) or data_quality.get("score",0)<70: hard.append("Qualité des données insuffisante.")
    if regime.get("base") == "RANGE" and direction in {"ACHAT","VENTE"}: soft.append("Marché en range: privilégier les extrêmes et éviter les poursuites de mouvement.")
    if regime.get("volatility") == "EXPANSION": soft.append("Expansion de volatilité: attendre une confirmation et élargir l'invalidation si nécessaire.")
    if macro_risk in {"BLOQUÉ / CHOC MACRO","TRÈS ÉLEVÉ"}: hard.append(f"Risque macro {macro_risk}.")
    if direction not in {"ACHAT","VENTE"}: hard.append("Aucun scénario directionnel suffisamment structuré.")
    if direction in {"ACHAT","VENTE"}:
        lq=liquidity or {}
        if not lq.get("ok",False): hard.append("Analyse de liquidité indisponible.")
        elif not lq.get("pools"): hard.append("Aucune zone de liquidité crédible détectée pour le scénario.")
    policy=result.get("policy",{}) or {}
    available_frames=result.get("timeframes",{}) or {}
    required=list(dict.fromkeys([tf for tf in [*policy.get("context",()), *policy.get("structure",()), policy.get("setup"), policy.get("trigger")] if tf and tf in available_frames]))
    usable=[available_frames.get(tf,{}) for tf in required]
    avail=[x for x in usable if x.get("available")]
    setup_tf=policy.get("setup", result.get("execution_timeframe","M15"))
    if not result.get("timeframes",{}).get(setup_tf,{}).get("available"): hard.append("Timeframe d'exécution indisponible.")
    if required and len(avail)<max(2, len(required)-1): hard.append("Couverture multi-timeframe incomplète.")
    status="REJETÉ" if hard else "CANDIDAT" if soft else "CANDIDAT FORT"
    return {"status":status,"hard_blocks":hard,"soft_warnings":soft,"scenario":direction,
            "thesis": "Scénario conditionnel, pas une prédiction: le trade n'est autorisé que si les barrières de risque et de qualité restent valides au moment de l'exécution.",
            "note":"Le moteur ne transforme jamais un score de qualité en probabilité de gain."}
