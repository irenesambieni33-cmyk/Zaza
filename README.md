# RE-ZERO V5.2

Multi-asset, multi-timeframe market-analysis assistant with liquidity-first reasoning, conservative risk gates, paper-trade management and event-based notifications.

**Execution timeframes:** M5, M15, M30, H1, H4, D1. The selected timeframe is never silently changed.

**Risk controls:** minimum R:R 1:2, maximum 3 trades/day, one active paper trade at a time, no forced trade, session window configurable around 3–4 hours.

**Primary logic:** data quality → regime → MTF context → liquidity → structure → momentum/orderflow → macro → setup quality → RR/risk → decision.

**Execution:** broker execution is disabled by default. Use analysis and paper trading before any future live integration.

**Deployment:** upload/extract the complete V5.2 file set into the repository root. Do not mix V5.2 `app.py` with older modules.
