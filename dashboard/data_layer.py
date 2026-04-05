#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Data loading layer for the dashboard package."""

from __future__ import annotations

import contextlib
import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2
from typing import Dict, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime

DASHBOARD_ROOT = Path(__file__).resolve().parent
DASHBOARD_DATA = DASHBOARD_ROOT / "data"
ROOT_DATA = REPO_ROOT / "data"
BOOTSTRAP_FILES = [
    "btc_usdt_swap_5m.csv",
    "btc_usdt_swap_1h.csv",
    "btc_usdt_swap_4h.csv",
]


def ensure_dashboard_data() -> None:
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    for name in BOOTSTRAP_FILES:
        src = ROOT_DATA / name
        dst = DASHBOARD_DATA / name
        if not dst.exists() and src.exists():
            copy2(src, dst)


def strict_refresh() -> None:
    ensure_dashboard_data()
    missing = [name for name in BOOTSTRAP_FILES if not (DASHBOARD_DATA / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"dashboard bootstrap data missing: {missing}. "
            f"Expected local seed files under {DASHBOARD_DATA} or repo data bootstrap."
        )
    if os.environ.get("DASHBOARD_USE_CACHE_ONLY", "0") == "1":
        return

    loader = DataLoader5m(str(DASHBOARD_DATA))
    try:
        loader.fetch_5m_data(force=False)
        loader.fetch_direct_timeframe_data("1h", force=False)
        loader.fetch_direct_timeframe_data("4h", force=False)
        loader.fetch_direct_timeframe_data("1d", force=False)
    except Exception:
        if not all((DASHBOARD_DATA / name).exists() for name in BOOTSTRAP_FILES):
            raise


def load_market_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    strict_refresh()
    df_5m = pd.read_csv(DASHBOARD_DATA / "btc_usdt_swap_5m.csv")
    df_4h = pd.read_csv(DASHBOARD_DATA / "btc_usdt_swap_4h.csv")
    return ensure_datetime(df_5m), ensure_datetime(df_4h)


def data_freshness_report(df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
    now_utc = pd.Timestamp(datetime.now(timezone.utc))
    last_5m = pd.Timestamp(df_5m["timestamp"].iloc[-1])
    last_4h = pd.Timestamp(df_4h["timestamp"].iloc[-1])
    expected_5m = now_utc.floor("5min")
    expected_4h = now_utc.floor("4h")

    gap_5m = df_5m["timestamp"].diff().dropna().dt.total_seconds().div(60.0)
    gap_4h = df_4h["timestamp"].diff().dropna().dt.total_seconds().div(60.0)
    missing_5m = int((gap_5m > 5.0).sum())
    missing_4h = int((gap_4h > 240.0).sum())

    lag_5m_min = float((expected_5m - last_5m).total_seconds() / 60.0)
    lag_4h_min = float((expected_4h - last_4h).total_seconds() / 60.0)

    return {
        "generated_at_utc": str(now_utc),
        "last_5m_bar_utc": str(last_5m),
        "last_4h_bar_utc": str(last_4h),
        "expected_last_5m_close_utc": str(expected_5m),
        "expected_last_4h_close_utc": str(expected_4h),
        "lag_5m_minutes": lag_5m_min,
        "lag_4h_minutes": lag_4h_min,
        "missing_5m_bar_gaps": missing_5m,
        "missing_4h_bar_gaps": missing_4h,
        "is_stale": bool(lag_5m_min > 15.0 or lag_4h_min > 300.0),
    }


def direct_aux_report() -> Dict:
    report: Dict[str, object] = {}
    file_1h = DASHBOARD_DATA / "btc_usdt_swap_1h.csv"
    file_1d = DASHBOARD_DATA / "btc_usdt_swap_1d.csv"

    if file_1h.exists():
        df_1h = pd.read_csv(file_1h)
        df_1h["timestamp"] = pd.to_datetime(df_1h["timestamp"], utc=True)
        report["last_1h_bar_utc"] = str(df_1h["timestamp"].max())
    if file_1d.exists():
        df_1d = pd.read_csv(file_1d)
        df_1d["timestamp"] = pd.to_datetime(df_1d["timestamp"], utc=True)
        report["last_1d_bar_utc"] = str(df_1d["timestamp"].max())
    return report
