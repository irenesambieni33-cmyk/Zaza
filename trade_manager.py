"""Persistent trade manager. One active position, followed until TP2 or SL."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from config import MAX_TRADES_PER_DAY
import time
from datetime import datetime, timezone
from performance import summarize_trades

@dataclass
class ManagedTrade:
    symbol: str
    direction: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    units: float
    quality_score: float
    grade: str
    liquidity_note: str = ""
    opened_at: float = 0.0
    status: str = "OPEN"
    current_price: float | None = None
    exit_price: float | None = None
    closed_at: float | None = None
    pnl: float | None = None
    exit_reason: str | None = None
    max_favorable_r: float = 0.0
    max_adverse_r: float = 0.0
    last_health: str = "EN SUIVI"
    last_health_note: str = ""

class TradeManager:
    def __init__(self):
        self.active: Optional[ManagedTrade] = None
        self.history: List[ManagedTrade] = []
        self.last_event: str = ""

    def trades_today(self) -> int:
        today = datetime.now(timezone.utc).date()
        n = sum(1 for t in self.history if datetime.fromtimestamp(t.opened_at, timezone.utc).date() == today)
        if self.active is not None and datetime.fromtimestamp(self.active.opened_at, timezone.utc).date() == today:
            n += 1
        return n

    def can_open(self) -> bool:
        return self.active is None and self.trades_today() < MAX_TRADES_PER_DAY

    def open(self, symbol: str, setup: Dict[str, Any], units: float, quality: Dict[str, Any], liquidity_note: str = "") -> Dict[str, Any]:
        if self.active is not None:
            return {"ok": False, "reason": "Une position est déjà active. Aucun nouveau trade n'est autorisé."}
        if self.trades_today() >= MAX_TRADES_PER_DAY:
            return {"ok": False, "reason": "Limite quotidienne de 3 trades atteinte."}
        if symbol not in {"BTC/USD", "EUR/USD", "XAU/USD"}:
            return {"ok": False, "reason": "Instrument non supporté."}
        if not setup or not setup.get("valid") or units <= 0 or not quality.get("approved"):
            return {"ok": False, "reason": "Setup, taille ou qualité insuffisante."}
        self.active = ManagedTrade(symbol=symbol, direction=setup["direction"], entry=float(setup["entry"]),
                                   sl=float(setup["sl"]), tp1=float(setup["tp1"]), tp2=float(setup["tp2"]),
                                   units=float(units), quality_score=float(quality.get("score", 0)),
                                   grade=str(quality.get("grade", "REJETÉ")), liquidity_note=liquidity_note,
                                   opened_at=time.time(), current_price=float(setup["entry"]))
        self.last_event = f"Position BTC/USD {setup['direction']} ouverte en PAPER. Suivi verrouillé."
        return {"ok": True, "trade": asdict(self.active)}

    def update(self, symbol: str, price: float, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if self.active is None or self.active.symbol != symbol:
            return {"ok": True, "active": False, "event": None}
        t = self.active; p = float(price); t.current_price = p
        risk = abs(t.entry - t.sl); sign = 1.0 if t.direction == "ACHAT" else -1.0
        r_now = sign * (p - t.entry) / risk if risk > 0 else 0.0
        t.max_favorable_r = max(t.max_favorable_r, r_now); t.max_adverse_r = min(t.max_adverse_r, r_now)
        context = context or {}
        # Health describes the scenario but NEVER closes the trade by opinion. TP/SL remain the exit rules.
        momentum = str(context.get("momentum", "INCONNU")); trend = str(context.get("trend", "INCONNU")); liquidity = str(context.get("liquidity", "INCONNU")); vol = str(context.get("volatility", "INCONNU"))
        favorable = 0; unfavorable = 0
        for value in (momentum, trend, liquidity):
            if any(k in value.upper() for k in ("FAVORABLE","HAUSSIER","BAISSIER","FORT","POSITIVE","OK","SUPPORT")): favorable += 1
            if any(k in value.upper() for k in ("DÉFAVORABLE","DEFAVORABLE","FAIBLE","CONTRE","RUPTURE")): unfavorable += 1
        if r_now >= 1: favorable += 1
        if r_now < -0.5: unfavorable += 1
        if unfavorable >= 2: t.last_health = "⚠️ SOUS PRESSION"
        elif favorable >= 2: t.last_health = "🟢 SCÉNARIO FAVORABLE"
        else: t.last_health = "🟡 EN SUIVI"
        t.last_health_note = f"Tendance: {trend} • Momentum: {momentum} • Liquidité: {liquidity} • Volatilité: {vol} • R: {r_now:+.2f}"
        hit = None; reason = None
        if t.direction == "ACHAT":
            if p <= t.sl: hit, reason = t.sl, "SL"
            elif p >= t.tp2: hit, reason = t.tp2, "TP2"
        else:
            if p >= t.sl: hit, reason = t.sl, "SL"
            elif p <= t.tp2: hit, reason = t.tp2, "TP2"
        if hit is not None:
            t.exit_price=float(hit); t.closed_at=time.time(); t.status="CLOSED"; t.exit_reason=reason
            t.pnl=(t.exit_price-t.entry)*t.units*sign; self.history.append(t); self.active=None
            self.last_event=f"{symbol} : {reason} atteint à {hit:.2f}. Trade terminé. Nouveau scan autorisé."
            return {"ok":True,"active":False,"closed":True,"event":reason,"trade":asdict(t)}
        return {"ok":True,"active":True,"closed":False,"event":"SUIVI","trade":asdict(t),"r_now":r_now,"health":t.last_health,"health_note":t.last_health_note}

    def snapshot(self) -> Dict[str, Any]:
        return {"active": asdict(self.active) if self.active else None, "history":[asdict(x) for x in self.history], "last_event":self.last_event, "performance":summarize_trades(self.history)}
