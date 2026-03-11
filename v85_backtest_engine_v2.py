#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v85_backtest_engine_v2.py
=========================
V85 4H signal + 5m intrabar backtest engine with execution realism.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


@dataclass
class V85Params:
    init_equity: float = 10000.0
    position_pct: float = 60.0
    commission_pct: float = 0.06
    slippage: float = 0.0

    bb_period: int = 20
    squeeze_threshold: float = 0.9
    min_squeeze_candles: int = 4
    short_squeeze_threshold: float = 0.9

    atr_period: int = 14
    initial_stop_atr: float = 2.4
    trail_start_atr: float = 3.0
    trail_offset_atr: float = 2.8
    break_even_atr: float = 1.7

    enable_partial_tp: bool = True
    tp1_atr: float = 2.1
    tp1_pct: float = 30.0
    tp2_atr: float = 3.5
    tp2_pct: float = 30.0

    enable_short: bool = True
    short_only_bear: bool = True

    ema_trend_len: int = 200
    use_env_filter: bool = True
    use_adx_filter: bool = True
    adx_period: int = 11
    adx_trend_level: float = 20.0

    min_long_score: int = 1
    min_short_score: int = 3

    enable_daily_loss_limit: bool = True
    daily_loss_limit_pct: float = 1.5
    cooldown_bars: int = 3

    entry_execution_mode: str = "signal_close"
    close_delay_bps: float = 8.0
    intrabar_path_mode: str = "pessimistic"
    intrabar_execution_model: str = "segment_path_same_bar"
    protective_update_mode: str = "same_bar"

    slippage_fixed_bps: float = 0.0
    slippage_breakout_extra_bps: float = 0.0
    slippage_stop_extra_bps: float = 0.0
    slippage_range_weight: float = 0.0
    slippage_max_bps: float = 0.0
    slippage_breakout_atr_threshold: float = 1.10

    min_bar_range_atr: float = 0.0
    min_breakout_distance_atr: float = 0.0
    long_close_location_min: float = 0.0
    short_close_location_min: float = 0.0
    short_adx_extra: float = 0.0


class Direction(Enum):
    FLAT = "flat"
    LONG = "long"
    SHORT = "short"


class ExitReason(Enum):
    TP1 = "TP1"
    TP2 = "TP2"
    SL = "SL"
    BE = "BE"
    TRAIL = "TRAIL"
    SIGNAL = "SIGNAL"
    EOD = "EOD"


@dataclass
class Position:
    direction: Direction
    entry_price: float
    entry_time: pd.Timestamp
    entry_bar_4h: pd.Timestamp
    initial_qty: float
    current_qty: float
    stop_loss_price: float
    tp1_price: float
    tp2_price: float
    entry_atr: float
    tp1_filled: bool = False
    tp2_filled: bool = False
    be_activated: bool = False
    trailing_active: bool = False
    highest_since_entry: float = 0.0
    lowest_since_entry: float = 0.0


@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    direction: str
    qty: float
    pnl: float
    commission: float
    exit_reason: str
    entry_bar_4h: pd.Timestamp


@dataclass
class PendingEntry:
    direction: Direction
    signal_bar_time: pd.Timestamp
    signal_confirm_time: pd.Timestamp
    execute_index: int
    atr: float
    reference_close: float
    mode: str


class IndicatorEngine:
    def __init__(self, params: V85Params):
        self.p = params

    @staticmethod
    def calc_rma(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(alpha=1.0 / period, adjust=False).mean()

    @staticmethod
    def calc_atr(df: pd.DataFrame, period: int) -> pd.Series:
        high, low, close = df["high"], df["low"], df["close"]
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return IndicatorEngine.calc_rma(tr, period)

    @staticmethod
    def calc_sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).mean()

    @staticmethod
    def calc_ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calc_stdev(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).std()

    @staticmethod
    def calc_mom(series: pd.Series, period: int = 12) -> pd.Series:
        return series - series.shift(period)

    @staticmethod
    def calc_dmi(df: pd.DataFrame, period: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
        high, low, close = df["high"], df["low"], df["close"]
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=df.index)
        minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=df.index)

        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        atr = IndicatorEngine.calc_rma(tr, period)
        smooth_plus = IndicatorEngine.calc_rma(plus_dm, period)
        smooth_minus = IndicatorEngine.calc_rma(minus_dm, period)
        plus_di = 100.0 * smooth_plus / atr.replace(0, np.nan)
        minus_di = 100.0 * smooth_minus / atr.replace(0, np.nan)
        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = IndicatorEngine.calc_rma(dx.fillna(0.0), period)
        return plus_di.fillna(0.0), minus_di.fillna(0.0), adx.fillna(0.0)

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        p = self.p
        df["atr"] = self.calc_atr(df, p.atr_period)
        df["ema_trend"] = self.calc_ema(df["close"], p.ema_trend_len)

        df["bb_basis"] = self.calc_sma(df["close"], p.bb_period)
        df["bb_dev"] = self.calc_stdev(df["close"], p.bb_period)
        df["bb_upper"] = df["bb_basis"] + 2.0 * df["bb_dev"]
        df["bb_lower"] = df["bb_basis"] - 2.0 * df["bb_dev"]
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_basis"]
        df["bb_width_ma"] = self.calc_sma(df["bb_width"], 200)
        df["bb_width_norm"] = np.where(
            (df["bb_width_ma"].isna()) | (df["bb_width_ma"] == 0.0),
            0.0,
            df["bb_width"] / df["bb_width_ma"],
        )

        df["in_squeeze_long"] = df["bb_width_norm"] < p.squeeze_threshold
        df["in_squeeze_short"] = df["bb_width_norm"] < p.short_squeeze_threshold

        cnt_long = 0
        cnt_short = 0
        long_counts: List[int] = []
        short_counts: List[int] = []
        for i in range(len(df)):
            cnt_long = cnt_long + 1 if bool(df["in_squeeze_long"].iloc[i]) else 0
            cnt_short = cnt_short + 1 if bool(df["in_squeeze_short"].iloc[i]) else 0
            long_counts.append(cnt_long)
            short_counts.append(cnt_short)
        df["squeeze_count_long"] = long_counts
        df["squeeze_count_short"] = short_counts
        df["squeeze_quality_long"] = df["squeeze_count_long"] >= p.min_squeeze_candles
        df["squeeze_quality_short"] = df["squeeze_count_short"] >= p.min_squeeze_candles

        df["mom"] = self.calc_mom(df["close"], 12)
        df["mom_up"] = (df["mom"] > 0) & (df["mom"] > df["mom"].shift(1))
        df["mom_down"] = (df["mom"] < 0) & (df["mom"] < df["mom"].shift(1))

        df["vol_ma"] = self.calc_sma(df["volume"], 20)
        df["vol_spike"] = df["volume"] > df["vol_ma"] * 1.2
        df["bull"] = (df["close"] > df["ema_trend"]) & df["ema_trend"].notna()
        df["bear"] = (df["close"] < df["ema_trend"]) & df["ema_trend"].notna()

        _, _, df["adx"] = self.calc_dmi(df, p.adx_period)
        df["strong_trend"] = (df["adx"] > p.adx_trend_level) & df["adx"].notna()
        df["bar_range_atr"] = np.where(df["atr"] > 0, (df["high"] - df["low"]) / df["atr"], 0.0)
        df["close_location"] = np.where(
            (df["high"] - df["low"]) > 0,
            (df["close"] - df["low"]) / (df["high"] - df["low"]),
            0.5,
        )
        df["long_breakout_distance_atr"] = np.where(df["atr"] > 0, np.maximum(df["close"] - df["bb_upper"], 0.0) / df["atr"], 0.0)
        df["short_breakout_distance_atr"] = np.where(df["atr"] > 0, np.maximum(df["bb_lower"] - df["close"], 0.0) / df["atr"], 0.0)
        return df


def calc_long_score(row, prev_row) -> int:
    score = 0
    if bool(prev_row["in_squeeze_long"]) and (not bool(row["in_squeeze_long"])):
        score += 1
    if row["close"] > row["bb_upper"]:
        score += 1
    if bool(prev_row["squeeze_quality_long"]):
        score += 1
    if bool(row["mom_up"]):
        score += 1
    if bool(row["vol_spike"]):
        score += 1
    return score


def calc_short_score(row, prev_row) -> int:
    score = 0
    if bool(prev_row["in_squeeze_short"]) and (not bool(row["in_squeeze_short"])):
        score += 1
    if row["close"] < row["bb_lower"]:
        score += 1
    if bool(prev_row["squeeze_quality_short"]):
        score += 1
    if bool(row["mom_down"]):
        score += 1
    if bool(row["vol_spike"]):
        score += 1
    return score


def check_entry_conditions(row, prev_row, p: V85Params, has_position: bool) -> Tuple[bool, bool]:
    if has_position:
        return False, False

    long_env_ok = bool(row["bull"]) if p.use_env_filter else True
    short_env_ok = bool(row["bear"]) if p.use_env_filter else True
    long_trend_ok = (not p.use_adx_filter) or bool(row["adx"] > p.adx_trend_level)
    short_trend_ok = (not p.use_adx_filter) or bool(row["adx"] > (p.adx_trend_level + p.short_adx_extra))
    long_score = calc_long_score(row, prev_row)
    short_score = calc_short_score(row, prev_row)

    long_quality_ok = True
    short_quality_ok = True
    if p.min_bar_range_atr > 0:
        long_quality_ok = long_quality_ok and (float(row["bar_range_atr"]) >= p.min_bar_range_atr)
        short_quality_ok = short_quality_ok and (float(row["bar_range_atr"]) >= p.min_bar_range_atr)
    if p.min_breakout_distance_atr > 0:
        long_quality_ok = long_quality_ok and (float(row["long_breakout_distance_atr"]) >= p.min_breakout_distance_atr)
        short_quality_ok = short_quality_ok and (float(row["short_breakout_distance_atr"]) >= p.min_breakout_distance_atr)
    if p.long_close_location_min > 0:
        long_quality_ok = long_quality_ok and (float(row["close_location"]) >= p.long_close_location_min)
    if p.short_close_location_min > 0:
        short_quality_ok = short_quality_ok and ((1.0 - float(row["close_location"])) >= p.short_close_location_min)

    long_signal = long_env_ok and long_trend_ok and long_quality_ok and long_score >= p.min_long_score
    short_allowed = short_env_ok and short_trend_ok and ((not p.short_only_bear) or bool(row["bear"]))
    short_signal = p.enable_short and short_allowed and short_quality_ok and short_score >= p.min_short_score
    return bool(long_signal), bool(short_signal)

class PositionManager:
    def __init__(self, params: V85Params):
        self.p = params
        self.position: Optional[Position] = None
        self.trades: List[Trade] = []
        self.equity = float(params.init_equity)

    def is_flat(self) -> bool:
        return self.position is None

    def is_open(self) -> bool:
        return self.position is not None

    def open_position(
        self,
        direction: Direction,
        price: float,
        qty: float,
        atr: float,
        time: pd.Timestamp,
        bar_4h: pd.Timestamp,
    ) -> None:
        if self.is_open() or qty <= 0 or price <= 0 or atr <= 0:
            return
        if direction == Direction.LONG:
            stop = price - self.p.initial_stop_atr * atr
            tp1 = price + self.p.tp1_atr * atr
            tp2 = price + self.p.tp2_atr * atr
        else:
            stop = price + self.p.initial_stop_atr * atr
            tp1 = price - self.p.tp1_atr * atr
            tp2 = price - self.p.tp2_atr * atr

        self.position = Position(
            direction=direction,
            entry_price=float(price),
            entry_time=time,
            entry_bar_4h=bar_4h,
            initial_qty=float(qty),
            current_qty=float(qty),
            stop_loss_price=float(stop),
            tp1_price=float(tp1),
            tp2_price=float(tp2),
            entry_atr=float(atr),
            highest_since_entry=float(price),
            lowest_since_entry=float(price),
        )
        commission = price * qty * (self.p.commission_pct / 100.0)
        self.equity -= commission

    def _tp_qty(self, pct: float) -> float:
        if self.is_flat():
            return 0.0
        pos = self.position
        qty = pos.initial_qty * (pct / 100.0)
        return min(qty, pos.current_qty)

    def _stop_exit_reason(self) -> ExitReason:
        pos = self.position
        if pos is None:
            return ExitReason.SL
        if pos.trailing_active:
            return ExitReason.TRAIL
        if pos.be_activated:
            return ExitReason.BE
        return ExitReason.SL

    def _resolve_intrabar_execution_model(self) -> str:
        model = getattr(self.p, "intrabar_execution_model", "segment_path_same_bar")
        # Backward-compatible alias for earlier audit work.
        if model == "segment_path_same_bar" and getattr(self.p, "protective_update_mode", "same_bar") == "defer_within_bar":
            return "segment_path_defer_protective"
        return model

    def _path_points(self, bar: pd.Series, path_mode: str, direction: Direction) -> List[float]:
        open_px = float(bar["open"])
        high_px = float(bar["high"])
        low_px = float(bar["low"])
        close_px = float(bar["close"])
        if path_mode == "optimistic":
            if direction == Direction.LONG:
                mid1, mid2 = high_px, low_px
            else:
                mid1, mid2 = low_px, high_px
        elif path_mode == "midpoint":
            if abs(open_px - high_px) < abs(open_px - low_px):
                mid1, mid2 = high_px, low_px
            elif abs(open_px - high_px) > abs(open_px - low_px):
                mid1, mid2 = low_px, high_px
            elif close_px >= open_px:
                mid1, mid2 = low_px, high_px
            else:
                mid1, mid2 = high_px, low_px
        elif path_mode == "volatility_aware":
            if close_px >= open_px:
                mid1, mid2 = low_px, high_px
            else:
                mid1, mid2 = high_px, low_px
        else:
            if direction == Direction.LONG:
                mid1, mid2 = low_px, high_px
            else:
                mid1, mid2 = high_px, low_px
        return [open_px, mid1, mid2, close_px]

    def _init_pending_protective(self) -> Dict[str, float | bool | None]:
        return {"stop": None, "be_activated": False, "trailing_active": False}

    def _schedule_protective_update(
        self,
        pending: Dict[str, float | bool | None],
        stop: float,
        *,
        be_activated: bool = False,
        trailing_active: bool = False,
        long_side: bool = True,
    ) -> None:
        current = pending["stop"]
        if current is None:
            pending["stop"] = float(stop)
        elif long_side:
            pending["stop"] = max(float(current), float(stop))
        else:
            pending["stop"] = min(float(current), float(stop))
        pending["be_activated"] = bool(pending["be_activated"] or be_activated)
        pending["trailing_active"] = bool(pending["trailing_active"] or trailing_active)

    def _apply_pending_protective(self, pending: Dict[str, float | bool | None]) -> None:
        if self.is_flat():
            return
        pos = self.position
        stop = pending["stop"]
        if stop is not None:
            pos.stop_loss_price = float(stop)
        pos.be_activated = bool(pos.be_activated or pending["be_activated"])
        pos.trailing_active = bool(pos.trailing_active or pending["trailing_active"])

    def _legacy_bar_extrema(self, bar: pd.Series, current_atr: float, bar_time: pd.Timestamp) -> List[Tuple[ExitReason, float, float, pd.Timestamp]]:
        if self.is_flat():
            return []
        pos = self.position
        triggers: List[Tuple[ExitReason, float, float, pd.Timestamp]] = []
        high_px = float(bar["high"])
        low_px = float(bar["low"])

        # Legacy philosophy: inspect the stop that existed at bar start first,
        # then update TP/BE/trail from full-bar extrema, but do not re-check any
        # newly activated protective state inside the same bar.
        old_stop = float(pos.stop_loss_price)
        old_reason = self._stop_exit_reason()
        pos.highest_since_entry = max(pos.highest_since_entry, high_px)
        pos.lowest_since_entry = min(pos.lowest_since_entry, low_px)

        if pos.direction == Direction.LONG:
            if low_px <= old_stop:
                triggers.append((old_reason, old_stop, pos.current_qty, bar_time))
                return triggers
            profit_atr = (high_px - pos.entry_price) / current_atr if current_atr > 0 else 0.0
            if self.p.enable_partial_tp and (not pos.tp1_filled) and profit_atr >= self.p.tp1_atr:
                qty = self._tp_qty(self.p.tp1_pct)
                if qty > 0:
                    triggers.append((ExitReason.TP1, pos.tp1_price, qty, bar_time))
                    pos.tp1_filled = True
                    pos.current_qty -= qty
            if self.p.enable_partial_tp and pos.tp1_filled and (not pos.tp2_filled) and profit_atr >= self.p.tp2_atr:
                qty = self._tp_qty(self.p.tp2_pct)
                if qty > 0:
                    triggers.append((ExitReason.TP2, pos.tp2_price, qty, bar_time))
                    pos.tp2_filled = True
                    pos.current_qty -= qty
            if (not pos.be_activated) and profit_atr >= self.p.break_even_atr:
                pos.stop_loss_price = max(pos.stop_loss_price, pos.entry_price)
                pos.be_activated = True
            if profit_atr >= self.p.trail_start_atr:
                pos.trailing_active = True
                pos.stop_loss_price = max(pos.stop_loss_price, pos.highest_since_entry - self.p.trail_offset_atr * current_atr)
            return triggers

        if high_px >= old_stop:
            triggers.append((old_reason, old_stop, pos.current_qty, bar_time))
            return triggers
        profit_atr = (pos.entry_price - low_px) / current_atr if current_atr > 0 else 0.0
        if self.p.enable_partial_tp and (not pos.tp1_filled) and profit_atr >= self.p.tp1_atr:
            qty = self._tp_qty(self.p.tp1_pct)
            if qty > 0:
                triggers.append((ExitReason.TP1, pos.tp1_price, qty, bar_time))
                pos.tp1_filled = True
                pos.current_qty -= qty
        if self.p.enable_partial_tp and pos.tp1_filled and (not pos.tp2_filled) and profit_atr >= self.p.tp2_atr:
            qty = self._tp_qty(self.p.tp2_pct)
            if qty > 0:
                triggers.append((ExitReason.TP2, pos.tp2_price, qty, bar_time))
                pos.tp2_filled = True
                pos.current_qty -= qty
        if (not pos.be_activated) and profit_atr >= self.p.break_even_atr:
            pos.stop_loss_price = min(pos.stop_loss_price, pos.entry_price)
            pos.be_activated = True
        if profit_atr >= self.p.trail_start_atr:
            pos.trailing_active = True
            pos.stop_loss_price = min(pos.stop_loss_price, pos.lowest_since_entry + self.p.trail_offset_atr * current_atr)
        return triggers

    def _process_long_segment(
        self,
        start_px: float,
        end_px: float,
        current_atr: float,
        bar_time: pd.Timestamp,
        triggers: List[Tuple[ExitReason, float, float, pd.Timestamp]],
        pending: Optional[Dict[str, float | bool | None]] = None,
        *,
        execution_model: str = "segment_path_same_bar",
    ) -> bool:
        pos = self.position
        if pos is None:
            return True
        defer_protective = execution_model == "segment_path_defer_protective" and pending is not None
        if end_px >= start_px:
            pos.highest_since_entry = max(pos.highest_since_entry, end_px)
            if self.p.enable_partial_tp and (not pos.tp1_filled) and end_px >= pos.tp1_price:
                qty = self._tp_qty(self.p.tp1_pct)
                if qty > 0:
                    triggers.append((ExitReason.TP1, pos.tp1_price, qty, bar_time))
                    pos.tp1_filled = True
                    pos.current_qty -= qty
            if self.p.enable_partial_tp and pos.tp1_filled and (not pos.tp2_filled) and end_px >= pos.tp2_price:
                qty = self._tp_qty(self.p.tp2_pct)
                if qty > 0:
                    triggers.append((ExitReason.TP2, pos.tp2_price, qty, bar_time))
                    pos.tp2_filled = True
                    pos.current_qty -= qty
            profit_atr = (end_px - pos.entry_price) / current_atr if current_atr > 0 else 0.0
            if (not pos.be_activated) and profit_atr >= self.p.break_even_atr:
                new_stop = max(pos.stop_loss_price, pos.entry_price)
                if defer_protective:
                    self._schedule_protective_update(pending, new_stop, be_activated=True, long_side=True)
                else:
                    pos.stop_loss_price = new_stop
                    pos.be_activated = True
            if profit_atr >= self.p.trail_start_atr:
                new_stop = max(pos.stop_loss_price, pos.highest_since_entry - self.p.trail_offset_atr * current_atr)
                if defer_protective:
                    self._schedule_protective_update(pending, new_stop, trailing_active=True, long_side=True)
                else:
                    pos.trailing_active = True
                    pos.stop_loss_price = new_stop
            return False

        pos.lowest_since_entry = min(pos.lowest_since_entry, end_px)
        if end_px <= pos.stop_loss_price <= start_px:
            triggers.append((self._stop_exit_reason(), pos.stop_loss_price, pos.current_qty, bar_time))
            return True
        return False

    def _process_short_segment(
        self,
        start_px: float,
        end_px: float,
        current_atr: float,
        bar_time: pd.Timestamp,
        triggers: List[Tuple[ExitReason, float, float, pd.Timestamp]],
        pending: Optional[Dict[str, float | bool | None]] = None,
        *,
        execution_model: str = "segment_path_same_bar",
    ) -> bool:
        pos = self.position
        if pos is None:
            return True
        defer_protective = execution_model == "segment_path_defer_protective" and pending is not None
        if end_px <= start_px:
            pos.lowest_since_entry = min(pos.lowest_since_entry, end_px)
            if self.p.enable_partial_tp and (not pos.tp1_filled) and end_px <= pos.tp1_price:
                qty = self._tp_qty(self.p.tp1_pct)
                if qty > 0:
                    triggers.append((ExitReason.TP1, pos.tp1_price, qty, bar_time))
                    pos.tp1_filled = True
                    pos.current_qty -= qty
            if self.p.enable_partial_tp and pos.tp1_filled and (not pos.tp2_filled) and end_px <= pos.tp2_price:
                qty = self._tp_qty(self.p.tp2_pct)
                if qty > 0:
                    triggers.append((ExitReason.TP2, pos.tp2_price, qty, bar_time))
                    pos.tp2_filled = True
                    pos.current_qty -= qty
            profit_atr = (pos.entry_price - end_px) / current_atr if current_atr > 0 else 0.0
            if (not pos.be_activated) and profit_atr >= self.p.break_even_atr:
                new_stop = min(pos.stop_loss_price, pos.entry_price)
                if defer_protective:
                    self._schedule_protective_update(pending, new_stop, be_activated=True, long_side=False)
                else:
                    pos.stop_loss_price = new_stop
                    pos.be_activated = True
            if profit_atr >= self.p.trail_start_atr:
                new_stop = min(pos.stop_loss_price, pos.lowest_since_entry + self.p.trail_offset_atr * current_atr)
                if defer_protective:
                    self._schedule_protective_update(pending, new_stop, trailing_active=True, long_side=False)
                else:
                    pos.trailing_active = True
                    pos.stop_loss_price = new_stop
            return False

        pos.highest_since_entry = max(pos.highest_since_entry, end_px)
        if start_px <= pos.stop_loss_price <= end_px:
            triggers.append((self._stop_exit_reason(), pos.stop_loss_price, pos.current_qty, bar_time))
            return True
        return False

    def process_intrabar_bar(
        self,
        bar: pd.Series,
        current_atr: float,
        bar_time: pd.Timestamp,
        path_mode: str,
    ) -> List[Tuple[ExitReason, float, float, pd.Timestamp]]:
        if self.is_flat():
            return []
        execution_model = self._resolve_intrabar_execution_model()
        if execution_model == "legacy_bar_extrema":
            return self._legacy_bar_extrema(bar, current_atr, bar_time)

        pos = self.position
        triggers: List[Tuple[ExitReason, float, float, pd.Timestamp]] = []
        path_points = self._path_points(bar, path_mode, pos.direction)
        pending = self._init_pending_protective() if execution_model == "segment_path_defer_protective" else None
        for start_px, end_px in zip(path_points[:-1], path_points[1:]):
            if self.is_flat():
                break
            if pos.direction == Direction.LONG:
                should_exit = self._process_long_segment(start_px, end_px, current_atr, bar_time, triggers, pending, execution_model=execution_model)
            else:
                should_exit = self._process_short_segment(start_px, end_px, current_atr, bar_time, triggers, pending, execution_model=execution_model)
            if should_exit:
                break
        if pending is not None and self.is_open():
            self._apply_pending_protective(pending)
        return triggers

    def execute_exit(self, reason: ExitReason, price: float, qty: float, time: pd.Timestamp) -> Optional[Trade]:
        if self.is_flat() or qty <= 0:
            return None
        pos = self.position
        qty = min(qty, pos.current_qty)
        if qty <= 0:
            return None
        pnl = (price - pos.entry_price) * qty if pos.direction == Direction.LONG else (pos.entry_price - price) * qty
        commission = price * qty * (self.p.commission_pct / 100.0)
        realized = pnl - commission
        self.equity += realized
        trade = Trade(
            entry_time=pos.entry_time,
            exit_time=time,
            entry_price=pos.entry_price,
            exit_price=float(price),
            direction=pos.direction.value,
            qty=float(qty),
            pnl=float(realized),
            commission=float(commission),
            exit_reason=reason.value,
            entry_bar_4h=pos.entry_bar_4h,
        )
        self.trades.append(trade)
        pos.current_qty -= qty
        if pos.current_qty <= 1e-12 or reason in {ExitReason.SL, ExitReason.BE, ExitReason.TRAIL, ExitReason.SIGNAL, ExitReason.EOD}:
            self.position = None
        return trade

    def close_position(self, price: float, time: pd.Timestamp, reason: ExitReason = ExitReason.SIGNAL) -> Optional[Trade]:
        if self.is_flat():
            return None
        return self.execute_exit(reason, price, self.position.current_qty, time)

    def snapshot_position(self) -> Dict:
        if self.is_flat():
            return {}
        pos = self.position
        return {
            "direction": pos.direction.value,
            "entry_price": float(pos.entry_price),
            "entry_time": pos.entry_time.isoformat(),
            "entry_bar_4h": pos.entry_bar_4h.isoformat(),
            "initial_qty": float(pos.initial_qty),
            "current_qty": float(pos.current_qty),
            "stop_loss_price": float(pos.stop_loss_price),
            "tp1_price": float(pos.tp1_price),
            "tp2_price": float(pos.tp2_price),
            "entry_atr": float(pos.entry_atr),
            "tp1_filled": bool(pos.tp1_filled),
            "tp2_filled": bool(pos.tp2_filled),
            "be_activated": bool(pos.be_activated),
            "trailing_active": bool(pos.trailing_active),
            "highest_since_entry": float(pos.highest_since_entry),
            "lowest_since_entry": float(pos.lowest_since_entry),
        }

class IntrabarBacktestEngine:
    def __init__(self, params: V85Params, use_intrabar_stop: bool = True):
        self.p = params
        self.use_intrabar_stop = use_intrabar_stop
        self.indicator_engine = IndicatorEngine(params)

    def _ensure_timestamp(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
        return out.sort_values("timestamp").reset_index(drop=True)

    def _build_mapping(self, df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict[pd.Timestamp, List[pd.Timestamp]]:
        ts_5m = pd.to_datetime(df_5m["timestamp"], utc=True)
        ts_4h = pd.to_datetime(df_4h["timestamp"], utc=True)
        mapping: Dict[pd.Timestamp, List[pd.Timestamp]] = {}
        for bar_ts in ts_4h:
            bar_end = bar_ts + timedelta(hours=4)
            mask = (ts_5m >= bar_ts) & (ts_5m < bar_end)
            mapping[bar_ts] = ts_5m[mask].tolist()
        return mapping

    @staticmethod
    def _apply_side_bps(price: float, side: str, bps: float) -> float:
        if price <= 0 or abs(bps) < 1e-12:
            return float(price)
        adj = bps / 10000.0
        return float(price) * (1.0 + adj) if side.lower() == "buy" else float(price) * (1.0 - adj)

    def _slippage_bps(
        self,
        *,
        row_4h: Optional[pd.Series] = None,
        bar_5m: Optional[pd.Series] = None,
        reason: Optional[ExitReason] = None,
        is_entry: bool = False,
    ) -> float:
        base = max(float(self.p.slippage_fixed_bps), float(self.p.slippage))
        if base <= 0 and self.p.slippage_breakout_extra_bps <= 0 and self.p.slippage_stop_extra_bps <= 0 and self.p.slippage_range_weight <= 0:
            return 0.0
        total = base
        local_range_bps = 0.0
        if bar_5m is not None:
            px = float(bar_5m["close"])
            if px > 0:
                local_range_bps = max(float(bar_5m["high"]) - float(bar_5m["low"]), 0.0) / px * 10000.0
        elif row_4h is not None:
            px = float(row_4h["close"])
            if px > 0:
                local_range_bps = max(float(row_4h["high"]) - float(row_4h["low"]), 0.0) / px * 10000.0
        if self.p.slippage_range_weight > 0 and local_range_bps > 0:
            total += self.p.slippage_range_weight * local_range_bps
        if is_entry and row_4h is not None:
            atr = float(row_4h.get("atr", 0.0) or 0.0)
            bar_range_atr = (float(row_4h["high"] - row_4h["low"]) / atr) if atr > 0 else 0.0
            breakout = bool(row_4h.get("close", 0.0) > row_4h.get("bb_upper", np.inf)) or bool(row_4h.get("close", 0.0) < row_4h.get("bb_lower", -np.inf))
            if breakout or (bar_range_atr >= self.p.slippage_breakout_atr_threshold):
                total += self.p.slippage_breakout_extra_bps
        if reason in {ExitReason.SL, ExitReason.BE, ExitReason.TRAIL}:
            total += self.p.slippage_stop_extra_bps
        if self.p.slippage_max_bps > 0:
            total = min(total, self.p.slippage_max_bps)
        return max(total, 0.0)

    def _apply_slippage(
        self,
        raw_price: float,
        *,
        side: str,
        row_4h: Optional[pd.Series] = None,
        bar_5m: Optional[pd.Series] = None,
        reason: Optional[ExitReason] = None,
        is_entry: bool = False,
    ) -> float:
        bps = self._slippage_bps(row_4h=row_4h, bar_5m=bar_5m, reason=reason, is_entry=is_entry)
        return self._apply_side_bps(raw_price, side, bps)

    @staticmethod
    def _entry_side(direction: Direction) -> str:
        return "buy" if direction == Direction.LONG else "sell"

    @staticmethod
    def _exit_side(direction: Direction) -> str:
        return "sell" if direction == Direction.LONG else "buy"

    def _schedule_entry(
        self,
        direction: Direction,
        signal_bar_time: pd.Timestamp,
        signal_row: pd.Series,
        bar_index: int,
        bar_count: int,
    ) -> Optional[PendingEntry]:
        mode = self.p.entry_execution_mode
        if mode in {"signal_close", "close_plus_delay_bps"}:
            return PendingEntry(
                direction=direction,
                signal_bar_time=signal_bar_time,
                signal_confirm_time=signal_bar_time + timedelta(hours=4),
                execute_index=bar_index,
                atr=float(signal_row["atr"]),
                reference_close=float(signal_row["close"]),
                mode=mode,
            )
        if (bar_index + 1) >= bar_count:
            return None
        if mode in {"next_bar_open", "live_runner_next_5m_close"}:
            return PendingEntry(
                direction=direction,
                signal_bar_time=signal_bar_time,
                signal_confirm_time=signal_bar_time + timedelta(hours=4),
                execute_index=bar_index + 1,
                atr=float(signal_row["atr"]),
                reference_close=float(signal_row["close"]),
                mode=mode,
            )
        raise ValueError(f"unsupported entry_execution_mode: {mode}")

    def _fill_immediate_signal_entry(self, pending: PendingEntry, signal_row: pd.Series) -> Tuple[float, pd.Timestamp]:
        raw_price = float(signal_row["close"])
        if pending.mode == "close_plus_delay_bps":
            raw_price = self._apply_side_bps(raw_price, self._entry_side(pending.direction), self.p.close_delay_bps)
        fill_price = self._apply_slippage(raw_price, side=self._entry_side(pending.direction), row_4h=signal_row, is_entry=True)
        return fill_price, pending.signal_confirm_time

    def _fill_delayed_entry(
        self,
        pending: PendingEntry,
        row_4h: pd.Series,
        ts_4h: pd.Timestamp,
        five_min_indices: List[pd.Timestamp],
        df_5m_indexed: pd.DataFrame,
    ) -> Optional[Tuple[float, pd.Timestamp, bool]]:
        side = self._entry_side(pending.direction)
        if pending.mode == "next_bar_open":
            raw_price = float(row_4h["open"])
            fill_price = self._apply_slippage(raw_price, side=side, row_4h=row_4h, is_entry=True)
            return fill_price, ts_4h, True
        if pending.mode == "live_runner_next_5m_close":
            if not five_min_indices:
                return None
            first_ts = five_min_indices[0]
            if first_ts not in df_5m_indexed.index:
                return None
            bar_5m = df_5m_indexed.loc[first_ts]
            raw_price = float(bar_5m["close"])
            fill_price = self._apply_slippage(raw_price, side=side, row_4h=row_4h, bar_5m=bar_5m, is_entry=True)
            return fill_price, first_ts + timedelta(minutes=5), False
        raise ValueError(f"unsupported delayed entry mode: {pending.mode}")

    def _execute_triggers(
        self,
        pm: PositionManager,
        triggers: List[Tuple[ExitReason, float, float, pd.Timestamp]],
        *,
        row_4h: Optional[pd.Series] = None,
        bar_5m: Optional[pd.Series] = None,
    ) -> None:
        for reason, raw_price, qty, event_time in triggers:
            if pm.is_flat():
                break
            side = self._exit_side(pm.position.direction)
            fill_price = self._apply_slippage(raw_price, side=side, row_4h=row_4h, bar_5m=bar_5m, reason=reason, is_entry=False)
            pm.execute_exit(reason, fill_price, qty, event_time)

    def run(
        self,
        df_5m: pd.DataFrame,
        df_4h: pd.DataFrame,
        *,
        close_on_end: bool = True,
        allow_entry_on_last_bar: bool = True,
    ) -> Dict:
        df_5m = self._ensure_timestamp(df_5m)
        df_4h = self._ensure_timestamp(df_4h)
        df_4h = self.indicator_engine.compute_indicators(df_4h)
        df_5m_indexed = df_5m.set_index("timestamp").sort_index()
        mapping = self._build_mapping(df_5m, df_4h)

        print("=" * 70)
        print(f"V85 backtest | intrabar={self.use_intrabar_stop} | entry={self.p.entry_execution_mode} | path={self.p.intrabar_path_mode}")
        print("=" * 70)

        pm = PositionManager(self.p)
        equity_history: List[Dict] = []
        current_day = None
        day_start_equity = self.p.init_equity
        day_limit_hit = False
        bars_since_hit = 0
        pending_entry: Optional[PendingEntry] = None

        df_4h_indexed = df_4h.set_index("timestamp").sort_index()
        timestamps = list(df_4h_indexed.index)
        bar_count = len(df_4h_indexed)

        for i in range(1, bar_count):
            prev_row = df_4h_indexed.iloc[i - 1]
            row = df_4h_indexed.iloc[i]
            ts_4h = timestamps[i]
            five_min_indices = mapping.get(ts_4h, [])
            atr = float(row["atr"] or 0.0)
            if atr <= 0:
                continue

            bar_day = ts_4h.date()
            if bar_day != current_day:
                current_day = bar_day
                day_start_equity = pm.equity
                day_limit_hit = False
                bars_since_hit = 0
            elif day_limit_hit:
                bars_since_hit += 1

            if self.p.enable_daily_loss_limit and (not day_limit_hit) and day_start_equity > 0:
                day_pnl_pct = (pm.equity / day_start_equity - 1.0) * 100.0
                if day_pnl_pct <= -self.p.daily_loss_limit_pct:
                    day_limit_hit = True
                    bars_since_hit = 0

            cooldown_passed = bars_since_hit >= self.p.cooldown_bars
            risk_allowed = (not self.p.enable_daily_loss_limit) or (not day_limit_hit) or cooldown_passed

            delayed_entry_armed = False
            if pending_entry is not None and pending_entry.execute_index == i and pending_entry.mode == "next_bar_open" and pm.is_flat() and risk_allowed:
                delayed = self._fill_delayed_entry(pending_entry, row, ts_4h, five_min_indices, df_5m_indexed)
                if delayed is not None:
                    fill_price, fill_time, _ = delayed
                    qty = pm.equity * (self.p.position_pct / 100.0) / max(pending_entry.reference_close, 1e-12)
                    pm.open_position(pending_entry.direction, fill_price, qty, pending_entry.atr, fill_time, pending_entry.signal_bar_time)
                pending_entry = None
            elif pending_entry is not None and pending_entry.execute_index == i and pending_entry.mode == "live_runner_next_5m_close":
                delayed_entry_armed = True

            if self.use_intrabar_stop and (pm.is_open() or delayed_entry_armed):
                for idx_5m, ts_5m in enumerate(five_min_indices):
                    if ts_5m not in df_5m_indexed.index:
                        continue
                    bar_5m = df_5m_indexed.loc[ts_5m]
                    if delayed_entry_armed and idx_5m == 0 and pending_entry is not None and pm.is_flat() and risk_allowed:
                        delayed = self._fill_delayed_entry(pending_entry, row, ts_4h, five_min_indices, df_5m_indexed)
                        if delayed is not None:
                            fill_price, fill_time, active_same_bar = delayed
                            qty = pm.equity * (self.p.position_pct / 100.0) / max(pending_entry.reference_close, 1e-12)
                            pm.open_position(pending_entry.direction, fill_price, qty, pending_entry.atr, fill_time, pending_entry.signal_bar_time)
                            pending_entry = None
                            delayed_entry_armed = False
                            if not active_same_bar:
                                continue
                    if pm.is_open():
                        triggers = pm.process_intrabar_bar(bar_5m, atr, ts_5m, self.p.intrabar_path_mode)
                        self._execute_triggers(pm, triggers, row_4h=row, bar_5m=bar_5m)
                        if pm.is_flat():
                            break

            if (not self.use_intrabar_stop) and pm.is_open():
                pos = pm.position
                if pos.direction == Direction.LONG and float(row["low"]) <= pos.stop_loss_price:
                    reason = pm._stop_exit_reason()
                    fill_price = self._apply_slippage(pos.stop_loss_price, side="sell", row_4h=row, reason=reason, is_entry=False)
                    pm.close_position(fill_price, ts_4h + timedelta(hours=4), reason)
                elif pos.direction == Direction.SHORT and float(row["high"]) >= pos.stop_loss_price:
                    reason = pm._stop_exit_reason()
                    fill_price = self._apply_slippage(pos.stop_loss_price, side="buy", row_4h=row, reason=reason, is_entry=False)
                    pm.close_position(fill_price, ts_4h + timedelta(hours=4), reason)

            is_last_bar = i == (bar_count - 1)
            if pm.is_flat() and (pending_entry is None) and risk_allowed and (allow_entry_on_last_bar or not is_last_bar):
                long_signal, short_signal = check_entry_conditions(row, prev_row, self.p, pm.is_open())
                if long_signal:
                    pending_entry = self._schedule_entry(Direction.LONG, ts_4h, row, i, bar_count)
                elif short_signal:
                    pending_entry = self._schedule_entry(Direction.SHORT, ts_4h, row, i, bar_count)

            if pending_entry is not None and pending_entry.execute_index == i and pending_entry.mode in {"signal_close", "close_plus_delay_bps"} and pm.is_flat() and risk_allowed:
                fill_price, fill_time = self._fill_immediate_signal_entry(pending_entry, row)
                qty = pm.equity * (self.p.position_pct / 100.0) / max(pending_entry.reference_close, 1e-12)
                pm.open_position(pending_entry.direction, fill_price, qty, pending_entry.atr, fill_time, pending_entry.signal_bar_time)
                pending_entry = None

            unrealized = 0.0
            if pm.is_open():
                pos = pm.position
                if pos.direction == Direction.LONG:
                    unrealized = (float(row["close"]) - pos.entry_price) * pos.current_qty
                else:
                    unrealized = (pos.entry_price - float(row["close"])) * pos.current_qty

            equity_history.append({
                "time": ts_4h,
                "equity": pm.equity + unrealized,
                "position": 0 if pm.is_flat() else (1 if pm.position.direction == Direction.LONG else -1),
            })

            if ((i + 1) % 500 == 0) or ((i + 1) == bar_count):
                print(f"  progress {i + 1}/{bar_count} equity=${pm.equity + unrealized:,.0f} trades={len(pm.trades)}")

        final_position = pm.snapshot_position()
        if close_on_end and pm.is_open():
            last_row = df_4h_indexed.iloc[-1]
            last_time = timestamps[-1] + timedelta(hours=4)
            fill_price = self._apply_slippage(float(last_row["close"]), side=self._exit_side(pm.position.direction), row_4h=last_row, reason=ExitReason.EOD, is_entry=False)
            pm.close_position(fill_price, last_time, ExitReason.EOD)

        trades_df = pd.DataFrame([asdict(t) for t in pm.trades]) if pm.trades else pd.DataFrame()
        equity_df = pd.DataFrame(equity_history).set_index("time") if equity_history else pd.DataFrame(columns=["equity", "position"])
        stats = self._calc_stats(trades_df, equity_df)
        stats.update({
            "EntryExecutionMode": self.p.entry_execution_mode,
            "IntrabarPathMode": self.p.intrabar_path_mode,
            "IntrabarExecutionModel": pm._resolve_intrabar_execution_model(),
            "ProtectiveUpdateMode": self.p.protective_update_mode,
            "SlippageFixedBps": float(self.p.slippage_fixed_bps),
            "SlippageStopExtraBps": float(self.p.slippage_stop_extra_bps),
            "SlippageBreakoutExtraBps": float(self.p.slippage_breakout_extra_bps),
        })
        return {
            "trades": trades_df,
            "equity": equity_df,
            "stats": stats,
            "signals": df_4h_indexed,
            "final_position": final_position,
            "meta": {
                "entry_execution_mode": self.p.entry_execution_mode,
                "intrabar_path_mode": self.p.intrabar_path_mode,
                "intrabar_execution_model": pm._resolve_intrabar_execution_model(),
                "use_intrabar_stop": self.use_intrabar_stop,
            },
        }

    def _calc_stats(self, trades_df: pd.DataFrame, equity_df: pd.DataFrame) -> Dict:
        init_equity = float(self.p.init_equity)
        if equity_df.empty:
            return {
                "FinalEquity": init_equity,
                "TotalReturn_pct": 0.0,
                "CAGR": 0.0,
                "Sharpe": 0.0,
                "MaxDD_pct": 0.0,
                "ProfitFactor": 0.0,
                "Trades": 0,
                "WinRate_pct": 0.0,
                "LongTrades": 0,
                "ShortTrades": 0,
                "LongPnL": 0.0,
                "ShortPnL": 0.0,
                "GrossProfit": 0.0,
                "GrossLoss": 0.0,
                "Years": 0.0,
                "ExitReasons": {},
            }

        eq = equity_df.copy()
        eq["peak"] = eq["equity"].cummax()
        eq["dd"] = eq["equity"] / eq["peak"] - 1.0
        eq["ret"] = eq["equity"].pct_change().fillna(0.0)
        final_equity = float(eq["equity"].iloc[-1])
        elapsed_days = max((eq.index[-1] - eq.index[0]).total_seconds() / 86400.0, 1.0)
        years = elapsed_days / 365.25
        cagr = (final_equity / init_equity) ** (1.0 / years) - 1.0 if final_equity > 0 and years > 0 else -1.0
        sharpe = 0.0
        ret_std = float(eq["ret"].std())
        if ret_std > 0:
            sharpe = float(eq["ret"].mean()) / ret_std * np.sqrt(252.0 * 6.0)

        n_trades = int(len(trades_df))
        win_rate = 0.0
        gross_profit = 0.0
        gross_loss = 0.0
        profit_factor = 0.0
        long_trades = pd.DataFrame()
        short_trades = pd.DataFrame()
        exit_reasons: Dict[str, int] = {}
        if n_trades > 0:
            wins = trades_df[trades_df["pnl"] > 0]
            losses = trades_df[trades_df["pnl"] < 0]
            win_rate = float(len(wins) / n_trades * 100.0)
            gross_profit = float(wins["pnl"].sum()) if not wins.empty else 0.0
            gross_loss = float(losses["pnl"].sum()) if not losses.empty else 0.0
            profit_factor = gross_profit / abs(gross_loss) if gross_loss < 0 else 0.0
            long_trades = trades_df[trades_df["direction"] == "long"]
            short_trades = trades_df[trades_df["direction"] == "short"]
            exit_reasons = trades_df["exit_reason"].value_counts().to_dict()

        return {
            "FinalEquity": final_equity,
            "TotalReturn_pct": (final_equity / init_equity - 1.0) * 100.0,
            "CAGR": float(cagr),
            "Sharpe": float(sharpe),
            "MaxDD_pct": float(eq["dd"].min()),
            "ProfitFactor": float(profit_factor),
            "Trades": n_trades,
            "WinRate_pct": float(win_rate),
            "LongTrades": int(len(long_trades)),
            "ShortTrades": int(len(short_trades)),
            "LongPnL": float(long_trades["pnl"].sum()) if not long_trades.empty else 0.0,
            "ShortPnL": float(short_trades["pnl"].sum()) if not short_trades.empty else 0.0,
            "GrossProfit": float(gross_profit),
            "GrossLoss": float(gross_loss),
            "Years": float(years),
            "ExitReasons": exit_reasons,
        }


def plot_results(result: Dict, outdir: Path, title: str = "") -> None:
    signals = result["signals"]
    eq = result["equity"]
    trades = result["trades"]
    stats = result["stats"]

    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(4, 1, height_ratios=[2.5, 1, 1, 0.5], hspace=0.3)

    ax0 = fig.add_subplot(gs[0, 0])
    ax0.plot(signals.index, signals["close"], label="Close", linewidth=0.8, color="black")
    ax0.plot(signals.index, signals["ema_trend"], label="EMA200", linewidth=0.8, alpha=0.7, color="orange")
    if len(trades) > 0:
        for _, trade in trades.iterrows():
            color = "green" if trade["direction"] == "long" else "red"
            marker = "^" if trade["direction"] == "long" else "v"
            ax0.scatter(trade["entry_time"], trade["entry_price"], marker=marker, s=30, c=color, zorder=5, alpha=0.7)
    ax0.set_title(f"V85 Intrabar Backtest {title}")
    ax0.legend(loc="upper left", fontsize=8)
    ax0.grid(True, alpha=0.3)

    ax1 = fig.add_subplot(gs[1, 0])
    ax1.plot(eq.index, eq["equity"], label="Equity", color="blue")
    ax1.axhline(10000, linestyle="--", color="gray", linewidth=0.8)
    ax1.set_title(f"Equity (Final: ${stats['FinalEquity']:,.0f}, Return: {stats['TotalReturn_pct']:.1f}%)")
    ax1.legend(loc="upper left", fontsize=8)
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(gs[2, 0])
    dd = eq["equity"] / eq["equity"].cummax() - 1.0
    ax2.fill_between(eq.index, dd * 100.0, 0.0, color="salmon", alpha=0.7)
    ax2.set_title(f"Drawdown (Max: {stats['MaxDD_pct'] * 100.0:.1f}%)")
    ax2.grid(True, alpha=0.3)

    ax3 = fig.add_subplot(gs[3, 0])
    ax3.axis("off")
    stats_text = (
        f"CAGR: {stats['CAGR'] * 100.0:.1f}% | Sharpe: {stats['Sharpe']:.2f} | "
        f"PF: {stats['ProfitFactor']:.2f} | Trades: {stats['Trades']} | WinRate: {stats['WinRate_pct']:.1f}%"
    )
    ax3.text(0.5, 0.5, stats_text, transform=ax3.transAxes, fontsize=10, ha="center", va="center",
             bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
    plt.tight_layout()
    fig.savefig(outdir / "backtest_plot.png", dpi=150)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="V85 intrabar backtest runner")
    parser.add_argument("--data_dir", default="./data")
    parser.add_argument("--start", default=None)
    parser.add_argument("--end", default=None)
    parser.add_argument("--no_intrabar", action="store_true")
    parser.add_argument("--outdir", default=None)
    parser.add_argument("--entry_execution_mode", default="signal_close", choices=["signal_close", "next_bar_open", "close_plus_delay_bps", "live_runner_next_5m_close"])
    parser.add_argument("--intrabar_path_mode", default="pessimistic", choices=["pessimistic", "optimistic", "midpoint", "volatility_aware"])
    parser.add_argument("--intrabar_execution_model", default="segment_path_same_bar", choices=["legacy_bar_extrema", "segment_path_same_bar", "segment_path_defer_protective"])
    parser.add_argument("--protective_update_mode", default="same_bar", choices=["same_bar", "defer_within_bar"])
    parser.add_argument("--slippage_fixed_bps", type=float, default=0.0)
    parser.add_argument("--slippage_breakout_extra_bps", type=float, default=0.0)
    parser.add_argument("--slippage_stop_extra_bps", type=float, default=0.0)
    parser.add_argument("--slippage_range_weight", type=float, default=0.0)
    parser.add_argument("--slippage_max_bps", type=float, default=0.0)
    parser.add_argument("--close_delay_bps", type=float, default=8.0)
    args = parser.parse_args()

    from universal_data_updater_5m import DataLoader5m

    print("Loading data...")
    loader = DataLoader5m(args.data_dir)
    df_5m, df_4h = loader.load_data(args.start, args.end)
    print(f"5m rows: {len(df_5m)}")
    print(f"4h rows: {len(df_4h)}")

    params = V85Params(
        entry_execution_mode=args.entry_execution_mode,
        intrabar_path_mode=args.intrabar_path_mode,
        intrabar_execution_model=args.intrabar_execution_model,
        protective_update_mode=args.protective_update_mode,
        slippage_fixed_bps=args.slippage_fixed_bps,
        slippage_breakout_extra_bps=args.slippage_breakout_extra_bps,
        slippage_stop_extra_bps=args.slippage_stop_extra_bps,
        slippage_range_weight=args.slippage_range_weight,
        slippage_max_bps=args.slippage_max_bps,
        close_delay_bps=args.close_delay_bps,
    )
    engine = IntrabarBacktestEngine(params, use_intrabar_stop=(not args.no_intrabar))
    result = engine.run(df_5m, df_4h)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "intrabar" if (not args.no_intrabar) else "close_only"
    outdir = Path(args.outdir) if args.outdir else Path(args.data_dir) / f"v85_{mode}_{stamp}"
    outdir.mkdir(parents=True, exist_ok=True)

    if not result["trades"].empty:
        result["trades"].to_csv(outdir / "trades.csv", index=False)
    result["equity"].to_csv(outdir / "equity.csv")
    with (outdir / "stats.json").open("w", encoding="utf-8") as f:
        json.dump(result["stats"], f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else str(x))

    try:
        plot_results(result, outdir)
    except Exception as exc:
        print(f"Plot failed: {exc}")

    stats = result["stats"]
    print("\n" + "=" * 70)
    print("V85 Backtest Result")
    print("=" * 70)
    print(f"TotalReturn: {stats['TotalReturn_pct']:.2f}%")
    print(f"CAGR: {stats['CAGR'] * 100.0:.2f}%")
    print(f"Sharpe: {stats['Sharpe']:.3f}")
    print(f"MaxDD: {stats['MaxDD_pct'] * 100.0:.2f}%")
    print(f"ProfitFactor: {stats['ProfitFactor']:.3f}")
    print(f"Trades: {stats['Trades']}")
    print(f"WinRate: {stats['WinRate_pct']:.2f}%")
    print(f"LongTrades: {stats['LongTrades']} (${stats['LongPnL']:,.2f})")
    print(f"ShortTrades: {stats['ShortTrades']} (${stats['ShortPnL']:,.2f})")
    print(f"EntryExecutionMode: {stats['EntryExecutionMode']}")
    print(f"IntrabarPathMode: {stats['IntrabarPathMode']}")
    print(f"IntrabarExecutionModel: {stats['IntrabarExecutionModel']}")
    print(f"ProtectiveUpdateMode: {stats['ProtectiveUpdateMode']}")
    print("=" * 70)
    print(f"Saved to: {outdir}")


__all__ = [
    "V85Params",
    "Direction",
    "ExitReason",
    "Position",
    "Trade",
    "IndicatorEngine",
    "calc_long_score",
    "calc_short_score",
    "check_entry_conditions",
    "IntrabarBacktestEngine",
    "plot_results",
    "main",
]


if __name__ == "__main__":
    main()

