#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared volatility background utilities for mainline and live layers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from v85_research_suite_v2 import ensure_datetime


ATR_LEN = 14
HV_LOOKBACK_BARS = 14 * 6
HV_PCTL_LOOKBACK_BARS = 180 * 6
DEFAULT_ATR_REF_DAYS = 180
DEFAULT_ATR_REF_STAT = "median"
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


def normalize_atrvt_spec(spec: dict | None = None) -> dict:
    raw = {} if spec is None else dict(spec)
    ref_days = int(raw.get("atr_ref_days", DEFAULT_ATR_REF_DAYS))
    ref_stat = str(raw.get("atr_ref_stat", DEFAULT_ATR_REF_STAT)).lower()
    if ref_stat not in {"median", "mean"}:
        raise ValueError(f"Unsupported ATRVT ref stat: {ref_stat}")
    scale_min = float(raw.get("atr_scale_min", ATR_SCALE_MIN))
    scale_max = float(raw.get("atr_scale_max", ATR_SCALE_MAX))
    return {
        "atr_ref_days": ref_days,
        "atr_ref_stat": ref_stat,
        "atr_scale_min": scale_min,
        "atr_scale_max": scale_max,
    }


def atrvt_label(spec: dict | None = None) -> str:
    cfg = normalize_atrvt_spec(spec)
    stat = "med" if cfg["atr_ref_stat"] == "median" else "mean"
    low = f"{cfg['atr_scale_min']:.2f}".replace(".", "")
    high = f"{cfg['atr_scale_max']:.2f}".replace(".", "")
    return f"ATRVT_{cfg['atr_ref_days']}D_{stat}_{low}_{high}"


def normalize_atrvt_contract(contract: dict | None = None) -> dict:
    raw = {} if contract is None else dict(contract)
    if "atrvt_s1_spec" in raw and "atrvt_s2_spec" in raw:
        s1 = normalize_atrvt_spec(raw["atrvt_s1_spec"])
        s2 = normalize_atrvt_spec(raw["atrvt_s2_spec"])
        return {
            "atrvt_s1_spec": s1,
            "atrvt_s2_spec": s2,
            "atrvt_s1_label": atrvt_label(s1),
            "atrvt_s2_label": atrvt_label(s2),
        }
    if any(k.startswith("atrvt_s1_") or k.startswith("atrvt_s2_") for k in raw):
        s1 = normalize_atrvt_spec(
            {
                "atr_ref_days": raw.get("atrvt_s1_ref_days", raw.get("atr_ref_days", DEFAULT_ATR_REF_DAYS)),
                "atr_ref_stat": raw.get("atrvt_s1_ref_stat", raw.get("atr_ref_stat", DEFAULT_ATR_REF_STAT)),
                "atr_scale_min": raw.get("atrvt_s1_scale_min", raw.get("atr_scale_min", ATR_SCALE_MIN)),
                "atr_scale_max": raw.get("atrvt_s1_scale_max", raw.get("atr_scale_max", ATR_SCALE_MAX)),
            }
        )
        s2 = normalize_atrvt_spec(
            {
                "atr_ref_days": raw.get("atrvt_s2_ref_days", raw.get("atr_ref_days", DEFAULT_ATR_REF_DAYS)),
                "atr_ref_stat": raw.get("atrvt_s2_ref_stat", raw.get("atr_ref_stat", DEFAULT_ATR_REF_STAT)),
                "atr_scale_min": raw.get("atrvt_s2_scale_min", raw.get("atr_scale_min", ATR_SCALE_MIN)),
                "atr_scale_max": raw.get("atrvt_s2_scale_max", raw.get("atr_scale_max", ATR_SCALE_MAX)),
            }
        )
    else:
        shared = normalize_atrvt_spec(raw)
        s1 = dict(shared)
        s2 = dict(shared)
    return {
        "atrvt_s1_spec": s1,
        "atrvt_s2_spec": s2,
        "atrvt_s1_label": atrvt_label(s1),
        "atrvt_s2_label": atrvt_label(s2),
    }


def atrvt_contract_label(contract: dict | None = None) -> str:
    cfg = normalize_atrvt_contract(contract)
    if cfg["atrvt_s1_label"] == cfg["atrvt_s2_label"]:
        return cfg["atrvt_s1_label"]
    return f"{cfg['atrvt_s1_label']}__{cfg['atrvt_s2_label']}"


def build_volatility_background(
    df_4h: pd.DataFrame,
    atr_len: int = ATR_LEN,
    hv_lookback_bars: int = HV_LOOKBACK_BARS,
    hv_pctl_lookback_bars: int = HV_PCTL_LOOKBACK_BARS,
    atr_ref_days: int = DEFAULT_ATR_REF_DAYS,
    atr_ref_stat: str = DEFAULT_ATR_REF_STAT,
    atr_scale_min: float = ATR_SCALE_MIN,
    atr_scale_max: float = ATR_SCALE_MAX,
) -> pd.DataFrame:
    cfg = normalize_atrvt_spec(
        {
            "atr_ref_days": atr_ref_days,
            "atr_ref_stat": atr_ref_stat,
            "atr_scale_min": atr_scale_min,
            "atr_scale_max": atr_scale_max,
        }
    )
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    atr = compute_atr(d4.reset_index(), atr_len)
    atr.index = d4.index
    atr_pct = (atr / d4["close"].astype(float)).replace([np.inf, -np.inf], np.nan)
    atr_ref_bars = int(cfg["atr_ref_days"]) * 6
    atr_min_periods = max(60, atr_ref_bars // 4)
    if cfg["atr_ref_stat"] == "median":
        atr_target_pct = atr_pct.rolling(atr_ref_bars, min_periods=atr_min_periods).median().shift(1)
    else:
        atr_target_pct = atr_pct.rolling(atr_ref_bars, min_periods=atr_min_periods).mean().shift(1)
    atr_scale = (atr_target_pct / atr_pct).clip(lower=cfg["atr_scale_min"], upper=cfg["atr_scale_max"])
    atr_scale = atr_scale.replace([np.inf, -np.inf], np.nan).fillna(1.0)

    log_ret = np.log(d4["close"].astype(float) / d4["close"].astype(float).shift(1))
    hv_ann = log_ret.rolling(hv_lookback_bars, min_periods=30).std() * np.sqrt(6.0 * 365.0)
    hv_pct_180d = rolling_last_percentile(hv_ann, hv_pctl_lookback_bars)

    out = pd.DataFrame(index=d4.index)
    out["close"] = d4["close"].astype(float)
    out["atr14"] = atr.astype(float)
    out["atr_pct"] = atr_pct.astype(float)
    out["atr_ref_days"] = float(cfg["atr_ref_days"])
    out["atr_ref_stat"] = cfg["atr_ref_stat"]
    out["atr_scale_min"] = float(cfg["atr_scale_min"])
    out["atr_scale_max"] = float(cfg["atr_scale_max"])
    out["atrvt_label"] = atrvt_label(cfg)
    out["atr_target_pct"] = atr_target_pct.astype(float)
    out["atr_target_pct_180d_med"] = atr_target_pct.astype(float)
    out["atr_scale"] = atr_scale.astype(float)
    out["hv14_ann"] = hv_ann.astype(float)
    out["hv_pct_180d"] = hv_pct_180d.astype(float)
    out["hv_ge_85"] = (out["hv_pct_180d"] >= 0.85).fillna(False)
    out["hv_ge_90"] = (out["hv_pct_180d"] >= 0.90).fillna(False)
    return out
