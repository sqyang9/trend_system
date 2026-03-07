#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v85_intrabar_backtest.py
========================
Trend Squeeze V8.5 澶氬懆鏈熺洏涓鎹熷洖娴嬬郴缁?
鏍稿績鏋舵瀯锛?- 4H: 淇″彿璁＄畻銆佸紑骞充粨鍐崇瓥
- 5m: 鐩樹腑姝㈡崯/姝㈢泩瑙﹀彂鎵ц

涓ユ牸瀵圭収TradingView v85 PineScript:
- useIntrabarStop=true: 浣跨敤5m绾у埆瑙﹀彂姝㈡崯
- process_orders_on_close=true: 淇″彿鍦?H鏀剁洏纭

Usage:
  python v85_intrabar_backtest.py --data_dir ./data
  python v85_intrabar_backtest.py --data_dir ./data --no_intrabar  # 鍥為€€鍒?H妯″紡楠岃瘉
"""

import argparse
import json
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, List, Tuple
from pathlib import Path
from datetime import datetime, timezone, timedelta
from enum import Enum

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ============================================================
# 1. 鍙傛暟瀹氫箟 (涓ユ牸瀵圭収Pine v85)
# ============================================================

@dataclass
class V85Params:
    """V8.5绛栫暐鍙傛暟 - 瀹屽叏瀵圭収PineScript"""
    
    # 璧勯噾绠＄悊
    init_equity: float = 10000.0
    position_pct: float = 60.0          # single-position allocation pct
    commission_pct: float = 0.06        # one-way commission pct
    slippage: float = 0.0               # 婊戠偣锛堟殏涓嶄娇鐢級
    
    # 鎸ゅ帇鍙傛暟
    bb_period: int = 20                 # squeezeLookback
    squeeze_threshold: float = 0.9      # squeezeThreshold  
    min_squeeze_candles: int = 4        # minSqueezeCandles
    short_squeeze_threshold: float = 0.9
    
    # ATR and stops
    atr_period: int = 14                # atrPeriod
    initial_stop_atr: float = 2.4       # initialStopATR
    trail_start_atr: float = 3.0        # trailStartATR
    trail_offset_atr: float = 2.8       # trailOffsetATR
    break_even_atr: float = 1.7         # breakEvenATR
    
    # 閮ㄥ垎姝㈢泩
    enable_partial_tp: bool = True      # enablePartialTP
    tp1_atr: float = 2.1                # tp1_ATR
    tp1_pct: float = 30.0               # tp1_Pct (%)
    tp2_atr: float = 3.5                # tp2_ATR
    tp2_pct: float = 30.0               # tp2_Pct (%)
    
    # 鍋氱┖
    enable_short: bool = True           # enableShort
    short_only_bear: bool = True        # shortOnlyBear
    
    # 鐜杩囨护
    ema_trend_len: int = 200            # emaTrendLen
    use_env_filter: bool = True         # useEnvFilter
    use_adx_filter: bool = True         # useAdxFilter
    adx_period: int = 11                # adxPeriod
    adx_trend_level: float = 20.0       # adxTrendLevel
    
    # 璇勫垎瑕佹眰
    min_long_score: int = 1             # minLongScore
    min_short_score: int = 3            # minShortScore
    
    # 褰撴棩椋庢帶
    enable_daily_loss_limit: bool = True
    daily_loss_limit_pct: float = 1.5   # %
    cooldown_bars: int = 3


# ============================================================
# 2. 鏋氫妇鍜屾暟鎹粨鏋?# ============================================================

class Direction(Enum):
    FLAT = "flat"
    LONG = "long"
    SHORT = "short"


class ExitReason(Enum):
    TP1 = "TP1"
    TP2 = "TP2"
    SL = "SL"
    BE = "BE"              # 淇濇湰姝㈡崯瑙﹀彂
    TRAIL = "TRAIL"        # 杩借釜姝㈡崯瑙﹀彂
    SIGNAL = "SIGNAL"      # 淇″彿骞充粨
    EOD = "EOD"            # 鏈熸湯骞充粨


@dataclass
class Position:
    """Active position snapshot."""
    direction: Direction
    entry_price: float
    entry_time: pd.Timestamp
    entry_bar_4h: pd.Timestamp      # 寮€浠撶殑4H K绾挎椂闂?    
    initial_qty: float              # 鍒濆鏁伴噺
    current_qty: float              # 褰撳墠鏁伴噺
    
    # 椋庨櫓鍙傛暟
    stop_loss_price: float
    tp1_price: float
    tp2_price: float
    
    # ATR鍊硷紙寮€浠撴椂璁板綍锛岀敤浜庡悗缁绠楋級
    entry_atr: float
    
    # Trigger flags
    tp1_filled: bool = False
    tp2_filled: bool = False
    be_activated: bool = False
    trailing_active: bool = False
    
    # Extremes since entry
    highest_since_entry: float = 0.0
    lowest_since_entry: float = 0.0


@dataclass
class Trade:
    """浜ゆ槗璁板綍"""
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    direction: str
    qty: float
    pnl: float
    commission: float
    exit_reason: str
    entry_bar_4h: pd.Timestamp = None


# ============================================================
# 3. 鎸囨爣璁＄畻寮曟搸 (4H)
# ============================================================

class IndicatorEngine:
    """4H鎸囨爣璁＄畻寮曟搸 - 涓ユ牸瀵圭収Pine"""
    
    def __init__(self, params: V85Params):
        self.p = params
    
    @staticmethod
    def calc_rma(series: pd.Series, period: int) -> pd.Series:
        """RMA (Wilder's Smoothing) - ta.rma()"""
        return series.ewm(alpha=1.0/period, adjust=False).mean()
    
    @staticmethod
    def calc_atr(df: pd.DataFrame, period: int) -> pd.Series:
        """ATR - ta.atr()"""
        high, low, close = df['high'], df['low'], df['close']
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
    def calc_dmi(df: pd.DataFrame, period: int):
        """DMI/ADX - ta.dmi()"""
        high, low, close = df['high'], df['low'], df['close']
        
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        plus_dm = pd.Series(plus_dm, index=df.index)
        
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)
        minus_dm = pd.Series(minus_dm, index=df.index)
        
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = IndicatorEngine.calc_rma(tr, period)
        smooth_plus = IndicatorEngine.calc_rma(plus_dm, period)
        smooth_minus = IndicatorEngine.calc_rma(minus_dm, period)
        
        plus_di = 100 * smooth_plus / atr.replace(0, np.nan)
        minus_di = 100 * smooth_minus / atr.replace(0, np.nan)
        
        di_sum = plus_di + minus_di
        di_diff = (plus_di - minus_di).abs()
        dx = 100 * di_diff / di_sum.replace(0, np.nan)
        
        adx = IndicatorEngine.calc_rma(dx.fillna(0), period)
        
        return plus_di.fillna(0), minus_di.fillna(0), adx.fillna(0)
    
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """璁＄畻鎵€鏈?H鎸囨爣"""
        df = df.copy()
        p = self.p
        
        # ATR
        df['atr'] = self.calc_atr(df, p.atr_period)
        
        # EMA瓒嬪娍
        df['ema_trend'] = self.calc_ema(df['close'], p.ema_trend_len)
        
        # Bollinger bands
        df["bb_basis"] = self.calc_sma(df["close"], p.bb_period)
        df['bb_dev'] = self.calc_stdev(df['close'], p.bb_period)
        df['bb_upper'] = df['bb_basis'] + 2.0 * df['bb_dev']
        df['bb_lower'] = df['bb_basis'] - 2.0 * df['bb_dev']
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_basis']
        
        # Squeeze normalization
        df["bb_width_ma"] = self.calc_sma(df["bb_width"], 200)
        df['bb_width_norm'] = np.where(
            (df['bb_width_ma'].isna()) | (df['bb_width_ma'] == 0),
            0.0,
            df['bb_width'] / df['bb_width_ma']
        )
        
        df['in_squeeze_long'] = df['bb_width_norm'] < p.squeeze_threshold
        df['in_squeeze_short'] = df['bb_width_norm'] < p.short_squeeze_threshold
        
        # 杩炵画鎸ゅ帇璁℃暟
        squeeze_count_long = []
        squeeze_count_short = []
        cnt_long = cnt_short = 0
        
        for i in range(len(df)):
            if df['in_squeeze_long'].iloc[i]:
                cnt_long += 1
            else:
                cnt_long = 0
            squeeze_count_long.append(cnt_long)
            
            if df['in_squeeze_short'].iloc[i]:
                cnt_short += 1
            else:
                cnt_short = 0
            squeeze_count_short.append(cnt_short)
        
        df['squeeze_count_long'] = squeeze_count_long
        df['squeeze_count_short'] = squeeze_count_short
        df['squeeze_quality_long'] = df['squeeze_count_long'] >= p.min_squeeze_candles
        df['squeeze_quality_short'] = df['squeeze_count_short'] >= p.min_squeeze_candles
        
        # 鍔ㄩ噺
        df['mom'] = self.calc_mom(df['close'], 12)
        df['mom_up'] = (df['mom'] > 0) & (df['mom'] > df['mom'].shift(1))
        df['mom_down'] = (df['mom'] < 0) & (df['mom'] < df['mom'].shift(1))
        
        # Volume features
        df["vol_ma"] = self.calc_sma(df["volume"], 20)
        df['vol_spike'] = df['volume'] > df['vol_ma'] * 1.2
        
        # 瓒嬪娍
        df['bull'] = (df['close'] > df['ema_trend']) & df['ema_trend'].notna()
        df['bear'] = (df['close'] < df['ema_trend']) & df['ema_trend'].notna()
        
        # ADX
        _, _, df['adx'] = self.calc_dmi(df, p.adx_period)
        df['strong_trend'] = (df['adx'] > p.adx_trend_level) & df['adx'].notna()
        
        return df


# ============================================================
# 4. 璇勫垎涓庝俊鍙疯绠?# ============================================================

def calc_long_score(row, prev_row) -> int:
    """璁＄畻鍋氬璇勫垎 - 瀵圭収Pine"""
    score = 0
    
    # 1. 鎸ゅ帇閲婃斁
    if prev_row['in_squeeze_long'] and not row['in_squeeze_long']:
        score += 1
    
    # 2. 绐佺牬涓婅建
    if row['close'] > row['bb_upper']:
        score += 1
    
    # 3. 鎸ゅ帇璐ㄩ噺
    if prev_row['squeeze_quality_long']:
        score += 1
    
    # 4. 鍔ㄩ噺鍚戜笂
    if row['mom_up']:
        score += 1
    
    # 5. 鏀鹃噺
    if row['vol_spike']:
        score += 1
    
    return score


def calc_short_score(row, prev_row) -> int:
    """璁＄畻鍋氱┖璇勫垎 - 瀵圭収Pine"""
    score = 0
    
    # 1. 鎸ゅ帇閲婃斁
    if prev_row['in_squeeze_short'] and not row['in_squeeze_short']:
        score += 1
    
    # 2. 璺岀牬涓嬭建
    if row['close'] < row['bb_lower']:
        score += 1
    
    # 3. 鎸ゅ帇璐ㄩ噺
    if prev_row['squeeze_quality_short']:
        score += 1
    
    # 4. 鍔ㄩ噺鍚戜笅
    if row['mom_down']:
        score += 1
    
    # 5. 鏀鹃噺
    if row['vol_spike']:
        score += 1
    
    return score


def check_entry_conditions(row, prev_row, p: V85Params, has_position: bool) -> Tuple[bool, bool]:
    """
    妫€鏌ュ紑浠撴潯浠?    杩斿洖: (long_signal, short_signal)
    """
    if has_position:
        return False, False
    
    # 鐜杩囨护
    long_env_ok = row['bull'] if p.use_env_filter else True
    short_env_ok = row['bear'] if p.use_env_filter else True
    
    # ADX杩囨护 - 鍏抽敭淇锛氫笉鍙栧弽!
    # Pine: longTrendOK = not useAdxFilter or strongTrend
    long_trend_ok = (not p.use_adx_filter) or row['strong_trend']
    short_trend_ok = (not p.use_adx_filter) or row['strong_trend']
    
    long_allowed = long_env_ok and long_trend_ok
    short_allowed = short_env_ok and short_trend_ok and ((not p.short_only_bear) or row['bear'])
    
    # 璇勫垎
    long_score = calc_long_score(row, prev_row)
    short_score = calc_short_score(row, prev_row)
    
    long_signal = long_allowed and long_score >= p.min_long_score
    short_signal = p.enable_short and short_allowed and short_score >= p.min_short_score
    
    return long_signal, short_signal


# ============================================================
# 5. 浠撲綅绠＄悊鍣?# ============================================================

class PositionManager:
    """Position and order state manager."""
    
    def __init__(self, params: V85Params):
        self.p = params
        self.position: Optional[Position] = None
        self.trades: List[Trade] = []
        self.equity = params.init_equity
    
    def is_flat(self) -> bool:
        return self.position is None
    
    def is_open(self) -> bool:
        return self.position is not None
    
    def open_position(self, direction: Direction, price: float, qty: float,
                     atr: float, time: pd.Timestamp, bar_4h: pd.Timestamp):
        """Open a new position."""
        if self.is_open():
            return
        
        # Calculate stop-loss and take-profit prices
        if direction == Direction.LONG:
            sl = price - self.p.initial_stop_atr * atr
            tp1 = price + self.p.tp1_atr * atr
            tp2 = price + self.p.tp2_atr * atr
        else:
            sl = price + self.p.initial_stop_atr * atr
            tp1 = price - self.p.tp1_atr * atr
            tp2 = price - self.p.tp2_atr * atr
        
        self.position = Position(
            direction=direction,
            entry_price=price,
            entry_time=time,
            entry_bar_4h=bar_4h,
            initial_qty=qty,
            current_qty=qty,
            stop_loss_price=sl,
            tp1_price=tp1,
            tp2_price=tp2,
            entry_atr=atr,
            highest_since_entry=price,
            lowest_since_entry=price
        )
        
        # 鎵ｉ櫎寮€浠撴墜缁垂
        commission = price * qty * (self.p.commission_pct / 100)
        self.equity -= commission
    
    def check_intrabar_triggers(self, high: float, low: float, current_atr: float,
                                bar_time: pd.Timestamp) -> List[Tuple[ExitReason, float, float]]:
        """
        妫€鏌?m K绾夸腑鐨勮Е鍙戜簨浠?        
        杩斿洖: [(exit_reason, exit_price, exit_qty), ...]
        
        浼樺厛绾ч『搴? SL > TP2 > TP1 > BE/Trail鏇存柊
        """
        if self.is_flat():
            return []
        
        pos = self.position
        triggers = []
        
        # Update price extremes seen since entry
        pos.highest_since_entry = max(pos.highest_since_entry, high)
        pos.lowest_since_entry = min(pos.lowest_since_entry, low)
        
        # ========== 1. 姝㈡崯妫€鏌?(鏈€楂樹紭鍏堢骇) ==========
        if pos.direction == Direction.LONG:
            if low <= pos.stop_loss_price:
                triggers.append((ExitReason.SL, pos.stop_loss_price, pos.current_qty))
                return triggers  # stop hit takes priority
        else:  # SHORT
            if high >= pos.stop_loss_price:
                triggers.append((ExitReason.SL, pos.stop_loss_price, pos.current_qty))
                return triggers
        
        # ========== 2. 璁＄畻褰撳墠鐩堝埄ATR ==========
        if pos.direction == Direction.LONG:
            current_profit = high - pos.entry_price
        else:
            current_profit = pos.entry_price - low
        
        profit_atr = current_profit / current_atr if current_atr > 0 else 0
        
        # ========== 3. 閮ㄥ垎姝㈢泩妫€鏌?==========
        if self.p.enable_partial_tp:
            # TP1
            if not pos.tp1_filled and profit_atr >= self.p.tp1_atr:
                tp1_qty = pos.initial_qty * (self.p.tp1_pct / 100)
                tp1_qty = min(tp1_qty, pos.current_qty)
                if tp1_qty > 0:
                    triggers.append((ExitReason.TP1, pos.tp1_price, tp1_qty))
                    pos.tp1_filled = True
                    pos.current_qty -= tp1_qty
            
            # TP2 (鍦═P1涔嬪悗)
            if pos.tp1_filled and not pos.tp2_filled and profit_atr >= self.p.tp2_atr:
                tp2_qty = pos.initial_qty * (self.p.tp2_pct / 100)
                tp2_qty = min(tp2_qty, pos.current_qty)
                if tp2_qty > 0:
                    triggers.append((ExitReason.TP2, pos.tp2_price, tp2_qty))
                    pos.tp2_filled = True
                    pos.current_qty -= tp2_qty
        
        # ========== 4. 淇濇湰姝㈡崯鏇存柊 ==========
        if not pos.be_activated and profit_atr >= self.p.break_even_atr:
            if pos.direction == Direction.LONG:
                pos.stop_loss_price = max(pos.stop_loss_price, pos.entry_price)
            else:
                pos.stop_loss_price = min(pos.stop_loss_price, pos.entry_price)
            pos.be_activated = True
        
        # ========== 5. 杩借釜姝㈡崯鏇存柊 ==========
        if profit_atr >= self.p.trail_start_atr:
            pos.trailing_active = True
            
            if pos.direction == Direction.LONG:
                new_trail = pos.highest_since_entry - self.p.trail_offset_atr * current_atr
                pos.stop_loss_price = max(pos.stop_loss_price, new_trail)
            else:
                new_trail = pos.lowest_since_entry + self.p.trail_offset_atr * current_atr
                pos.stop_loss_price = min(pos.stop_loss_price, new_trail)
        
        return triggers
    
    def execute_exit(self, reason: ExitReason, price: float, qty: float,
                    time: pd.Timestamp) -> Trade:
        """鎵ц鍑哄満"""
        if self.is_flat():
            return None
        
        pos = self.position
        
        # 璁＄畻PnL
        if pos.direction == Direction.LONG:
            pnl = (price - pos.entry_price) * qty
        else:
            pnl = (pos.entry_price - price) * qty
        
        # Exit commission
        commission = price * qty * (self.p.commission_pct / 100)
        
        # 鏇存柊鏉冪泭
        self.equity += pnl - commission
        
        # 鍒涘缓浜ゆ槗璁板綍
        trade = Trade(
            entry_time=pos.entry_time,
            exit_time=time,
            entry_price=pos.entry_price,
            exit_price=price,
            direction=pos.direction.value,
            qty=qty,
            pnl=pnl - commission,
            commission=commission,
            exit_reason=reason.value,
            entry_bar_4h=pos.entry_bar_4h
        )
        
        self.trades.append(trade)
        
        # Clear position if fully closed
        if pos.current_qty <= 0 or reason in [ExitReason.SL, ExitReason.SIGNAL, ExitReason.EOD]:
            self.position = None
        
        return trade
    
    def close_position(self, price: float, time: pd.Timestamp, 
                      reason: ExitReason = ExitReason.SIGNAL) -> Trade:
        """瀹屽叏骞充粨"""
        if self.is_flat():
            return None
        
        return self.execute_exit(reason, price, self.position.current_qty, time)

    def snapshot_position(self) -> Dict:
        """Return the active position state for live/research reuse."""
        if self.is_flat():
            return {}

        pos = self.position
        return {
            'direction': pos.direction.value,
            'entry_price': float(pos.entry_price),
            'entry_time': pos.entry_time.isoformat(),
            'entry_bar_4h': pos.entry_bar_4h.isoformat(),
            'initial_qty': float(pos.initial_qty),
            'current_qty': float(pos.current_qty),
            'stop_loss_price': float(pos.stop_loss_price),
            'tp1_price': float(pos.tp1_price),
            'tp2_price': float(pos.tp2_price),
            'entry_atr': float(pos.entry_atr),
            'tp1_filled': bool(pos.tp1_filled),
            'tp2_filled': bool(pos.tp2_filled),
            'be_activated': bool(pos.be_activated),
            'trailing_active': bool(pos.trailing_active),
            'highest_since_entry': float(pos.highest_since_entry),
            'lowest_since_entry': float(pos.lowest_since_entry),
        }


# ============================================================
# 6. 鍥炴祴寮曟搸
# ============================================================

class IntrabarBacktestEngine:
    """Multi-timeframe intrabar backtest engine."""
    
    def __init__(self, params: V85Params, use_intrabar_stop: bool = True):
        self.p = params
        self.use_intrabar_stop = use_intrabar_stop
        self.indicator_engine = IndicatorEngine(params)
    
    def run(self, df_5m: pd.DataFrame, df_4h: pd.DataFrame, *, close_on_end: bool = True, allow_entry_on_last_bar: bool = True) -> Dict:
        """
        鎵ц鍥炴祴
        
        Args:
            df_5m: 5鍒嗛挓鏁版嵁 (columns: timestamp, open, high, low, close, volume)
            df_4h: 4灏忔椂鏁版嵁 (鍚屼笂)
        
        Returns:
            鍥炴祴缁撴灉瀛楀吀
        """
        print("=" * 70)
        print(f"V8.5 澶氬懆鏈熷洖娴嬪紩鎿?({'鐩樹腑姝㈡崯' if self.use_intrabar_stop else '鏀剁洏姝㈡崯'})")
        print("=" * 70)
        
        # 1. 璁＄畻4H鎸囨爣
        print("\n[1/4] 璁＄畻4H鎸囨爣...")
        df_4h = self.indicator_engine.compute_indicators(df_4h)
        
        # 2. Build the 4H->5m mapping
        print("[2/4] 寤虹珛鏃堕棿鏄犲皠...")
        mapping = self._build_mapping(df_5m, df_4h)
        print(f"  鏄犲皠浜?{len(mapping)} 涓?H鍛ㄦ湡")
        
        # 3. 鎵ц鍥炴祴
        print(f"[3/4] 鎵ц鍥炴祴...")
        pm = PositionManager(self.p)
        equity_history = []
        
        # 褰撴棩椋庢帶鍙橀噺
        day_start_equity = self.p.init_equity
        current_day = None
        day_limit_hit = False
        bars_since_hit = 0
        
        # 纭繚df_4h鏈夋纭殑绱㈠紩
        if 'timestamp' in df_4h.columns:
            df_4h = df_4h.set_index('timestamp')
        df_4h = df_4h.sort_index()
        
        # 纭繚df_5m鏈夋纭殑绱㈠紩
        if 'timestamp' in df_5m.columns:
            df_5m_indexed = df_5m.set_index('timestamp').sort_index()
        else:
            df_5m_indexed = df_5m.sort_index()
        
        bar_count = len(df_4h)
        
        for i in range(1, bar_count):
            prev_row = df_4h.iloc[i - 1]
            row = df_4h.iloc[i]
            ts_4h = df_4h.index[i]
            
            atr = row['atr']
            if pd.isna(atr) or atr <= 0:
                continue
            
            # ========== 褰撴棩椋庢帶 ==========
            bar_day = ts_4h.date() if hasattr(ts_4h, 'date') else ts_4h
            new_day = (bar_day != current_day)
            
            if new_day:
                day_start_equity = pm.equity
                current_day = bar_day
                day_limit_hit = False
                bars_since_hit = 0
            else:
                if day_limit_hit:
                    bars_since_hit += 1
            
            if self.p.enable_daily_loss_limit and not day_limit_hit and day_start_equity > 0:
                day_pnl_pct = (pm.equity - day_start_equity) / day_start_equity * 100
                if day_pnl_pct <= -self.p.daily_loss_limit_pct:
                    day_limit_hit = True
                    bars_since_hit = 0
            
            cooldown_passed = bars_since_hit >= self.p.cooldown_bars
            risk_allowed = (not self.p.enable_daily_loss_limit) or (not day_limit_hit) or cooldown_passed
            
            # ========== 鐩樹腑姝㈡崯妫€鏌?(鍦?H鏀剁洏鍓? ==========
            if self.use_intrabar_stop and pm.is_open() and ts_4h in mapping:
                five_min_indices = mapping[ts_4h]
                
                for ts_5m in five_min_indices:
                    if ts_5m not in df_5m_indexed.index:
                        continue
                    
                    bar_5m = df_5m_indexed.loc[ts_5m]
                    
                    # Check intrabar triggers
                    triggers = pm.check_intrabar_triggers(
                        bar_5m['high'], bar_5m['low'], atr, ts_5m
                    )
                    
                    # 鎵ц瑙﹀彂
                    for reason, price, qty in triggers:
                        pm.execute_exit(reason, price, qty, ts_5m)
                    
                    # 濡傛灉宸插钩浠擄紝璺冲嚭5m寰幆
                    if pm.is_flat():
                        break
            
            # ========== 4H鏀剁洏淇″彿澶勭悊 ==========
            # 杩欓噷澶勭悊鏂板紑浠撲俊鍙?
            is_last_bar = (i == bar_count - 1)
            if pm.is_flat() and risk_allowed and (allow_entry_on_last_bar or not is_last_bar):
                long_signal, short_signal = check_entry_conditions(
                    row, prev_row, self.p, pm.is_open()
                )
                
                if long_signal:
                    # 璁＄畻浠撲綅
                    position_value = pm.equity * (self.p.position_pct / 100)
                    qty = position_value / row['close']
                    
                    pm.open_position(
                        Direction.LONG, row['close'], qty, atr, ts_4h, ts_4h
                    )
                
                elif short_signal:
                    position_value = pm.equity * (self.p.position_pct / 100)
                    qty = position_value / row['close']
                    
                    pm.open_position(
                        Direction.SHORT, row['close'], qty, atr, ts_4h, ts_4h
                    )
            
            # ========== 闈炵洏涓ā寮? 4H鏀剁洏姝㈡崯妫€鏌?==========
            if not self.use_intrabar_stop and pm.is_open():
                pos = pm.position
                
                if pos.direction == Direction.LONG:
                    if row['low'] <= pos.stop_loss_price:
                        pm.close_position(row['close'], ts_4h, ExitReason.SL)
                else:
                    if row['high'] >= pos.stop_loss_price:
                        pm.close_position(row['close'], ts_4h, ExitReason.SL)
            
            # ========== 璁板綍鏉冪泭 ==========
            unrealized = 0.0
            if pm.is_open():
                pos = pm.position
                if pos.direction == Direction.LONG:
                    unrealized = (row['close'] - pos.entry_price) * pos.current_qty
                else:
                    unrealized = (pos.entry_price - row['close']) * pos.current_qty
            
            equity_history.append({
                'time': ts_4h,
                'equity': pm.equity + unrealized,
                'position': 0 if pm.is_flat() else (1 if pm.position.direction == Direction.LONG else -1)
            })
            
            # 杩涘害鏄剧ず
            if (i + 1) % 500 == 0 or (i + 1) == bar_count:
                print(f"  杩涘害: {i + 1}/{bar_count} | 鏉冪泭: ${pm.equity + unrealized:,.0f} | 浜ゆ槗: {len(pm.trades)}")
        
        final_position = pm.snapshot_position()

        # 鏈熸湯骞充粨
        if close_on_end and pm.is_open():
            last_price = df_4h.iloc[-1]['close']
            last_time = df_4h.index[-1]
            pm.close_position(last_price, last_time, ExitReason.EOD)
        
        # 4. 璁＄畻缁熻
        print("[4/4] 璁＄畻缁熻...")
        trades_df = pd.DataFrame([asdict(t) for t in pm.trades]) if pm.trades else pd.DataFrame()
        equity_df = pd.DataFrame(equity_history).set_index('time') if equity_history else pd.DataFrame()
        
        stats = self._calc_stats(trades_df, equity_df)
        
        return {
            'trades': trades_df,
            'equity': equity_df,
            'stats': stats,
            'signals': df_4h,
            'final_position': final_position,
        }
    
    def _build_mapping(self, df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
        """Build the 4H to 5m index mapping."""
        # 纭繚鏃堕棿鎴冲垪瀛樺湪
        if 'timestamp' in df_5m.columns:
            ts_5m = pd.to_datetime(df_5m['timestamp'], utc=True)
        else:
            ts_5m = df_5m.index
        
        if 'timestamp' in df_4h.columns:
            ts_4h_series = pd.to_datetime(df_4h['timestamp'], utc=True)
        else:
            ts_4h_series = df_4h.index
        
        mapping = {}
        
        for ts_4h in ts_4h_series:
            ts_4h_end = ts_4h + timedelta(hours=4)
            
            # Find all 5m bars that belong to this 4H interval
            mask = (ts_5m >= ts_4h) & (ts_5m < ts_4h_end)
            indices = ts_5m[mask]
            
            if len(indices) > 0:
                mapping[ts_4h] = indices.tolist()
        
        return mapping
    
    def _calc_stats(self, trades_df: pd.DataFrame, equity_df: pd.DataFrame) -> Dict:
        """Calculate backtest summary statistics."""
        if len(equity_df) == 0:
            return {'error': 'No equity data'}
        
        equity_df['dd'] = (equity_df['equity'] / equity_df['equity'].cummax()) - 1.0
        
        final_equity = float(equity_df['equity'].iloc[-1])
        init_equity = self.p.init_equity
        
        # 鏃堕棿璺ㄥ害
        years = (equity_df.index.max() - equity_df.index.min()).total_seconds() / (365.25 * 24 * 3600)
        years = max(years, 1e-6)
        
        # CAGR
        ratio = max(final_equity / init_equity, 1e-12)
        cagr = (ratio ** (1.0 / years)) - 1.0
        
        # Sharpe (4H绾?460鏍?骞?
        ret = equity_df['equity'].pct_change().dropna()
        sharpe = (ret.mean() / (ret.std() + 1e-12)) * np.sqrt(1460)
        
        # 浜ゆ槗缁熻
        n_trades = len(trades_df)
        n_wins = len(trades_df[trades_df['pnl'] > 0]) if n_trades > 0 else 0
        win_rate = n_wins / n_trades * 100 if n_trades > 0 else 0
        
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum() if n_trades > 0 else 0
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum()) if n_trades > 0 else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # 澶氱┖鍒嗙
        long_trades = trades_df[trades_df['direction'] == 'long'] if n_trades > 0 else pd.DataFrame()
        short_trades = trades_df[trades_df['direction'] == 'short'] if n_trades > 0 else pd.DataFrame()
        
        # Exit-reason distribution
        exit_reasons = trades_df["exit_reason"].value_counts().to_dict() if n_trades > 0 else {}
        
        return {
            'FinalEquity': final_equity,
            'TotalReturn_pct': (final_equity / init_equity - 1) * 100,
            'CAGR': cagr,
            'Sharpe': float(sharpe),
            'MaxDD_pct': float(equity_df['dd'].min()),
            'ProfitFactor': profit_factor,
            'Trades': n_trades,
            'WinRate_pct': win_rate,
            'LongTrades': len(long_trades),
            'ShortTrades': len(short_trades),
            'LongPnL': long_trades['pnl'].sum() if len(long_trades) > 0 else 0,
            'ShortPnL': short_trades['pnl'].sum() if len(short_trades) > 0 else 0,
            'GrossProfit': gross_profit,
            'GrossLoss': gross_loss,
            'Years': years,
            'ExitReasons': exit_reasons
        }


# ============================================================
# 7. 涓荤▼搴?# ============================================================

def plot_results(result: Dict, outdir: Path, title: str = ""):
    """Plot the backtest result set."""
    signals = result['signals']
    eq = result['equity']
    trades = result['trades']
    stats = result['stats']
    
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(4, 1, height_ratios=[2.5, 1, 1, 0.5], hspace=0.3)
    
    # 浠锋牸鍥?    ax0 = fig.add_subplot(gs[0, 0])
    ax0.plot(signals.index, signals['close'], label='Close', linewidth=0.8, color='black')
    ax0.plot(signals.index, signals['ema_trend'], label='EMA200', linewidth=0.8, alpha=0.7, color='orange')
    
    # 鏍囪浜ゆ槗
    if len(trades) > 0:
        for _, trade in trades.iterrows():
            color = 'green' if trade['direction'] == 'long' else 'red'
            marker = '^' if trade['direction'] == 'long' else 'v'
            ax0.scatter(trade['entry_time'], trade['entry_price'], 
                       marker=marker, s=30, c=color, zorder=5, alpha=0.7)
    
    ax0.set_title(f"V8.5 Intrabar Backtest {title}")
    ax0.legend(loc='upper left', fontsize=8)
    ax0.grid(True, alpha=0.3)
    
    # 鏉冪泭鏇茬嚎
    ax1 = fig.add_subplot(gs[1, 0])
    ax1.plot(eq.index, eq['equity'], label='Equity', color='blue')
    ax1.axhline(10000, linestyle='--', color='gray', linewidth=0.8)
    ax1.set_title(f"Equity (Final: ${stats['FinalEquity']:,.0f}, Return: {stats['TotalReturn_pct']:.1f}%)")
    ax1.legend(loc='upper left', fontsize=8)
    ax1.grid(True, alpha=0.3)
    
    # 鍥炴挙
    ax2 = fig.add_subplot(gs[2, 0])
    ax2.fill_between(eq.index, eq['dd'] * 100, 0, color='salmon', alpha=0.7)
    ax2.set_title(f"Drawdown (Max: {stats['MaxDD_pct']*100:.1f}%)")
    ax2.grid(True, alpha=0.3)
    
    # 缁熻鏂囧瓧
    ax3 = fig.add_subplot(gs[3, 0])
    ax3.axis('off')
    stats_text = (
        f"CAGR: {stats['CAGR']*100:.1f}% | "
        f"Sharpe: {stats['Sharpe']:.2f} | "
        f"PF: {stats['ProfitFactor']:.2f} | "
        f"Trades: {stats['Trades']} | "
        f"WinRate: {stats['WinRate_pct']:.1f}%"
    )
    ax3.text(0.5, 0.5, stats_text, transform=ax3.transAxes, 
             fontsize=10, ha='center', va='center',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    fig.savefig(outdir / 'backtest_plot.png', dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="V8.5 intrabar backtest runner")
    parser.add_argument("--data_dir", default="./data", help="data directory")
    parser.add_argument("--start", default=None, help="start date YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="end date YYYY-MM-DD")
    parser.add_argument("--no_intrabar", action="store_true", help="disable intrabar stop handling")
    parser.add_argument("--outdir", default=None, help="output directory")
    args = parser.parse_args()

    try:
        from universal_data_updater_5m import DataLoader5m
    except ImportError:
        print("Error: universal_data_updater_5m.py not found")
        return

    print("Loading data...")
    loader = DataLoader5m(args.data_dir)

    try:
        df_5m, df_4h = loader.load_data(args.start, args.end)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        print("Run: python universal_data_updater_5m.py --fetch")
        return

    print(f"5m rows: {len(df_5m)}")
    print(f"4h rows: {len(df_4h)}")

    params = V85Params()
    use_intrabar = not args.no_intrabar
    engine = IntrabarBacktestEngine(params, use_intrabar_stop=use_intrabar)
    result = engine.run(df_5m, df_4h)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "intrabar" if use_intrabar else "4h_only"
    outdir = Path(args.outdir) if args.outdir else Path(args.data_dir) / f"v85_{mode}_{stamp}"
    outdir.mkdir(parents=True, exist_ok=True)

    if not result["trades"].empty:
        result["trades"].to_csv(outdir / "trades.csv", index=False)
    result["equity"].to_csv(outdir / "equity.csv")

    with open(outdir / "stats.json", "w", encoding="utf-8") as f:
        json.dump(
            result["stats"],
            f,
            indent=2,
            default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else str(x),
        )

    try:
        plot_results(result, outdir)
    except Exception as exc:
        print(f"Plot failed: {exc}")

    stats = result["stats"]
    print("\n" + "=" * 70)
    print(f"V8.5 Backtest Result ({'intrabar' if use_intrabar else 'close-only'})")
    print("=" * 70)
    print(f"TotalReturn: {stats['TotalReturn_pct']:.2f}%")
    print(f"CAGR: {stats['CAGR'] * 100:.2f}%")
    print(f"Sharpe: {stats['Sharpe']:.3f}")
    print(f"MaxDD: {stats['MaxDD_pct'] * 100:.2f}%")
    print(f"ProfitFactor: {stats['ProfitFactor']:.3f}")
    print(f"Trades: {stats['Trades']}")
    print(f"WinRate: {stats['WinRate_pct']:.2f}%")
    print(f"LongTrades: {stats['LongTrades']} (${stats['LongPnL']:,.2f})")
    print(f"ShortTrades: {stats['ShortTrades']} (${stats['ShortPnL']:,.2f})")

    if "ExitReasons" in stats:
        print("\nExitReasons:")
        for reason, count in stats["ExitReasons"].items():
            print(f"  {reason}: {count}")

    print("=" * 70)
    print(f"Saved to: {outdir}")


if __name__ == "__main__":
    main()

