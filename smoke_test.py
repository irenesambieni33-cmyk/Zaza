"""Local RE-ZERO smoke tests. Requires only project Python dependencies (pandas/numpy)."""
import time
import numpy as np
import pandas as pd

from config import EXECUTION_TIMEFRAMES, MAX_TRADES_PER_DAY, MIN_RR
from timeframe_policy import get_policy
from analysis import analyze_multi_timeframe
from decision_engine import decide
from risk import build_setup
from trade_manager import TradeManager, ManagedTrade


def make_frames():
    idx = pd.date_range("2026-01-01", periods=420, freq="5min")
    x = np.arange(len(idx))
    close = 100 + 0.02*x + 2*np.sin(x/18)
    open_ = close - 0.1*np.cos(x/5)
    high = np.maximum(open_, close) + 0.25
    low = np.minimum(open_, close) - 0.25
    volume = np.full(len(idx), 1000.0)
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)
    def agg(rule):
        return df.resample(rule).agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
    return {"M5": df, "M15": agg("15min"), "M30": agg("30min"), "H1": agg("1h"), "H4": agg("4h"), "D1": agg("1D")}


def main():
    frames = make_frames()
    assert EXECUTION_TIMEFRAMES == ("M5", "M15", "M30", "H1", "H4", "D1")
    for tf in EXECUTION_TIMEFRAMES:
        p = get_policy(tf)
        assert p["execution"] == tf and p["setup"] == tf
        result = analyze_multi_timeframe(frames, tf)
        assert result["execution_timeframe"] == tf
        assert result["setup_timeframe"] == tf
        assert result["timeframes"][tf]["available"]
        assert "liquidity" in result["timeframes"][tf]
    # RR gate
    valid = build_setup(100.0, 1.0, {"swings":{"highs":[],"lows":[]}}, "ACHAT", {"supports":[],"resistances":[]})
    assert valid["valid"] and valid["rr1"] >= MIN_RR
    # Daily trade ceiling
    tm = TradeManager(); now = time.time()
    for i in range(MAX_TRADES_PER_DAY):
        tm.history.append(ManagedTrade("EUR/USD","ACHAT",1,.9,1.2,1.4,1,80,"A",opened_at=now-i*60,status="CLOSED",closed_at=now-i*30,pnl=1))
    assert tm.trades_today() == MAX_TRADES_PER_DAY and not tm.can_open()
    # Liquidity gate blocks directional decisions without a credible map.
    blocked = decide({"decision":"ACHAT","policy":{"context":("D1",),"structure":("H1",),"setup":"M5","trigger":"M1"},"timeframes":{"D1":{"available":True},"H1":{"available":True},"M5":{"available":True}}}, {"base":"TREND","volatility":"NORMAL"}, {"ok":True,"score":90}, "NORMAL", liquidity={"ok":False,"pools":[]})
    assert blocked["status"] == "REJETÉ"
    print("RE-ZERO SMOKE TEST: PASS")


if __name__ == "__main__":
    main()
