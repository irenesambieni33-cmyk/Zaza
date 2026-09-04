"""Market-data acquisition, cleaning and timeframe construction."""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import pandas as pd
import yfinance as yf

from config import INSTRUMENTS, MIN_BARS, PERIODS, TIMEFRAMES, YF_INTERVALS

LOGGER = logging.getLogger(__name__)


def _clean_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [c[0] if isinstance(c, tuple) else c for c in out.columns]
    out.columns = [str(c).strip().lower() for c in out.columns]
    required = ["open", "high", "low", "close"]
    if any(c not in out.columns for c in required):
        return pd.DataFrame()
    if "volume" not in out.columns:
        out["volume"] = 0.0
    out = out[required + ["volume"]].copy()
    for col in out.columns:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=required)
    out = out[(out["high"] >= out[["open", "close"]].max(axis=1)) &
              (out["low"] <= out[["open", "close"]].min(axis=1))]
    out = out[~out.index.duplicated(keep="last")].sort_index()
    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_convert("UTC").tz_localize(None)
    return out


def _download(ticker: str, interval: str, period: str) -> pd.DataFrame:
    try:
        raw = yf.download(
            ticker, period=period, interval=interval, auto_adjust=False,
            progress=False, threads=False, group_by="column",
        )
        return _clean_ohlcv(raw)
    except Exception as exc:
        LOGGER.warning("Yahoo download failed: %s %s %s: %s", ticker, interval, period, exc)
        return pd.DataFrame()


def _resample_h4(hourly: pd.DataFrame) -> pd.DataFrame:
    if hourly.empty:
        return hourly
    # UTC timestamps are used so the aggregation boundary is deterministic.
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    h4 = hourly.resample("4h", origin="epoch", label="right", closed="right").agg(agg)
    return h4.dropna(subset=["open", "high", "low", "close"])


def fetch_timeframe(ticker: str, timeframe: str) -> Tuple[pd.DataFrame, Optional[str]]:
    if timeframe not in TIMEFRAMES:
        return pd.DataFrame(), f"Timeframe inconnu : {timeframe}."
    raw = _download(ticker, YF_INTERVALS[timeframe], PERIODS[timeframe])
    df = _resample_h4(raw) if timeframe == "H4" else raw
    if df.empty:
        return df, f"Aucune donnée disponible pour {timeframe}."
    if len(df) < MIN_BARS:
        return df, f"Données limitées pour {timeframe} ({len(df)} bougies). Analyse partielle."
    return df, None


def fetch_instrument(name: str) -> Tuple[Dict[str, pd.DataFrame], Dict[str, str], bool]:
    meta = INSTRUMENTS[name]
    frames: Dict[str, pd.DataFrame] = {}
    warnings: Dict[str, str] = {}
    for tf in TIMEFRAMES:
        df, warning = fetch_timeframe(meta["ticker"], tf)
        if not df.empty:
            frames[tf] = df
        if warning:
            warnings[tf] = warning

    used_proxy = False
    # XAU fallback is triggered when spot data is broadly unusable, not merely because one TF failed.
    if name == "XAU/USD" and meta.get("proxy") and len(frames) < 3:
        proxy_frames: Dict[str, pd.DataFrame] = {}
        proxy_warnings: Dict[str, str] = {}
        for tf in TIMEFRAMES:
            df, warning = fetch_timeframe(meta["proxy"], tf)
            if not df.empty:
                proxy_frames[tf] = df
            if warning:
                proxy_warnings[tf] = warning
        if len(proxy_frames) > len(frames):
            frames, warnings, used_proxy = proxy_frames, proxy_warnings, True

    if not frames:
        warnings["global"] = f"Impossible de récupérer les données Yahoo Finance pour {meta['ticker']}."
    return frames, warnings, used_proxy
