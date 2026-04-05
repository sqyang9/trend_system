#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared volatility background utilities for mainline and live layers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from v85_research_suite_v2 import ensure_datetime


ATR_LEN = 14
HV_LOOKBACK_BARS = 14 * 6
PCTL_LOOKBACK_BARS = 180 * 6
ATR_SCALE_MIN = 0.35
ATR_SCALE_MAX = 1.50


def compute_atr(df_4h: pd.DataFrame, length: int = ATR_LEN) -> pd.Series:
    high = df_4h["high"].astype(float)
    low = df_4h["low"].astype(float)
    close = df_4h["close"].astype(float)
    prev_close = close.shift(1)
    true_range = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def rolling_last_percentile(series: pd.Series, window: int) -> pd.Series:
    def _last_pct(values: np.ndarray) -> float:
        arr = values[np.isfinite(values)]
        if arr.size == 0:
            return np.nan
        last = arr[-1]
        return float((arr <= last).mean())

    return series.rolling(window, min_periods=max(30, window // 5)).apply(_last_pct, raw=True)


def build_volatility_background(
    df_4h: pd.DataFrame,
    atr_len: int = ATR_LEN,
    hv_lookback_bars: int = HV_LOOKBACK_BARS,
    pctl_lookback_bars: int = PCTL_LOOKBACK_BARS,
    atr_scale_min: float = ATR_SCALE_MIN,
    atr_scale_max: float = ATR_SCALE_MAX,
) -> pd.DataFrame:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    atr = compute_atr(d4.reset_index(), atr_len).reindex(d4.index)
    atr_pct = (atr / d4["close"].astype(float)).replace([np.inf, -np.inf], np.nan)
    atr_target_pct = atr_pct.rolling(pctl_lookback_bars, min_periods=120).median().shift(1)
    atr_scale = (atr_target_pct / atr_pct).clip(lower=atr_scale_min, upper=atr_scale_max)
    atr_scale = atr_scale.replace([np.inf, -np.inf], np.nan).fillna(1.0)

    log_ret = np.log(d4["close"].astype(float) / d4["close"].astype(float).shift(1))
    hv_ann = log_ret.rolling(hv_lookback_bars, min_periods=30).std() * np.sqrt(6.0 * 365.0)
    hv_pct_180d = rolling_last_percentile(hv_ann, pctl_lookback_bars)

    out = pd.DataFrame(index=d4.index)
    out["close"] = d4["close"].astype(float)
    out["atr14"] = atr.astype(float)
    out["atr_pct"] = atr_pct.astype(float)
    out["atr_target_pct_180d_med"] = atr_target_pct.astype(float)
    out["atr_scale"] = atr_scale.astype(float)
    out["hv14_ann"] = hv_ann.astype(float)
    out["hv_pct_180d"] = hv_pct_180d.astype(float)
    out["hv_ge_85"] = (out["hv_pct_180d"] >= 0.85).fillna(False)
    out["hv_ge_90"] = (out["hv_pct_180d"] >= 0.90).fillna(False)
    return out
