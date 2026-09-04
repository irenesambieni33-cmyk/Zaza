"""Alert engine for in-app and optional Telegram notifications."""
from __future__ import annotations
import json
import time
import urllib.parse
import urllib.request
from typing import Dict, Any


def build_alert(instrument: str, result: Dict[str, Any], quality: Dict[str, Any], gate: Dict[str, Any], timing: Dict[str, Any], setup: Dict[str, Any] | None) -> Dict[str, Any]:
    trade_ready = bool(result.get("decision") in {"ACHAT", "VENTE"} and quality.get("approved") and gate.get("approved") and timing.get("status") == "FENÊTRE FAVORABLE" and setup)
    return {"active": trade_ready, "instrument": instrument, "direction": result.get("decision"), "quality": quality.get("score", 0), "grade": quality.get("grade", "REJETÉ"), "timing_score": timing.get("score", 0),
            "message": f"🚨 OPPORTUNITÉ {instrument} : {result.get('decision')} • Qualité {quality.get('grade')} ({quality.get('score',0):.0f}/100) • Fenêtre {timing.get('score',0):.0f}/100" if trade_ready else "Aucune opportunité suffisamment filtrée maintenant.",
            "setup": setup or {}}


def send_telegram(alert: Dict[str, Any], bot_token: str, chat_id: str) -> Dict[str, Any]:
    if not alert.get("active"):
        return {"ok": False, "reason": "Aucune alerte active."}
    if not bot_token or not chat_id:
        return {"ok": False, "reason": "Telegram non configuré."}
    s = alert.get("setup", {})
    text = (f"RE-ZERO — OPPORTUNITÉ\n{alert['instrument']} {alert['direction']}\n"
            f"Qualité: {alert['grade']} ({alert['quality']:.0f}/100)\n"
            f"Fenêtre: {alert['timing_score']:.0f}/100\n"
            f"Entry: {s.get('entry')} | SL: {s.get('sl')} | TP1: {s.get('tp1')} | TP2: {s.get('tp2')}\n"
            "Alerte d'analyse, pas un ordre broker.")
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage?" + urllib.parse.urlencode({"chat_id": chat_id, "text": text})
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {"ok": bool(data.get("ok"))}
    except Exception as exc:
        return {"ok": False, "reason": f"Échec Telegram: {exc}"}
