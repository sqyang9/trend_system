#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BTC long-only trend mother research line under the calibrated execution model."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_backtest_engine_v2 import (
    Direction,
    ExitReason,
    IntrabarBacktestEngine,
    PendingEntry,
    PositionManager,
    V85Params,
)
from v85_research_suite_v2 import baseline_gate, ensure_datetime, live_safety_check


ANNUALIZATION_4H = np.sqrt(252.0 * 6.0)
SEED = 20260309


@dataclass
class TrendLongParams:
    candidate_name: str
    description: str
    breakout_mode: str = "donchian"
    donchian_entry_len: int = 55
    squeeze_threshold: float = 0.92
    squeeze_bars: int = 6
    ema_len: int = 200
    ema_slope_len: int = 20
    use_ema_slope: bool = True
    adx_period: int = 14
    adx_min: float = 18.0
    use_adx_filter: bool = True
    close_location_min: float = 0.55
    range_atr_min: float = 0.50
    volume_multiple: float = 1.00
    structure_lookback: int = 20
    initial_stop_atr: float = 3.0
    trail_atr_mult: float = 4.5
    trail_activate_atr: float = 2.0
    swing_trail_lookback: int = 20
    use_swing_trail: bool = False
    break_even_after_atr: float = 1e9
    position_pct: float = 100.0
    init_equity: float = 10000.0
    commission_pct: float = 0.06
    entry_execution_mode: str = "next_bar_open"
    close_delay_bps: float = 8.0
    intrabar_execution_model: str = "legacy_bar_extrema"
    intrabar_path_mode: str = "midpoint"
    slippage_fixed_bps: float = 5.0
    slippage_breakout_extra_bps: float = 5.0
    slippage_stop_extra_bps: float = 8.0
    slippage_range_weight: float = 0.05
    slippage_max_bps: float = 25.0
    slippage_breakout_atr_threshold: float = 1.10
    enable_daily_loss_limit: bool = False
    daily_loss_limit_pct: float = 1.5
    cooldown_bars: int = 0

    def to_exec_params(self) -> V85Params:
        return V85Params(
            init_equity=self.init_equity,
            position_pct=self.position_pct,
            commission_pct=self.commission_pct,
            enable_partial_tp=False,
            enable_short=False,
            short_only_bear=False,
            entry_execution_mode=self.entry_execution_mode,
            close_delay_bps=self.close_delay_bps,
            intrabar_execution_model=self.intrabar_execution_model,
            intrabar_path_mode=self.intrabar_path_mode,
            slippage_fixed_bps=self.slippage_fixed_bps,
            slippage_breakout_extra_bps=self.slippage_breakout_extra_bps,
            slippage_stop_extra_bps=self.slippage_stop_extra_bps,
            slippage_range_weight=self.slippage_range_weight,
            slippage_max_bps=self.slippage_max_bps,
            slippage_breakout_atr_threshold=self.slippage_breakout_atr_threshold,
            enable_daily_loss_limit=self.enable_daily_loss_limit,
            daily_loss_limit_pct=self.daily_loss_limit_pct,
            cooldown_bars=self.cooldown_bars,
            break_even_atr=1e9,
            trail_start_atr=1e9,
            trail_offset_atr=1e9,
            initial_stop_atr=self.initial_stop_atr,
            tp1_atr=1e9,
            tp2_atr=1e9,
        )


@dataclass
class PendingTrendEntry:
    pending: PendingEntry
    signal_index: int
    initial_stop_price: float
    structure_low: float
    signal_close: float


class TrendIndicatorEngine:
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
        return TrendIndicatorEngine.calc_rma(tr, period)

    @staticmethod
    def calc_ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calc_sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).mean()

    @staticmethod
    def calc_stdev(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).std()

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
        atr = TrendIndicatorEngine.calc_rma(tr, period)
        smooth_plus = TrendIndicatorEngine.calc_rma(plus_dm, period)
        smooth_minus = TrendIndicatorEngine.calc_rma(minus_dm, period)
        plus_di = 100.0 * smooth_plus / atr.replace(0, np.nan)
        minus_di = 100.0 * smooth_minus / atr.replace(0, np.nan)
        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = TrendIndicatorEngine.calc_rma(dx.fillna(0.0), period)
        return plus_di.fillna(0.0), minus_di.fillna(0.0), adx.fillna(0.0)

    def compute(self, df: pd.DataFrame, params: TrendLongParams) -> pd.DataFrame:
        out = ensure_datetime(df)
        out["atr"] = self.calc_atr(out, params.adx_period)
        out["ema"] = self.calc_ema(out["close"], params.ema_len)
        out["ema_slope"] = out["ema"] - out["ema"].shift(params.ema_slope_len)
        _, _, out["adx"] = self.calc_dmi(out, params.adx_period)
        out["bar_range_atr"] = np.where(out["atr"] > 0, (out["high"] - out["low"]) / out["atr"], 0.0)
        out["close_location"] = np.where(
            (out["high"] - out["low"]) > 0,
            (out["close"] - out["low"]) / (out["high"] - out["low"]),
            0.5,
        )
        out["vol_ma"] = self.calc_sma(out["volume"], 20)
        out["vol_ok"] = np.where(out["vol_ma"] > 0, out["volume"] >= out["vol_ma"] * params.volume_multiple, True)
        out["donchian_high_entry"] = out["high"].shift(1).rolling(params.donchian_entry_len).max()
        out["structure_low"] = out["low"].shift(1).rolling(params.structure_lookback).min()
        out["swing_trail_low"] = out["low"].shift(1).rolling(params.swing_trail_lookback).min()
        bb_basis = self.calc_sma(out["close"], 20)
        bb_dev = self.calc_stdev(out["close"], 20)
        bb_upper = bb_basis + 2.0 * bb_dev
        bb_lower = bb_basis - 2.0 * bb_dev
        bb_width = (bb_upper - bb_lower) / bb_basis
        bb_width_ma = self.calc_sma(bb_width, 200)
        out["bb_width_norm"] = np.where(
            (bb_width_ma.isna()) | (bb_width_ma == 0.0),
            0.0,
            bb_width / bb_width_ma,
        )
        squeeze = out["bb_width_norm"] < params.squeeze_threshold
        count = 0
        counts: List[int] = []
        for active in squeeze.fillna(False).tolist():
            count = count + 1 if active else 0
            counts.append(count)
        out["squeeze_count"] = counts
        out["trend_ok"] = (out["close"] > out["ema"]) & out["ema"].notna()
        if params.use_ema_slope:
            out["trend_ok"] = out["trend_ok"] & (out["ema_slope"] > 0)
        if params.use_adx_filter:
            out["trend_ok"] = out["trend_ok"] & (out["adx"] >= params.adx_min)
        out["breakout"] = out["close"] > out["donchian_high_entry"]
        out["quality_ok"] = (
            (out["close_location"] >= params.close_location_min)
            & (out["bar_range_atr"] >= params.range_atr_min)
            & out["vol_ok"].astype(bool)
        )
        out["squeeze_ready"] = out["squeeze_count"] >= params.squeeze_bars
        return out

class TrendLongMotherEngine(IntrabarBacktestEngine):
    def __init__(self, params: TrendLongParams, use_intrabar_stop: bool = True):
        self.tp = params
        super().__init__(params.to_exec_params(), use_intrabar_stop=use_intrabar_stop)
        self.indicator_engine = TrendIndicatorEngine()
        self.closed_trade_meta: List[Dict] = []
        self.open_trade_meta: Optional[Dict] = None

    def _prepare(self, df_4h: pd.DataFrame) -> pd.DataFrame:
        return self.indicator_engine.compute(df_4h, self.tp)

    def _entry_signal(self, row: pd.Series, prev_row: pd.Series) -> bool:
        if not bool(row["trend_ok"]):
            return False
        if not bool(row["breakout"]):
            return False
        if self.tp.breakout_mode == "donchian":
            return True
        if self.tp.breakout_mode == "quality_breakout":
            return bool(row["quality_ok"])
        if self.tp.breakout_mode == "squeeze_release":
            return bool(prev_row["squeeze_ready"]) and bool(row["quality_ok"])
        raise ValueError(f"unsupported breakout_mode: {self.tp.breakout_mode}")

    def _entry_stop(self, signal_row: pd.Series, entry_reference_price: float) -> float:
        atr_stop = float(entry_reference_price) - self.tp.initial_stop_atr * float(signal_row["atr"])
        structure_low = float(signal_row["structure_low"]) if pd.notna(signal_row["structure_low"]) else atr_stop
        return min(atr_stop, structure_low)

    def _update_stop_from_completed_history(self, pm: PositionManager, hist: pd.DataFrame) -> None:
        if pm.is_flat() or self.open_trade_meta is None or hist.empty:
            return
        pos = pm.position
        entry_index = int(self.open_trade_meta["entry_index"])
        completed = hist.iloc[entry_index:]
        if completed.empty:
            return
        current_stop = float(pos.stop_loss_price)
        latest_atr = float(hist.iloc[-1]["atr"])
        highest_high = float(completed["high"].max())
        profit_atr = (highest_high - pos.entry_price) / max(pos.entry_atr, 1e-12)
        if self.tp.break_even_after_atr < 1e8 and profit_atr >= self.tp.break_even_after_atr:
            current_stop = max(current_stop, pos.entry_price)
            pos.be_activated = True
        if profit_atr >= self.tp.trail_activate_atr:
            trail_stop = highest_high - self.tp.trail_atr_mult * latest_atr
            current_stop = max(current_stop, trail_stop)
            pos.trailing_active = True
        if self.tp.use_swing_trail:
            swing_low = float(hist.iloc[-1]["swing_trail_low"]) if pd.notna(hist.iloc[-1]["swing_trail_low"]) else current_stop
            current_stop = max(current_stop, swing_low)
            if current_stop > pos.stop_loss_price:
                pos.trailing_active = True
        pos.stop_loss_price = min(current_stop, highest_high)

    def _register_open(self, pm: PositionManager, fill_price: float, fill_time: pd.Timestamp, signal_index: int, initial_stop: float) -> None:
        if pm.is_flat():
            return
        pos = pm.position
        pos.stop_loss_price = float(initial_stop)
        pos.tp1_price = float("inf")
        pos.tp2_price = float("inf")
        pos.highest_since_entry = float(fill_price)
        pos.lowest_since_entry = float(fill_price)
        self.open_trade_meta = {
            "entry_time": fill_time,
            "entry_price": float(fill_price),
            "entry_index": int(signal_index + 1),
            "initial_stop_price": float(initial_stop),
            "entry_atr": float(pos.entry_atr),
            "candidate_name": self.tp.candidate_name,
        }

    def _finalize_trade_meta(self, trade: object | None) -> None:
        if trade is None or self.open_trade_meta is None:
            return
        if isinstance(trade, pd.Series):
            exit_price = float(trade["exit_price"])
            exit_time = pd.Timestamp(trade["exit_time"])
            pnl = float(trade["pnl"])
            exit_reason = str(trade["exit_reason"])
        else:
            exit_price = float(trade.exit_price)
            exit_time = pd.Timestamp(trade.exit_time)
            pnl = float(trade.pnl)
            exit_reason = str(trade.exit_reason)
        meta = dict(self.open_trade_meta)
        meta.update(
            {
                "exit_time": exit_time,
                "exit_price": exit_price,
                "pnl": pnl,
                "exit_reason": exit_reason,
                "risk_pct": (meta["entry_price"] - meta["initial_stop_price"]) / max(meta["entry_price"], 1e-12),
            }
        )
        self.closed_trade_meta.append(meta)
        self.open_trade_meta = None

    def run(self, df_5m: pd.DataFrame, df_4h: pd.DataFrame, *, close_on_end: bool = True, allow_entry_on_last_bar: bool = True) -> Dict:
        self.closed_trade_meta = []
        self.open_trade_meta = None
        df_5m = self._ensure_timestamp(df_5m)
        df_4h = self._prepare(df_4h)
        df_5m_indexed = df_5m.set_index("timestamp").sort_index()
        df_4h_indexed = df_4h.set_index("timestamp").sort_index()
        mapping = self._build_mapping(df_5m, df_4h)
        timestamps = list(df_4h_indexed.index)
        bar_count = len(df_4h_indexed)
        pm = PositionManager(self.p)
        equity_history: List[Dict] = []
        pending_entry: Optional[PendingTrendEntry] = None

        for i in range(1, bar_count):
            prev_row = df_4h_indexed.iloc[i - 1]
            row = df_4h_indexed.iloc[i]
            ts_4h = timestamps[i]
            five_min_indices = mapping.get(ts_4h, [])
            atr = float(row["atr"] or 0.0)
            if atr <= 0:
                continue

            if pm.is_open():
                self._update_stop_from_completed_history(pm, df_4h_indexed.iloc[:i])

            delayed_entry_armed = False
            if pending_entry is not None and pending_entry.pending.execute_index == i and pending_entry.pending.mode == "next_bar_open" and pm.is_flat():
                delayed = self._fill_delayed_entry(pending_entry.pending, row, ts_4h, five_min_indices, df_5m_indexed)
                if delayed is not None:
                    fill_price, fill_time, _ = delayed
                    qty = pm.equity * (self.p.position_pct / 100.0) / max(fill_price, 1e-12)
                    pm.open_position(Direction.LONG, fill_price, qty, pending_entry.pending.atr, fill_time, pending_entry.pending.signal_bar_time)
                    self._register_open(pm, fill_price, fill_time, pending_entry.signal_index, pending_entry.initial_stop_price)
                pending_entry = None
            elif pending_entry is not None and pending_entry.pending.execute_index == i and pending_entry.pending.mode == "live_runner_next_5m_close":
                delayed_entry_armed = True

            if self.use_intrabar_stop and (pm.is_open() or delayed_entry_armed):
                for idx_5m, ts_5m in enumerate(five_min_indices):
                    if ts_5m not in df_5m_indexed.index:
                        continue
                    bar_5m = df_5m_indexed.loc[ts_5m]
                    if delayed_entry_armed and idx_5m == 0 and pending_entry is not None and pm.is_flat():
                        delayed = self._fill_delayed_entry(pending_entry.pending, row, ts_4h, five_min_indices, df_5m_indexed)
                        if delayed is not None:
                            fill_price, fill_time, active_same_bar = delayed
                            qty = pm.equity * (self.p.position_pct / 100.0) / max(fill_price, 1e-12)
                            pm.open_position(Direction.LONG, fill_price, qty, pending_entry.pending.atr, fill_time, pending_entry.pending.signal_bar_time)
                            self._register_open(pm, fill_price, fill_time, pending_entry.signal_index, pending_entry.initial_stop_price)
                            pending_entry = None
                            delayed_entry_armed = False
                            if not active_same_bar:
                                continue
                    if pm.is_open():
                        triggers = pm.process_intrabar_bar(bar_5m, atr, ts_5m, self.p.intrabar_path_mode)
                        before = len(pm.trades)
                        self._execute_triggers(pm, triggers, row_4h=row, bar_5m=bar_5m)
                        if len(pm.trades) > before:
                            self._finalize_trade_meta(pm.trades[-1])
                        if pm.is_flat():
                            break

            is_last_bar = i == (bar_count - 1)
            if pm.is_flat() and pending_entry is None and (allow_entry_on_last_bar or not is_last_bar):
                if self._entry_signal(row, prev_row) and pd.notna(row["donchian_high_entry"]) and pd.notna(row["structure_low"]):
                    pending = self._schedule_entry(Direction.LONG, ts_4h, row, i, bar_count)
                    if pending is not None:
                        pending_entry = PendingTrendEntry(
                            pending=pending,
                            signal_index=i,
                            initial_stop_price=self._entry_stop(row, float(row["close"])),
                            structure_low=float(row["structure_low"]),
                            signal_close=float(row["close"]),
                        )

            if pending_entry is not None and pending_entry.pending.execute_index == i and pending_entry.pending.mode in {"signal_close", "close_plus_delay_bps"} and pm.is_flat():
                fill_price, fill_time = self._fill_immediate_signal_entry(pending_entry.pending, row)
                qty = pm.equity * (self.p.position_pct / 100.0) / max(fill_price, 1e-12)
                pm.open_position(Direction.LONG, fill_price, qty, pending_entry.pending.atr, fill_time, pending_entry.pending.signal_bar_time)
                self._register_open(pm, fill_price, fill_time, pending_entry.signal_index, pending_entry.initial_stop_price)
                pending_entry = None

            unrealized = 0.0
            if pm.is_open():
                unrealized = (float(row["close"]) - pm.position.entry_price) * pm.position.current_qty
            equity_history.append(
                {
                    "time": ts_4h,
                    "equity": pm.equity + unrealized,
                    "position": 0 if pm.is_flat() else 1,
                    "close": float(row["close"]),
                }
            )

        if close_on_end and pm.is_open():
            last_row = df_4h_indexed.iloc[-1]
            last_time = timestamps[-1] + timedelta(hours=4)
            fill_price = self._apply_slippage(float(last_row["close"]), side="sell", row_4h=last_row, reason=ExitReason.EOD, is_entry=False)
            trade = pm.close_position(fill_price, last_time, ExitReason.EOD)
            self._finalize_trade_meta(trade)

        trades_df = pd.DataFrame([asdict(t) for t in pm.trades]) if pm.trades else pd.DataFrame()
        equity_df = pd.DataFrame(equity_history).set_index("time") if equity_history else pd.DataFrame(columns=["equity", "position", "close"])
        stats = self._calc_stats(trades_df, equity_df[["equity", "position"]] if not equity_df.empty else equity_df)
        stats.update(
            {
                "EntryExecutionMode": self.p.entry_execution_mode,
                "IntrabarPathMode": self.p.intrabar_path_mode,
                "IntrabarExecutionModel": self.p.intrabar_execution_model,
                "CandidateName": self.tp.candidate_name,
            }
        )
        return {
            "trades": trades_df,
            "equity": equity_df,
            "stats": stats,
            "signals": df_4h_indexed,
            "trade_meta": pd.DataFrame(self.closed_trade_meta),
            "params": asdict(self.tp),
        }


def make_candidates() -> List[TrendLongParams]:
    return [
        TrendLongParams(
            candidate_name="donchian_55_chandelier",
            description="55-bar breakout, EMA200 regime, positive EMA slope, mild ADX filter, slow chandelier trail.",
            breakout_mode="donchian",
            donchian_entry_len=55,
            adx_min=18.0,
            close_location_min=0.50,
            range_atr_min=0.35,
            initial_stop_atr=3.0,
            trail_atr_mult=4.8,
            trail_activate_atr=2.5,
            break_even_after_atr=1e9,
            use_swing_trail=False,
        ),
        TrendLongParams(
            candidate_name="quality_breakout_40",
            description="40-bar breakout plus bar quality confirmation, EMA200 trend filter, no partial profit taking, slower hybrid trail.",
            breakout_mode="quality_breakout",
            donchian_entry_len=40,
            adx_min=15.0,
            close_location_min=0.68,
            range_atr_min=0.80,
            volume_multiple=1.10,
            initial_stop_atr=3.2,
            trail_atr_mult=4.2,
            trail_activate_atr=2.0,
            use_swing_trail=True,
            swing_trail_lookback=18,
            break_even_after_atr=1e9,
        ),
        TrendLongParams(
            candidate_name="squeeze_release_20",
            description="Squeeze release plus 20-bar breakout inside a bullish EMA200 regime, designed to enter expansion after compression.",
            breakout_mode="squeeze_release",
            donchian_entry_len=20,
            squeeze_threshold=0.90,
            squeeze_bars=6,
            adx_min=14.0,
            close_location_min=0.60,
            range_atr_min=0.55,
            initial_stop_atr=3.4,
            trail_atr_mult=5.0,
            trail_activate_atr=2.5,
            use_swing_trail=False,
            break_even_after_atr=1e9,
        ),
    ]


def with_overrides(params: TrendLongParams, **overrides) -> TrendLongParams:
    data = asdict(params)
    data.update(overrides)
    return TrendLongParams(**data)


def run_candidate(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    engine = TrendLongMotherEngine(params, use_intrabar_stop=True)
    return engine.run(df_5m, df_4h)

def calc_sortino(ret: pd.Series) -> float:
    downside = ret[ret < 0]
    if downside.empty:
        return 0.0
    downside_std = float(downside.std())
    if downside_std <= 0:
        return 0.0
    return float(ret.mean()) / downside_std * ANNUALIZATION_4H


def calmar(cagr: float, maxdd: float) -> float:
    if maxdd >= 0:
        return 0.0
    return float(cagr) / abs(float(maxdd))


def buy_hold_metrics(df_4h: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, init_equity: float = 10000.0) -> Dict:
    df = ensure_datetime(df_4h)
    sub = df[(df["timestamp"] >= start) & (df["timestamp"] <= end)].copy().reset_index(drop=True)
    if sub.empty:
        return {}
    equity = init_equity * sub["close"] / float(sub["close"].iloc[0])
    ret = equity.pct_change().fillna(0.0)
    peak = equity.cummax()
    dd = equity / peak - 1.0
    elapsed_days = max((sub["timestamp"].iloc[-1] - sub["timestamp"].iloc[0]).total_seconds() / 86400.0, 1.0)
    years = elapsed_days / 365.25
    final_equity = float(equity.iloc[-1])
    cagr = (final_equity / init_equity) ** (1.0 / years) - 1.0 if years > 0 else 0.0
    sharpe = 0.0
    std = float(ret.std())
    if std > 0:
        sharpe = float(ret.mean()) / std * ANNUALIZATION_4H
    return {
        "FinalEquity": final_equity,
        "TotalReturn_pct": (final_equity / init_equity - 1.0) * 100.0,
        "CAGR": cagr,
        "Sharpe": sharpe,
        "Sortino": calc_sortino(ret),
        "MaxDD_pct": float(dd.min()),
        "Calmar": calmar(cagr, float(dd.min())),
        "Exposure_pct": 100.0,
        "Bars": int(len(sub)),
    }


def behavior_stats(result: Dict, df_5m: pd.DataFrame) -> Dict:
    trades = result["trades"]
    meta = result.get("trade_meta")
    if trades is None or trades.empty:
        return {
            "unique_entries": 0,
            "avg_hold_4h_bars": 0.0,
            "median_hold_4h_bars": 0.0,
            "max_winner_hold_4h_bars": 0.0,
            "top10_winner_contrib_pct": 0.0,
            "top3_winner_contrib_pct": 0.0,
            "exit_mix": {},
            "avg_initial_stop_pct": 0.0,
            "market_exposure_pct": 0.0,
            "beta_like": 0.0,
            "mfe_pct_mean": 0.0,
            "mae_pct_mean": 0.0,
        }
    df = trades.copy()
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)
    df["exit_time"] = pd.to_datetime(df["exit_time"], utc=True)
    hold_4h = (df["exit_time"] - df["entry_time"]).dt.total_seconds() / (240.0 * 60.0)
    winners = df[df["pnl"] > 0].sort_values("pnl", ascending=False)
    total_profit = float(winners["pnl"].sum()) if not winners.empty else 0.0
    top10 = float(winners.head(10)["pnl"].sum()) if not winners.empty else 0.0
    top3 = float(winners.head(3)["pnl"].sum()) if not winners.empty else 0.0
    mfe_values: List[float] = []
    mae_values: List[float] = []
    df_5m_indexed = ensure_datetime(df_5m).set_index("timestamp")
    if meta is not None and not meta.empty:
        meta = meta.copy()
        meta["entry_time"] = pd.to_datetime(meta["entry_time"], utc=True)
        meta["exit_time"] = pd.to_datetime(meta["exit_time"], utc=True)
        for _, row in meta.iterrows():
            window = df_5m_indexed[(df_5m_indexed.index >= row["entry_time"]) & (df_5m_indexed.index <= row["exit_time"])]
            if window.empty:
                continue
            entry_price = float(row["entry_price"])
            mfe_values.append((float(window["high"].max()) - entry_price) / max(entry_price, 1e-12))
            mae_values.append((float(window["low"].min()) - entry_price) / max(entry_price, 1e-12))
    eq = result["equity"].copy()
    exposure = float(eq["position"].mean() * 100.0) if not eq.empty else 0.0
    beta_like = 0.0
    if not eq.empty:
        strategy_ret = eq["equity"].pct_change().fillna(0.0)
        market_px = result["signals"].loc[eq.index, "close"]
        market_ret = market_px.pct_change().fillna(0.0)
        var = float(market_ret.var())
        if var > 0:
            beta_like = float(strategy_ret.cov(market_ret) / var)
    return {
        "unique_entries": int(len(df)),
        "avg_hold_4h_bars": float(hold_4h.mean()),
        "median_hold_4h_bars": float(hold_4h.median()),
        "max_winner_hold_4h_bars": float(hold_4h[df["pnl"] > 0].max()) if (df["pnl"] > 0).any() else 0.0,
        "top10_winner_contrib_pct": float(top10 / total_profit * 100.0) if total_profit > 0 else 0.0,
        "top3_winner_contrib_pct": float(top3 / total_profit * 100.0) if total_profit > 0 else 0.0,
        "exit_mix": df["exit_reason"].value_counts(normalize=True).to_dict(),
        "avg_initial_stop_pct": float(meta["risk_pct"].mean() * 100.0) if meta is not None and not meta.empty else 0.0,
        "market_exposure_pct": exposure,
        "beta_like": beta_like,
        "mfe_pct_mean": float(np.mean(mfe_values) * 100.0) if mfe_values else 0.0,
        "mae_pct_mean": float(np.mean(mae_values) * 100.0) if mae_values else 0.0,
    }


def compare_to_buy_hold(result: Dict, df_4h: pd.DataFrame) -> Dict:
    eq = result["equity"]
    if eq.empty:
        return {}
    start = eq.index[0]
    end = eq.index[-1]
    bh = buy_hold_metrics(df_4h, start, end, init_equity=10000.0)
    stats = result["stats"]
    strategy_ret = pd.Series(eq["equity"]).pct_change().fillna(0.0)
    return {
        "strategy": {
            "TotalReturn_pct": float(stats["TotalReturn_pct"]),
            "CAGR": float(stats["CAGR"]),
            "Sharpe": float(stats["Sharpe"]),
            "Sortino": calc_sortino(strategy_ret),
            "MaxDD_pct": float(stats["MaxDD_pct"]),
            "Calmar": calmar(float(stats["CAGR"]), float(stats["MaxDD_pct"])),
        },
        "buy_hold": bh,
        "delta": {
            "return_vs_bh_pct": float(stats["TotalReturn_pct"] - bh.get("TotalReturn_pct", 0.0)),
            "cagr_vs_bh_pct": float(stats["CAGR"] * 100.0 - bh.get("CAGR", 0.0) * 100.0),
            "maxdd_vs_bh_pct": float(stats["MaxDD_pct"] * 100.0 - bh.get("MaxDD_pct", 0.0) * 100.0),
            "sharpe_vs_bh": float(stats["Sharpe"] - bh.get("Sharpe", 0.0)),
            "calmar_vs_bh": float(calmar(float(stats["CAGR"]), float(stats["MaxDD_pct"])) - bh.get("Calmar", 0.0)),
        },
    }


def research_score(report: Dict) -> float:
    stats = report["result"]["stats"]
    comp = report["buy_hold_comparison"]
    return (
        float(stats["Sharpe"]) * 2.5
        + float(calmar(float(stats["CAGR"]), float(stats["MaxDD_pct"])))
        + float(comp["delta"]["sharpe_vs_bh"]) * 1.5
        + float(comp["delta"]["calmar_vs_bh"]) * 1.5
        + min(float(stats["TotalReturn_pct"]) / 100.0, 4.0)
    )


def generic_yearly_eval(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    years = sorted(ensure_datetime(df_4h)["timestamp"].dt.year.unique().tolist())
    rows = []
    d5 = ensure_datetime(df_5m)
    d4 = ensure_datetime(df_4h)
    for year in years:
        start = pd.Timestamp(f"{year}-01-01", tz="UTC")
        end = pd.Timestamp(f"{year + 1}-01-01", tz="UTC")
        sub4 = d4[(d4["timestamp"] >= start) & (d4["timestamp"] < end)]
        if len(sub4) < 180:
            continue
        sub5 = d5[(d5["timestamp"] >= start) & (d5["timestamp"] < end)]
        result = run_candidate(sub5, sub4, params)
        stats = result["stats"]
        rows.append({
            "year": int(year),
            "Return_pct": float(stats["TotalReturn_pct"]),
            "Sharpe": float(stats["Sharpe"]),
            "MaxDD_pct": float(stats["MaxDD_pct"]),
            "Trades": int(stats["Trades"]),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_year_data"}
    positive_ratio = float((df["Return_pct"] > 0).mean())
    avg_sharpe = float(df["Sharpe"].mean())
    worst_return = float(df["Return_pct"].min())
    passed = (positive_ratio >= 0.50) and (avg_sharpe >= 0.20) and (worst_return > -35.0)
    return {"rows": rows, "positive_ratio": positive_ratio, "avg_sharpe": avg_sharpe, "worst_return_pct": worst_return, "pass": passed}


def generic_rolling_oos(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams, train_years: int = 2) -> Dict:
    years = sorted(ensure_datetime(df_4h)["timestamp"].dt.year.unique().tolist())
    rows = []
    d5 = ensure_datetime(df_5m)
    d4 = ensure_datetime(df_4h)
    for oos_year in years:
        train_set = [y for y in years if (oos_year - train_years) <= y < oos_year]
        if len(train_set) < train_years:
            continue
        start = pd.Timestamp(f"{oos_year}-01-01", tz="UTC")
        end = pd.Timestamp(f"{oos_year + 1}-01-01", tz="UTC")
        sub4 = d4[(d4["timestamp"] >= start) & (d4["timestamp"] < end)]
        if len(sub4) < 180:
            continue
        sub5 = d5[(d5["timestamp"] >= start) & (d5["timestamp"] < end)]
        result = run_candidate(sub5, sub4, params)
        stats = result["stats"]
        rows.append({"oos_year": int(oos_year), "Return_pct": float(stats["TotalReturn_pct"]), "Sharpe": float(stats["Sharpe"]), "Trades": int(stats["Trades"])})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_oos_data"}
    avg_sharpe = float(df["Sharpe"].mean())
    positive_ratio = float((df["Return_pct"] > 0).mean())
    passed = (avg_sharpe >= 0.15) and (positive_ratio >= 0.45)
    return {"rows": rows, "avg_sharpe": avg_sharpe, "positive_ratio": positive_ratio, "pass": passed}

def generic_regime_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    regimes = [
        ("bull_2020_2021", "2020-01-01", "2022-01-01"),
        ("bear_2022", "2022-01-01", "2023-01-01"),
        ("mixed_2023_2025", "2023-01-01", "2026-01-01"),
    ]
    rows = []
    d5 = ensure_datetime(df_5m)
    d4 = ensure_datetime(df_4h)
    for name, start_text, end_text in regimes:
        start = pd.Timestamp(start_text, tz="UTC")
        end = pd.Timestamp(end_text, tz="UTC")
        sub4 = d4[(d4["timestamp"] >= start) & (d4["timestamp"] < end)]
        if len(sub4) < 180:
            continue
        sub5 = d5[(d5["timestamp"] >= start) & (d5["timestamp"] < end)]
        result = run_candidate(sub5, sub4, params)
        stats = result["stats"]
        rows.append({"regime": name, "Return_pct": float(stats["TotalReturn_pct"]), "Sharpe": float(stats["Sharpe"]), "MaxDD_pct": float(stats["MaxDD_pct"]), "Trades": int(stats["Trades"])})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_regimes"}
    passed = bool((df["Return_pct"] > -40.0).all() and (df["MaxDD_pct"] > -0.50).all())
    return {"rows": rows, "pass": passed}


def generic_cost_stress(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    rows = []
    for commission in [0.06, 0.10, 0.15, 0.20]:
        result = run_candidate(df_5m, df_4h, with_overrides(params, commission_pct=commission))
        stats = result["stats"]
        rows.append({"commission_pct": commission, "Return_pct": float(stats["TotalReturn_pct"]), "Sharpe": float(stats["Sharpe"]), "MaxDD_pct": float(stats["MaxDD_pct"])})
    df = pd.DataFrame(rows)
    worst = df.iloc[-1]
    passed = (float(worst["Return_pct"]) > -20.0) and (float(worst["MaxDD_pct"]) >= -0.40)
    return {"rows": rows, "pass": passed}


def generic_slippage_stress(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    scenarios = [
        ("default", {}),
        ("stress_1", {"slippage_fixed_bps": 10.0, "slippage_breakout_extra_bps": 8.0, "slippage_stop_extra_bps": 12.0, "slippage_range_weight": 0.06, "slippage_max_bps": 30.0}),
        ("stress_2", {"slippage_fixed_bps": 15.0, "slippage_breakout_extra_bps": 12.0, "slippage_stop_extra_bps": 15.0, "slippage_range_weight": 0.08, "slippage_max_bps": 40.0}),
    ]
    rows = []
    for name, overrides in scenarios:
        result = run_candidate(df_5m, df_4h, with_overrides(params, **overrides))
        stats = result["stats"]
        rows.append({"scenario": name, "Return_pct": float(stats["TotalReturn_pct"]), "Sharpe": float(stats["Sharpe"]), "MaxDD_pct": float(stats["MaxDD_pct"])})
    worst = rows[-1]
    passed = (worst["MaxDD_pct"] >= -0.45) and (worst["Return_pct"] > -30.0)
    return {"rows": rows, "pass": passed}


def generic_execution_mode_stress(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    rows = []
    for mode in ["next_bar_open", "live_runner_next_5m_close"]:
        result = run_candidate(df_5m, df_4h, with_overrides(params, entry_execution_mode=mode))
        stats = result["stats"]
        rows.append({"mode": mode, "Return_pct": float(stats["TotalReturn_pct"]), "Sharpe": float(stats["Sharpe"]), "MaxDD_pct": float(stats["MaxDD_pct"])})
    passed = rows[-1]["MaxDD_pct"] >= -0.45
    return {"rows": rows, "pass": passed}


def generic_intrabar_path_stress(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    rows = []
    scenarios = [
        ("default", {}),
        ("stress", {"entry_execution_mode": "live_runner_next_5m_close", "intrabar_execution_model": "segment_path_same_bar", "intrabar_path_mode": "pessimistic"}),
    ]
    for name, overrides in scenarios:
        result = run_candidate(df_5m, df_4h, with_overrides(params, **overrides))
        stats = result["stats"]
        rows.append({"scenario": name, "Return_pct": float(stats["TotalReturn_pct"]), "Sharpe": float(stats["Sharpe"]), "MaxDD_pct": float(stats["MaxDD_pct"])})
    passed = rows[-1]["MaxDD_pct"] >= -0.45
    return {"rows": rows, "pass": passed}


def gatekeeper_v2_for_long_trend(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams, workdir: Path) -> Dict:
    baseline_result = run_candidate(df_5m, df_4h, params)
    gate = {
        "baseline_gate": baseline_gate(baseline_result["stats"]),
        "yearly": generic_yearly_eval(df_5m, df_4h, params),
        "rolling_oos": generic_rolling_oos(df_5m, df_4h, params),
        "regime": generic_regime_test(df_5m, df_4h, params),
        "cost_stress": generic_cost_stress(df_5m, df_4h, params),
        "slippage_stress": generic_slippage_stress(df_5m, df_4h, params),
        "execution_mode_stress": generic_execution_mode_stress(df_5m, df_4h, params),
        "intrabar_path_stress": generic_intrabar_path_stress(df_5m, df_4h, params),
        "live_safety_check": live_safety_check(workdir),
        "baseline_stats": baseline_result["stats"],
    }
    summary = {name: bool(gate[name].get("pass", False)) for name in [
        "baseline_gate",
        "yearly",
        "rolling_oos",
        "regime",
        "cost_stress",
        "slippage_stress",
        "execution_mode_stress",
        "intrabar_path_stress",
        "live_safety_check",
    ]}
    gate["gate_summary"] = summary
    gate["final_pass"] = all(summary.values())
    trades = int(gate["baseline_gate"].get("Trades", 0))
    low_freq_mismatch = (
        (not gate["baseline_gate"]["pass"])
        and trades < 250
        and float(gate["baseline_gate"]["Sharpe"]) >= 0.80
        and float(gate["baseline_gate"]["ProfitFactor"]) >= 1.15
        and float(gate["baseline_gate"]["MaxDD_pct"]) >= -0.30
    )
    gate["trend_gate_mismatch"] = {
        "likely_trade_count_mismatch": bool(low_freq_mismatch),
        "comment": "Legacy baseline_gate trade threshold may be too high for a low-frequency trend mother." if low_freq_mismatch else "No obvious gate mismatch detected.",
    }
    return gate


def candidate_report(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    result = run_candidate(df_5m, df_4h, params)
    bh = compare_to_buy_hold(result, df_4h)
    behavior = behavior_stats(result, df_5m)
    gate = gatekeeper_v2_for_long_trend(df_5m, df_4h, params, Path("."))
    return {
        "params": asdict(params),
        "result": result,
        "buy_hold_comparison": bh,
        "behavior": behavior,
        "gatekeeper_v2": gate,
        "score": research_score({"result": result, "buy_hold_comparison": bh}),
    }


def compact_report(report: Dict) -> Dict:
    stats = report["result"]["stats"]
    return {
        "candidate_name": report["params"]["candidate_name"],
        "description": report["params"]["description"],
        "stats": {
            "Return_pct": float(stats["TotalReturn_pct"]),
            "CAGR_pct": float(stats["CAGR"] * 100.0),
            "Sharpe": float(stats["Sharpe"]),
            "MaxDD_pct": float(stats["MaxDD_pct"] * 100.0),
            "PF": float(stats["ProfitFactor"]),
            "Trades": int(stats["Trades"]),
        },
        "buy_hold_comparison": report["buy_hold_comparison"],
        "behavior": report["behavior"],
        "gate_summary": report["gatekeeper_v2"]["gate_summary"],
        "final_pass": bool(report["gatekeeper_v2"]["final_pass"]),
        "trend_gate_mismatch": report["gatekeeper_v2"]["trend_gate_mismatch"],
        "score": float(report["score"]),
    }

def local_neighborhood(base: TrendLongParams) -> List[TrendLongParams]:
    return [
        base,
        with_overrides(base, donchian_entry_len=max(base.donchian_entry_len - 15, 20)),
        with_overrides(base, donchian_entry_len=base.donchian_entry_len + 15),
        with_overrides(base, trail_atr_mult=max(base.trail_atr_mult - 0.6, 3.5)),
        with_overrides(base, trail_atr_mult=base.trail_atr_mult + 0.6),
        with_overrides(base, adx_min=max(base.adx_min - 4.0, 0.0), use_adx_filter=base.use_adx_filter),
        with_overrides(base, adx_min=base.adx_min + 4.0, use_adx_filter=base.use_adx_filter),
        with_overrides(base, initial_stop_atr=max(base.initial_stop_atr - 0.4, 2.2)),
        with_overrides(base, initial_stop_atr=base.initial_stop_atr + 0.4),
        with_overrides(base, break_even_after_atr=6.0),
    ]


def dedupe_params(params_list: List[TrendLongParams]) -> List[TrendLongParams]:
    seen = set()
    out: List[TrendLongParams] = []
    for params in params_list:
        key = json.dumps(asdict(params), sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(params)
    return out


def choose_launch_params(report: Dict) -> TrendLongParams:
    base = TrendLongParams(**report["params"])
    return with_overrides(base, position_pct=35.0)


def choose_signal_reference(report: Dict) -> TrendLongParams:
    base = TrendLongParams(**report["params"])
    return with_overrides(base, position_pct=100.0)


def write_outputs(payload: Dict, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    serializable = json.loads(json.dumps(payload, default=str, ensure_ascii=False))
    (outdir / "btc_longonly_trend_report.json").write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")
    Path("btc_longonly_trend_report.json").write_text(json.dumps(serializable, indent=2, ensure_ascii=False), encoding="utf-8")

    summary_lines = [
        f"recommended_research_candidate={payload['research_optimal']['candidate_name']}",
        f"launch_status={payload['launch_optimal']['status']}",
        f"closer_than_v85_as_independent_strategy={payload['summary_flags']['closer_than_v85']}",
        f"bh_outperform_potential={payload['summary_flags']['outperform_bh_potential']}",
        f"pause_old_v85_mother_as_primary={payload['summary_flags']['pause_old_v85_primary']}",
    ]
    (outdir / "btc_longonly_trend_summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")
    Path("btc_longonly_trend_summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    lines = [
        "# BTC Long-Only Trend Mother Report",
        "",
        f"- Recommended: {payload['launch_optimal']['status']}",
        f"- Compared with old v85: {payload['summary_flags']['closer_than_v85_text']}",
        f"- Potential to beat buy-and-hold: {payload['summary_flags']['outperform_bh_text']}",
        f"- Daily default research tuple: {payload['default_research_tuple']}",
        f"- Stress / gate tuple: {payload['stress_tuple']}",
        "",
        "## Mother Design",
        "",
        "- New line is long-only, 4H trend-following, no short symmetry, no partial TP.",
        "- Entry is causal and uses next_bar_open under the calibrated intrabar model.",
        "- Exit philosophy is slow trailing with structure-aware initial stop; no early profit harvesting.",
        "- This differs from old v85 because it removes score stacking and focuses on low-frequency breakout continuation.",
        "",
        "## Candidates",
        "",
    ]
    for item in payload["candidate_summaries"]:
        lines.extend([
            f"### {item['candidate_name']}",
            f"- rules: {item['description']}",
            f"- stats: Return {item['stats']['Return_pct']:.2f}%, CAGR {item['stats']['CAGR_pct']:.2f}%, Sharpe {item['stats']['Sharpe']:.3f}, MaxDD {item['stats']['MaxDD_pct']:.2f}%, PF {item['stats']['PF']:.3f}, Trades {item['stats']['Trades']}",
            f"- vs B&H: return delta {item['buy_hold_comparison']['delta']['return_vs_bh_pct']:.2f}pp, sharpe delta {item['buy_hold_comparison']['delta']['sharpe_vs_bh']:.3f}, calmar delta {item['buy_hold_comparison']['delta']['calmar_vs_bh']:.3f}",
            f"- holding: avg {item['behavior']['avg_hold_4h_bars']:.1f} bars, median {item['behavior']['median_hold_4h_bars']:.1f}, top10 winners contrib {item['behavior']['top10_winner_contrib_pct']:.1f}%",
            f"- gate_summary: {json.dumps(item['gate_summary'], ensure_ascii=False)}",
            f"- trend_gate_mismatch: {item['trend_gate_mismatch']['comment']}",
            "",
        ])
    lines.extend([
        "## Buy-And-Hold Comparison",
        "",
        f"- Research optimal strategy return delta vs B&H: {payload['research_optimal']['buy_hold_delta_return_pct']:.2f}pp",
        f"- Research optimal strategy Sharpe delta vs B&H: {payload['research_optimal']['buy_hold_delta_sharpe']:.3f}",
        f"- Research optimal strategy Calmar delta vs B&H: {payload['research_optimal']['buy_hold_delta_calmar']:.3f}",
        "",
        "## Holding Continuity",
        "",
        f"- Research optimal avg hold: {payload['research_optimal']['behavior']['avg_hold_4h_bars']:.1f} 4H bars",
        f"- Research optimal median hold: {payload['research_optimal']['behavior']['median_hold_4h_bars']:.1f} 4H bars",
        f"- Research optimal max winner hold: {payload['research_optimal']['behavior']['max_winner_hold_4h_bars']:.1f} 4H bars",
        f"- Research optimal top10 winner contribution: {payload['research_optimal']['behavior']['top10_winner_contrib_pct']:.1f}%",
        f"- Research optimal exit mix: {json.dumps(payload['research_optimal']['behavior']['exit_mix'], ensure_ascii=False)}",
        "",
        "## Recommendation",
        "",
        f"- launch_optimal: {payload['launch_optimal']['status']} ({payload['launch_optimal']['reason']})",
        f"- research_optimal: {payload['research_optimal']['candidate_name']}",
        f"- signal_reference: {payload['signal_reference']['candidate_name']}",
        f"- next step: {payload['next_step']}",
    ])
    (outdir / "BTC_LONGONLY_TREND_MOTHER_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    Path("BTC_LONGONLY_TREND_MOTHER_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    base_candidates = make_candidates()
    candidate_reports = [candidate_report(df_5m, df_4h, params) for params in base_candidates]
    candidate_reports.sort(key=research_score, reverse=True)

    top_base = TrendLongParams(**candidate_reports[0]["params"])
    neighborhood = dedupe_params(local_neighborhood(top_base))
    neighborhood_reports = [candidate_report(df_5m, df_4h, params) for params in neighborhood]
    neighborhood_reports.sort(key=research_score, reverse=True)
    research_opt = neighborhood_reports[0]

    signal_params = choose_signal_reference(research_opt)
    signal_report = candidate_report(df_5m, df_4h, signal_params)
    launch_params = choose_launch_params(research_opt)
    launch_report = candidate_report(df_5m, df_4h, launch_params)

    launch_status = "LAUNCH_GO" if launch_report["gatekeeper_v2"]["final_pass"] else "LAUNCH_NO_GO"
    closer_than_v85 = bool(research_opt["buy_hold_comparison"]["strategy"]["Calmar"] > 0 and research_opt["behavior"]["avg_hold_4h_bars"] > 8)
    outperform_bh = bool(research_opt["buy_hold_comparison"]["delta"]["calmar_vs_bh"] > 0 and research_opt["buy_hold_comparison"]["delta"]["sharpe_vs_bh"] > 0)

    payload = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "default_research_tuple": "next_bar_open + legacy_bar_extrema + midpoint + full_model",
        "stress_tuple": "live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model",
        "candidate_summaries": [compact_report(r) for r in candidate_reports],
        "neighborhood_summaries": [compact_report(r) for r in neighborhood_reports[:8]],
        "research_optimal": {
            "candidate_name": research_opt["params"]["candidate_name"],
            "params": research_opt["params"],
            "stats": compact_report(research_opt)["stats"],
            "behavior": research_opt["behavior"],
            "gate_summary": research_opt["gatekeeper_v2"]["gate_summary"],
            "final_pass": research_opt["gatekeeper_v2"]["final_pass"],
            "buy_hold_delta_return_pct": research_opt["buy_hold_comparison"]["delta"]["return_vs_bh_pct"],
            "buy_hold_delta_sharpe": research_opt["buy_hold_comparison"]["delta"]["sharpe_vs_bh"],
            "buy_hold_delta_calmar": research_opt["buy_hold_comparison"]["delta"]["calmar_vs_bh"],
        },
        "signal_reference": {
            "candidate_name": signal_report["params"]["candidate_name"],
            "params": signal_report["params"],
            "stats": compact_report(signal_report)["stats"],
            "gate_summary": signal_report["gatekeeper_v2"]["gate_summary"],
            "final_pass": signal_report["gatekeeper_v2"]["final_pass"],
        },
        "launch_optimal": {
            "status": launch_status,
            "candidate_name": launch_report["params"]["candidate_name"],
            "params": launch_report["params"],
            "stats": compact_report(launch_report)["stats"],
            "gate_summary": launch_report["gatekeeper_v2"]["gate_summary"],
            "final_pass": launch_report["gatekeeper_v2"]["final_pass"],
            "reason": "passes all current Gatekeeper V2 checks" if launch_status == "LAUNCH_GO" else "fails one or more Gatekeeper V2 checks under the calibrated default/stress split",
        },
        "summary_flags": {
            "closer_than_v85": closer_than_v85,
            "closer_than_v85_text": "yes, this is structurally closer to an independent BTC trend system than the old v85 long+short mother" if closer_than_v85 else "not yet; still too thin or too passive to replace buy-and-hold as a stand-alone core strategy",
            "outperform_bh_potential": outperform_bh,
            "outperform_bh_text": "yes, risk-adjusted edge vs buy-and-hold is visible" if outperform_bh else "not yet; current edge is more defensive than dominant versus buy-and-hold",
            "pause_old_v85_primary": True,
        },
        "next_step": "continue only on the new long-only mother; do not resume old v85 parameter work as the primary line until this mother is either validated or rejected.",
    }

    outdir = Path("data") / f"btc_longonly_trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    write_outputs(payload, outdir)
    print(json.dumps({
        "outdir": str(outdir),
        "research_optimal": payload["research_optimal"],
        "launch_optimal": payload["launch_optimal"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
