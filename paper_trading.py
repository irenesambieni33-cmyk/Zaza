"""Minimal deterministic paper-trading ledger. No broker calls."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import List, Dict, Any
import time

@dataclass
class PaperTrade:
    symbol: str
    direction: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    units: float
    status: str = "OPEN"
    opened_at: float = 0.0
    closed_at: float | None = None
    exit_price: float | None = None
    pnl: float | None = None

class PaperLedger:
    def __init__(self):
        self.trades: List[PaperTrade] = []

    def open_trade(self, symbol: str, setup: Dict[str, Any], units: float) -> Dict[str, Any]:
        if not setup.get("valid") or units <= 0:
            return {"ok": False, "reason": "Setup ou taille invalide."}
        trade = PaperTrade(symbol, setup["direction"], float(setup["entry"]), float(setup["sl"]),
                           float(setup["tp1"]), float(setup["tp2"]), float(units), opened_at=time.time())
        self.trades.append(trade)
        return {"ok": True, "trade": asdict(trade)}

    def mark(self, symbol: str, price: float) -> Dict[str, Any]:
        events = []
        for t in self.trades:
            if t.symbol != symbol or t.status != "OPEN":
                continue
            p = float(price)
            hit = None
            if t.direction == "ACHAT":
                if p <= t.sl: hit = t.sl
                elif p >= t.tp2: hit = t.tp2
            else:
                if p >= t.sl: hit = t.sl
                elif p <= t.tp2: hit = t.tp2
            if hit is not None:
                t.status = "CLOSED"; t.closed_at = time.time(); t.exit_price = hit
                sign = 1 if t.direction == "ACHAT" else -1
                t.pnl = (hit - t.entry) * t.units * sign
                events.append(asdict(t))
        return {"events": events, "open": sum(t.status == "OPEN" for t in self.trades)}
