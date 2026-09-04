"""Optional public crypto microstructure snapshot for RE-ZERO.
No API key is required. If the public exchange endpoint is unavailable,
the core BTC analysis continues using the primary market-data source.
"""
from __future__ import annotations
import json
import urllib.parse
import urllib.request


def _get(url, timeout=5):
    req=urllib.request.Request(url, headers={"User-Agent":"RE-ZERO/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_btc_snapshot():
    out={"ok":False,"source":"public exchange snapshot"}
    try:
        base="https://api.binance.com"
        ticker=_get(base+"/api/v3/ticker/24hr?symbol=BTCUSDT")
        book=_get(base+"/api/v3/depth?symbol=BTCUSDT&limit=100")
        bids=sum(float(x[1]) for x in book.get("bids",[])); asks=sum(float(x[1]) for x in book.get("asks",[])); total=bids+asks
        out.update({"ok":True,"last":float(ticker["lastPrice"]),"change_pct":float(ticker["priceChangePercent"]),"volume_btc":float(ticker["volume"]),"high_24h":float(ticker["highPrice"]),"low_24h":float(ticker["lowPrice"]),"bid_volume":bids,"ask_volume":asks,"orderbook_imbalance":(bids-asks)/total if total else 0.0})
    except Exception as exc:
        out["error"]=str(exc)
    return out
