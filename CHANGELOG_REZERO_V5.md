# RE-ZERO V5 - Dynamic MTF / Liquidity / Risk / Notifications

## Implemented
- Dynamic execution timeframe: M5, M15, M30, H1, H4, D1.
- Relative MTF policy with context, structure, setup and trigger layers.
- M30 data acquisition added.
- Decision engine and setup-quality scoring refactored to use selected execution timeframe.
- Liquidity engine upgraded with sweep, reclaim and displacement inference.
- Session controller with 3-4 hour windows and remaining-time display.
- Hard maximum of 3 trades/day in TradeManager.
- R:R minimum remains 1:2.
- Browser notification bridge with permission/HTTPS diagnostics and de-duplication.
- Telegram notification path retained as optional external delivery.
- Dashboard rebuilt around selected timeframe.

## Verification
- `python -m compileall -q .` passed.
- Synthetic smoke tests passed for all six execution timeframes.
- M5 -> setup M5, trigger M1.
- M15 -> setup M15, trigger M5.
- M30 -> setup M30, trigger M15.
- H1 -> setup H1, trigger M15.
- H4 -> setup H4, trigger H1.
- D1 -> setup D1, trigger H4.
- No SHO-pred content is included in the release archive.
