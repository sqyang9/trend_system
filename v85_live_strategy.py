#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v85_live_strategy.py
Replay the research state machine on latest data to derive the live target position.
"""

from __future__ import annotations

import contextlib
import io
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_intrabar_backtest import (
    IntrabarBacktestEngine,
    V85Params,
    calc_long_score,
    calc_short_score,
    check_entry_conditions,
)


@dataclass
class StrategyTarget:
    symbol: str
    asof_5m: str
    latest_4h_bar: str
    signal_bar_4h: str
    last_price: float
    equity_basis_usdt: float
    target_side: str
    target_contracts: float
    target_notional: float
    remaining_fraction: float
    long_score: int
    short_score: int
    long_signal: bool
    short_signal: bool
    completed_4h_bar: bool
    live_position_state: Dict

    def to_dict(self) -> Dict:
        return asdict(self)


def _prepare_data(data_dir: Path, refresh_data: bool) -> Tuple[pd.DataFrame, pd.DataFrame]:
    loader = DataLoader5m(str(data_dir))

    if refresh_data:
        df_5m = loader.fetch_5m_data()
        loader.resample_to_1h(df_5m)
        df_4h = loader.resample_to_4h(df_5m)
    else:
        df_5m, df_4h = loader.load_data()

    df_5m = df_5m.copy()
    df_4h = df_4h.copy()
    df_5m["timestamp"] = pd.to_datetime(df_5m["timestamp"], utc=True)
    df_4h["timestamp"] = pd.to_datetime(df_4h["timestamp"], utc=True)
    df_5m = df_5m.sort_values("timestamp").reset_index(drop=True)
    df_4h = df_4h.sort_values("timestamp").reset_index(drop=True)
    return df_5m, df_4h


def _last_4h_bar_is_complete(last_5m_ts: pd.Timestamp, last_4h_ts: pd.Timestamp) -> bool:
    required_last_5m = last_4h_ts + pd.Timedelta(hours=4) - pd.Timedelta(minutes=5)
    return last_5m_ts >= required_last_5m


def compute_strategy_target(
    data_dir: str | Path,
    equity_usdt: float,
    *,
    params: V85Params | None = None,
    symbol: str = "BTC/USDT:USDT",
    refresh_data: bool = False,
    use_intrabar_stop: bool = True,
    allow_short: bool = True,
) -> StrategyTarget:
    params = params or V85Params()
    data_dir = Path(data_dir)
    df_5m, df_4h = _prepare_data(data_dir, refresh_data)

    if len(df_5m) < 100 or len(df_4h) < 5:
        raise RuntimeError("insufficient data for live strategy replay")

    last_5m_ts = pd.Timestamp(df_5m["timestamp"].iloc[-1])
    if last_5m_ts.tzinfo is None:
        last_5m_ts = last_5m_ts.tz_localize("UTC")
    else:
        last_5m_ts = last_5m_ts.tz_convert("UTC")

    last_4h_ts = pd.Timestamp(df_4h["timestamp"].iloc[-1])
    if last_4h_ts.tzinfo is None:
        last_4h_ts = last_4h_ts.tz_localize("UTC")
    else:
        last_4h_ts = last_4h_ts.tz_convert("UTC")
    completed_4h_bar = _last_4h_bar_is_complete(last_5m_ts, last_4h_ts)

    engine = IntrabarBacktestEngine(params, use_intrabar_stop=use_intrabar_stop)
    with contextlib.redirect_stdout(io.StringIO()):
        result = engine.run(
            df_5m,
            df_4h,
            close_on_end=False,
            allow_entry_on_last_bar=completed_4h_bar,
        )

    signals = result["signals"]
    if len(signals) < 3:
        raise RuntimeError("insufficient 4h bars after indicator preparation")

    if completed_4h_bar:
        signal_row = signals.iloc[-1]
        prev_signal_row = signals.iloc[-2]
        signal_bar_time = signals.index[-1]
    else:
        signal_row = signals.iloc[-2]
        prev_signal_row = signals.iloc[-3]
        signal_bar_time = signals.index[-2]

    long_score = int(calc_long_score(signal_row, prev_signal_row))
    short_score = int(calc_short_score(signal_row, prev_signal_row))
    long_signal, short_signal = check_entry_conditions(signal_row, prev_signal_row, params, False)

    pos_state = dict(result.get("final_position") or {})
    last_price = float(df_5m["close"].iloc[-1])
    equity_basis = float(max(equity_usdt, 0.0))

    target_side = "flat"
    remaining_fraction = 0.0
    target_contracts = 0.0

    if pos_state:
        target_side = str(pos_state.get("direction", "flat"))
        initial_qty = float(pos_state.get("initial_qty", 0.0) or 0.0)
        current_qty = float(pos_state.get("current_qty", 0.0) or 0.0)
        remaining_fraction = (current_qty / initial_qty) if initial_qty > 0 else 0.0

        base_contracts = 0.0
        if equity_basis > 0 and last_price > 0:
            base_contracts = equity_basis * (params.position_pct / 100.0) / last_price

        target_contracts = base_contracts * remaining_fraction
        if target_side == "short":
            target_contracts *= -1.0

    if (not allow_short) and target_contracts < 0:
        target_side = "flat"
        target_contracts = 0.0
        remaining_fraction = 0.0

    return StrategyTarget(
        symbol=symbol,
        asof_5m=last_5m_ts.isoformat(),
        latest_4h_bar=last_4h_ts.isoformat(),
        signal_bar_4h=(pd.Timestamp(signal_bar_time).tz_localize("UTC") if pd.Timestamp(signal_bar_time).tzinfo is None else pd.Timestamp(signal_bar_time).tz_convert("UTC")).isoformat(),
        last_price=last_price,
        equity_basis_usdt=equity_basis,
        target_side=target_side,
        target_contracts=float(target_contracts),
        target_notional=float(abs(target_contracts) * last_price),
        remaining_fraction=float(remaining_fraction),
        long_score=long_score,
        short_score=short_score,
        long_signal=bool(long_signal),
        short_signal=bool(short_signal),
        completed_4h_bar=bool(completed_4h_bar),
        live_position_state=pos_state,
    )

