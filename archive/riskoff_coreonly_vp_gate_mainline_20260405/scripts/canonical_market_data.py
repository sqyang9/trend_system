#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical local market-data root for the current BTC mainline."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime


REPO_ROOT = Path(__file__).resolve().parent
DASHBOARD_DATA = REPO_ROOT / "dashboard" / "data"
ROOT_DATA = REPO_ROOT / "data"
REQUIRED_FILES = ("btc_usdt_swap_5m.csv", "btc_usdt_swap_4h.csv")


def canonical_market_data_dir() -> Path:
    if all((DASHBOARD_DATA / name).exists() for name in REQUIRED_FILES):
        return DASHBOARD_DATA
    return ROOT_DATA


def canonical_market_data_label() -> str:
    path = canonical_market_data_dir()
    if path == DASHBOARD_DATA:
        return "dashboard/data"
    return "data"


def load_canonical_market_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    loader = DataLoader5m(str(canonical_market_data_dir()))
    df_5m, df_4h = loader.load_data()
    return ensure_datetime(df_5m), ensure_datetime(df_4h)
