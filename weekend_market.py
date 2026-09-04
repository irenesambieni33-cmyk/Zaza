"""Weekend market policy. No broker-specific weekend contract is invented here.
BTC/USD is monitored 24/7; broker-specific weekend contracts require a broker adapter.
"""
from datetime import datetime

def weekend_policy(symbol: str, now=None):
    now = now or datetime.utcnow()
    weekend = now.weekday() >= 5
    if symbol == "BTC/USD":
        return {"weekend": weekend, "available": True, "status": "BTC 24/7", "note": "BTC peut être surveillé le week-end. Les frais/spreads dépendent de la plateforme."}
    return {"weekend": weekend, "available": not weekend, "status": "Marché traditionnel", "note": "EUR/USD et XAU/USD suivent les horaires du marché/broker; pas d'invention d'un contrat week-end."}
