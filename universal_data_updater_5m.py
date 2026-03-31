#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
universal_data_updater_5m.py
==========================
OKX BTC-USDT 永续数据获取和重采样系统

功能：
1. 获取 5m 历史数据（支持增量更新）
2. 从 5m 重采样生成 1h / 4h
3. 直接获取 1h / 4h / 1d 历史数据（支持增量更新）
4. 获取 funding rate 历史数据（支持增量更新）
5. 提供统一的数据加载接口（回测使用 5m + 4h_from_5m）

说明：
- 默认使用 OKX REST 接口（/market/history-candles）
- 若 REST 异常，自动回退到 ccxt（若已安装）
"""

import argparse
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Tuple, Dict, Optional, List

import pandas as pd
import requests

try:
    import ccxt
except ImportError:
    ccxt = None


class DataLoader5m:
    """5m 数据加载器和重采样器"""

    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 文件路径
        self.file_5m = self.data_dir / "btc_usdt_swap_5m.csv"
        self.file_1h = self.data_dir / "btc_usdt_swap_1h.csv"
        self.file_4h_original = self.data_dir / "btc_usdt_swap_4h.csv"
        self.file_1d_original = self.data_dir / "btc_usdt_swap_1d.csv"
        self.file_1h_from_5m = self.data_dir / "btc_usdt_swap_1h_from_5m.csv"
        self.file_4h_from_5m = self.data_dir / "btc_usdt_swap_4h_from_5m.csv"
        self.file_funding = self.data_dir / "btc_usdt_swap_funding.csv"

    @staticmethod
    def _init_exchange():
        if ccxt is None:
            return None
        return ccxt.okx(
            {
                "enableRateLimit": True,
                "options": {"defaultType": "swap"},
            }
        )

    @staticmethod
    def _tf_to_ms(timeframe: str) -> int:
        unit = timeframe[-1]
        val = int(timeframe[:-1])
        if unit == "m":
            return val * 60 * 1000
        if unit == "h":
            return val * 60 * 60 * 1000
        if unit == "d":
            return val * 24 * 60 * 60 * 1000
        raise ValueError(f"不支持周期: {timeframe}")

    @staticmethod
    def _tf_to_okx_bar(timeframe: str) -> str:
        mapping = {"5m": "5m", "1h": "1H", "4h": "4H", "1d": "1D"}
        if timeframe not in mapping:
            raise ValueError(f"不支持周期: {timeframe}")
        return mapping[timeframe]

    @staticmethod
    def _symbol_to_inst_id(symbol: str) -> str:
        if symbol == "BTC/USDT:USDT":
            return "BTC-USDT-SWAP"
        return symbol.replace("/", "-").replace(":USDT", "-SWAP")

    def _fetch_ohlcv_range(
        self,
        exchange,
        symbol: str,
        timeframe: str,
        since_ms: int,
        end_ms: int,
        progress_prefix: str,
        sleep_s: float = 0.08,
    ) -> List[List[float]]:
        """按时间范围抓取OHLCV（REST优先，ccxt兜底）"""
        rest_rows, rest_ok = self._fetch_ohlcv_range_rest(
            symbol=symbol,
            timeframe=timeframe,
            since_ms=since_ms,
            end_ms=end_ms,
            progress_prefix=progress_prefix,
            sleep_s=sleep_s,
        )
        if rest_ok:
            return rest_rows

        if exchange is None:
            print("[ERROR] REST失败且未安装ccxt，无法继续取数")
            return []

        print(f"[WARN] REST失败，回退 ccxt 抓取 {timeframe}")
        return self._fetch_ohlcv_range_ccxt(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            since_ms=since_ms,
            end_ms=end_ms,
            progress_prefix=progress_prefix,
            sleep_s=sleep_s,
        )

    def _fetch_ohlcv_range_rest(
        self,
        symbol: str,
        timeframe: str,
        since_ms: int,
        end_ms: int,
        progress_prefix: str,
        sleep_s: float = 0.08,
    ) -> Tuple[List[List[float]], bool]:
        """使用 OKX REST /market/history-candles 抓取，绕过 ccxt 的 SPOT 市场加载依赖。"""
        endpoint = "https://www.okx.com/api/v5/market/history-candles"
        inst_id = self._symbol_to_inst_id(symbol)
        bar = self._tf_to_okx_bar(timeframe)

        rows: List[List[float]] = []
        seen_ts = set()
        cursor_after: Optional[int] = None
        last_cursor: Optional[int] = None

        consecutive_failures = 0
        max_consecutive_failures = 20
        any_success_call = False

        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            }
        )

        while True:
            params = {"instId": inst_id, "bar": bar, "limit": "100"}
            if cursor_after is not None:
                params["after"] = str(cursor_after)

            try:
                r = session.get(endpoint, params=params, timeout=20)
                r.raise_for_status()
                payload = r.json()
                if payload.get("code") != "0":
                    raise RuntimeError(f"okx返回异常: {payload.get('code')} {payload.get('msg')}")

                data = payload.get("data", [])
                any_success_call = True

                if not data:
                    break

                # OKX 返回倒序时间，row[0]=ts(ms)
                ts_list = [int(item[0]) for item in data]
                min_ts = min(ts_list)

                for item in data:
                    ts = int(item[0])
                    if ts >= end_ms:
                        continue
                    if ts < since_ms:
                        continue
                    if ts in seen_ts:
                        continue
                    seen_ts.add(ts)
                    rows.append(
                        [
                            ts,
                            float(item[1]),
                            float(item[2]),
                            float(item[3]),
                            float(item[4]),
                            float(item[5]),
                        ]
                    )

                print(f"\r{progress_prefix}(REST): {len(rows)} 根{timeframe} K线", end="", flush=True)
                consecutive_failures = 0

                if min_ts < since_ms:
                    break

                last_cursor, cursor_after = cursor_after, min_ts
                if last_cursor is not None and cursor_after >= last_cursor:
                    # 防止游标异常导致死循环
                    break

                time.sleep(sleep_s)
            except Exception as e:
                consecutive_failures += 1
                print(f"\nREST获取失败({consecutive_failures}/{max_consecutive_failures}): {e}")
                if consecutive_failures >= max_consecutive_failures:
                    print(f"REST连续失败达到上限，停止获取 {timeframe}")
                    return [], False
                time.sleep(1)

        print()
        rows.sort(key=lambda x: x[0])
        return rows, any_success_call

    def _fetch_ohlcv_range_ccxt(
        self,
        exchange,
        symbol: str,
        timeframe: str,
        since_ms: int,
        end_ms: int,
        progress_prefix: str,
        sleep_s: float = 0.08,
    ) -> List[List[float]]:
        """按时间范围抓取OHLCV（OKX limit=500）"""
        tf_ms = self._tf_to_ms(timeframe)
        batch_size = 500

        all_rows: List[List[float]] = []
        current_ms = since_ms

        consecutive_failures = 0
        max_consecutive_failures = 20

        while current_ms < end_ms:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_ms, limit=batch_size)
                if not ohlcv:
                    break

                # 丢弃尚未收线或越界数据
                chunk = [row for row in ohlcv if row[0] < end_ms]
                if not chunk:
                    break

                all_rows.extend(chunk)
                last_ts = chunk[-1][0]
                if last_ts <= current_ms:
                    break

                current_ms = last_ts + tf_ms
                consecutive_failures = 0
                print(f"\r{progress_prefix}(ccxt): {len(all_rows)} 根{timeframe} K线", end="", flush=True)
                time.sleep(sleep_s)
            except Exception as e:
                consecutive_failures += 1
                print(f"\nccxt获取失败({consecutive_failures}/{max_consecutive_failures}): {e}")
                if consecutive_failures >= max_consecutive_failures:
                    print(f"ccxt连续失败达到上限，停止获取 {timeframe}")
                    break
                time.sleep(1)

        print()
        return all_rows

    @staticmethod
    def _rows_to_df(rows: List[List[float]]) -> pd.DataFrame:
        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
        return df

    def _load_existing_df(self, csv_file: Path) -> pd.DataFrame:
        df = pd.read_csv(csv_file)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)

    def _incremental_fetch_to_file(
        self,
        csv_file: Path,
        timeframe: str,
        symbol: str = "BTC/USDT:USDT",
        start_date_if_empty: str = "2019-12-16",
        force: bool = False,
    ) -> pd.DataFrame:
        """通用增量抓取并保存到指定文件"""
        exchange = self._init_exchange()
        now = datetime.now(timezone.utc)
        end_ms = int(now.timestamp() * 1000)
        tf_ms = self._tf_to_ms(timeframe)

        if csv_file.exists() and not force:
            existing = self._load_existing_df(csv_file)
            last_ts = existing["timestamp"].max()
            start_ms = int(last_ts.timestamp() * 1000) + tf_ms

            print(f"发现现有 {timeframe} 数据: {csv_file}")
            print(f"现有范围: {existing['timestamp'].min()} -> {existing['timestamp'].max()}")

            # 如果距离当前不足一个周期，判定最新
            if start_ms >= end_ms - tf_ms:
                print(f"{timeframe} 数据已是最新")
                return existing

            rows = self._fetch_ohlcv_range(
                exchange,
                symbol,
                timeframe,
                start_ms,
                end_ms,
                progress_prefix=f"增量获取 {timeframe}",
            )

            if not rows:
                print(f"{timeframe} 无新增数据")
                return existing

            new_df = self._rows_to_df(rows)
            merged = (
                pd.concat([existing, new_df], ignore_index=True)
                .drop_duplicates(subset="timestamp")
                .sort_values("timestamp")
                .reset_index(drop=True)
            )
            merged.to_csv(csv_file, index=False)
            print(f"{timeframe} 增量更新完成: 新增 {len(merged) - len(existing)} 根")
            print(f"最新时间: {merged['timestamp'].max()}")
            return merged

        # 全量抓取
        start_dt = datetime.strptime(start_date_if_empty, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        start_ms = int(start_dt.timestamp() * 1000)

        print(f"开始获取 {timeframe} 数据...")
        print(f"时间范围: {start_dt.date()} -> {now.date()}")

        rows = self._fetch_ohlcv_range(
            exchange,
            symbol,
            timeframe,
            start_ms,
            end_ms,
            progress_prefix=f"已获取 {timeframe}",
        )

        if not rows:
            raise ValueError(f"未获取到 {timeframe} 数据")

        df = self._rows_to_df(rows)
        df.to_csv(csv_file, index=False)
        print(f"{timeframe} 数据已保存: {csv_file}")
        return df

    def fetch_5m_data(self, start_date: str = "2019-12-16", force: bool = False) -> pd.DataFrame:
        """获取 5m 数据（支持增量更新）"""
        df = self._incremental_fetch_to_file(
            csv_file=self.file_5m,
            timeframe="5m",
            start_date_if_empty=start_date,
            force=force,
        )
        self._validate_5m_alignment(df)
        return df

    def fetch_direct_timeframe_data(self, timeframe: str, start_date: str = "2019-12-16", force: bool = False) -> pd.DataFrame:
        """直接从OKX抓取 1h / 4h / 1d"""
        if timeframe == "1h":
            target = self.file_1h
        elif timeframe == "4h":
            target = self.file_4h_original
        elif timeframe == "1d":
            target = self.file_1d_original
        else:
            raise ValueError("只支持 1h / 4h / 1d")

        df = self._incremental_fetch_to_file(
            csv_file=target,
            timeframe=timeframe,
            start_date_if_empty=start_date,
            force=force,
        )

        if timeframe == "1h":
            self._validate_1h_alignment(df)
        elif timeframe == "4h":
            self._validate_4h_alignment(df)
        else:
            self._validate_1d_alignment(df)
        return df

    def _validate_1d_alignment(self, df_1d: pd.DataFrame):
        """验证1d时间戳对齐"""
        print("验证1d时间戳对齐...")

        if len(df_1d) > 1:
            time_diffs = (df_1d["timestamp"].diff().dt.total_seconds() / 86400).dropna()
            non_standard = time_diffs[time_diffs != 1]
            if len(non_standard) > 0:
                print(f"发现 {len(non_standard)} 个非标准时间间隔")
                print(f"  范围: {non_standard.min()} - {non_standard.max()} 天")
            else:
                print("1d时间戳对齐正确")

        hours = set(df_1d["timestamp"].dt.hour.unique())
        expected_hours = {0, 16}
        if not hours.issubset(expected_hours):
            print(f"发现非标准小时: {hours - expected_hours}")
        else:
            print("1d小时对齐正确")

    def fetch_funding_rate_history(
        self,
        symbol: str = "BTC/USDT:USDT",
        start_date_if_empty: str = "2019-12-16",
        force: bool = False,
    ) -> pd.DataFrame:
        endpoint = "https://www.okx.com/api/v5/public/funding-rate-history"
        inst_id = self._symbol_to_inst_id(symbol)
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            }
        )
        rows = []
        seen = set()

        if self.file_funding.exists() and not force:
            existing = pd.read_csv(self.file_funding)
            existing["fundingTime"] = pd.to_datetime(existing["fundingTime"], utc=True)
            after_ms = int(existing["fundingTime"].max().timestamp() * 1000)
            rows.extend(existing.to_dict("records"))
            for item in rows:
                seen.add(str(item["fundingTime"]))
        else:
            start_dt = datetime.strptime(start_date_if_empty, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            after_ms = int(start_dt.timestamp() * 1000)

        cursor_after = after_ms
        consecutive_failures = 0
        max_consecutive_failures = 20
        while True:
            params = {"instId": inst_id, "after": str(cursor_after), "limit": "100"}
            try:
                r = session.get(endpoint, params=params, timeout=20)
                r.raise_for_status()
                payload = r.json()
                if payload.get("code") != "0":
                    raise RuntimeError(f"okx返回异常: {payload.get('code')} {payload.get('msg')}")
                data = payload.get("data", [])
                if not data:
                    break
                max_ts = cursor_after
                for item in data:
                    ts = pd.to_datetime(int(item["fundingTime"]), unit="ms", utc=True)
                    key = str(ts)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(
                        {
                            "fundingTime": ts,
                            "fundingRate": float(item["fundingRate"]),
                            "realizedRate": float(item.get("realizedRate", item["fundingRate"])),
                        }
                    )
                    max_ts = max(max_ts, int(item["fundingTime"]))
                print(f"\rfunding增量获取: {len(rows)} 条", end="", flush=True)
                if max_ts <= cursor_after:
                    break
                cursor_after = max_ts
                consecutive_failures = 0
                time.sleep(0.08)
            except Exception as e:
                consecutive_failures += 1
                print(f"\nfunding获取失败({consecutive_failures}/{max_consecutive_failures}): {e}")
                if consecutive_failures >= max_consecutive_failures:
                    raise
                time.sleep(1)
        print()
        out = pd.DataFrame(rows)
        if out.empty:
            return pd.DataFrame(columns=["fundingTime", "fundingRate", "realizedRate"])
        out = out.sort_values("fundingTime").drop_duplicates(subset="fundingTime").reset_index(drop=True)
        out.to_csv(self.file_funding, index=False)
        return out

    def _validate_5m_alignment(self, df: pd.DataFrame):
        """验证5m时间戳对齐"""
        print("验证5m时间戳对齐...")

        if len(df) > 1:
            time_diffs = (df["timestamp"].diff().dt.total_seconds() / 60).dropna()
            non_standard = time_diffs[time_diffs != 5]
            if len(non_standard) > 0:
                print(f"发现 {len(non_standard)} 个非标准时间间隔")
                print(f"  范围: {non_standard.min()} - {non_standard.max()} 分钟")
            else:
                print("[OK] 时间戳对齐正确")

        minutes = set(df["timestamp"].dt.minute.unique())
        expected_minutes = set(range(0, 60, 5))
        if not minutes.issubset(expected_minutes):
            print(f"[WARN] 发现非标准分钟: {minutes - expected_minutes}")
        else:
            print("[OK] 分钟对齐正确")

    def _validate_1h_alignment(self, df_1h: pd.DataFrame):
        """验证1h时间戳对齐"""
        print("验证1h时间戳对齐...")

        if len(df_1h) > 1:
            time_diffs = (df_1h["timestamp"].diff().dt.total_seconds() / 3600).dropna()
            non_standard = time_diffs[time_diffs != 1]
            if len(non_standard) > 0:
                print(f"发现 {len(non_standard)} 个非标准时间间隔")
                print(f"  范围: {non_standard.min()} - {non_standard.max()} 小时")
            else:
                print("1h时间戳对齐正确")

        minutes = set(df_1h["timestamp"].dt.minute.unique())
        if minutes != {0}:
            print(f"发现非标准分钟: {minutes - {0}}")
        else:
            print("1h分钟对齐正确")

    def _validate_4h_alignment(self, df_4h: pd.DataFrame):
        """验证4h时间戳对齐"""
        print("验证4h时间戳对齐...")

        if len(df_4h) > 1:
            time_diffs = (df_4h["timestamp"].diff().dt.total_seconds() / 3600).dropna()
            non_standard = time_diffs[time_diffs != 4]
            if len(non_standard) > 0:
                print(f"发现 {len(non_standard)} 个非标准时间间隔")
                print(f"  范围: {non_standard.min()} - {non_standard.max()} 小时")
            else:
                print("4h时间戳对齐正确")

        hours = set(df_4h["timestamp"].dt.hour.unique())
        expected_hours = {0, 4, 8, 12, 16, 20}
        if not hours.issubset(expected_hours):
            print(f"发现非标准小时: {hours - expected_hours}")
        else:
            print("4h小时对齐正确")

    def _resample_from_5m(self, df_5m: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """将 5m 重采样到 1h/4h"""
        if timeframe not in {"1h", "4h"}:
            raise ValueError(f"不支持的重采样周期: {timeframe}")

        print(f"重采样 5m -> {timeframe}...")

        df = df_5m.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            df = df.set_index("timestamp")

        df = df.sort_index()
        group_col = f"{timeframe}_group"
        df[group_col] = df.index.floor(timeframe)

        out = (
            df.groupby(group_col)
            .agg(
                {
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }
            )
            .reset_index()
            .rename(columns={group_col: "timestamp"})
        )

        if timeframe == "1h":
            self._validate_1h_alignment(out)
            out.to_csv(self.file_1h_from_5m, index=False)
            print(f"重采样1h数据已保存: {self.file_1h_from_5m}")
        else:
            self._validate_4h_alignment(out)
            out.to_csv(self.file_4h_from_5m, index=False)
            print(f"重采样4h数据已保存: {self.file_4h_from_5m}")

        return out

    def resample_to_1h(self, df_5m: pd.DataFrame) -> pd.DataFrame:
        return self._resample_from_5m(df_5m, "1h")

    def resample_to_4h(self, df_5m: pd.DataFrame) -> pd.DataFrame:
        return self._resample_from_5m(df_5m, "4h")

    def compare_with_original_4h(self, df_4h_from_5m: pd.DataFrame) -> Optional[pd.DataFrame]:
        """与原始4h数据对比"""
        if not self.file_4h_original.exists():
            print("未找到原始4h数据进行对比")
            return None

        print("与原始4h数据对比...")

        df_orig = pd.read_csv(self.file_4h_original)
        df_orig["timestamp"] = pd.to_datetime(df_orig["timestamp"], utc=True)

        df_orig = df_orig.sort_values("timestamp").reset_index(drop=True)
        df_resamp = df_4h_from_5m.sort_values("timestamp").reset_index(drop=True)

        comparison = pd.merge(df_orig, df_resamp, on="timestamp", suffixes=("_orig", "_resamp"))

        if len(comparison) == 0:
            print("[ERROR] 时间戳完全不匹配")
            return None

        for col in ["open", "high", "low", "close"]:
            diff_col = f"{col}_diff"
            comparison[diff_col] = comparison[f"{col}_orig"] - comparison[f"{col}_resamp"]

        exact_matches = (
            (comparison["open_diff"].abs() < 1e-6)
            & (comparison["high_diff"].abs() < 1e-6)
            & (comparison["low_diff"].abs() < 1e-6)
            & (comparison["close_diff"].abs() < 1e-6)
        ).sum()

        print("数据对比结果:")
        print(f"  原始K线数: {len(df_orig)}")
        print(f"  重采样K线数: {len(df_resamp)}")
        print(f"  时间戳匹配: {len(comparison)}")
        print(f"  价格完全匹配: {exact_matches}/{len(comparison)} ({exact_matches / len(comparison) * 100:.1f}%)")

        for col in ["open", "high", "low", "close"]:
            diff_col = f"{col}_diff"
            abs_diff = comparison[diff_col].abs()
            non_zero = (abs_diff > 1e-6).sum()
            if non_zero > 0:
                print(f"  {col}: 最大差异={abs_diff.max():.6f}, 平均差异={abs_diff.mean():.6f}, 非零差异={non_zero}")

        return comparison

    def load_data(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
        tf_signal: str = "4h",
        tf_risk: str = "5m",
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """统一数据加载接口（回测使用 5m + 4h_from_5m）"""
        if not self.file_5m.exists():
            raise FileNotFoundError(f"未找到5m数据文件: {self.file_5m}")
        if not self.file_4h_from_5m.exists():
            raise FileNotFoundError(f"未找到重采样4h数据文件: {self.file_4h_from_5m}")

        df_5m = pd.read_csv(self.file_5m)
        df_4h = pd.read_csv(self.file_4h_from_5m)

        df_5m["timestamp"] = pd.to_datetime(df_5m["timestamp"], utc=True)
        df_4h["timestamp"] = pd.to_datetime(df_4h["timestamp"], utc=True)

        if start:
            start_dt = pd.to_datetime(start, utc=True)
            df_5m = df_5m[df_5m["timestamp"] >= start_dt]
            df_4h = df_4h[df_4h["timestamp"] >= start_dt]

        if end:
            end_dt = pd.to_datetime(end, utc=True)
            df_5m = df_5m[df_5m["timestamp"] <= end_dt]
            df_4h = df_4h[df_4h["timestamp"] <= end_dt]

        df_5m = df_5m.reset_index(drop=True)
        df_4h = df_4h.reset_index(drop=True)

        print("数据加载完成:")
        print(f"  {tf_risk}: {len(df_5m)} 根K线, 时间范围: {df_5m['timestamp'].min()} -> {df_5m['timestamp'].max()}")
        print(f"  {tf_signal}: {len(df_4h)} 根K线, 时间范围: {df_4h['timestamp'].min()} -> {df_4h['timestamp'].max()}")

        return df_5m, df_4h

    def build_4h_to_5m_mapping(self, df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict[pd.Timestamp, pd.Index]:
        """建立4h到5m的索引映射"""
        df_5m_indexed = df_5m.set_index("timestamp").sort_index()
        df_4h_indexed = df_4h.set_index("timestamp").sort_index()

        mapping = {}
        for ts_4h in df_4h_indexed.index:
            ts_4h_end = ts_4h + timedelta(hours=4)
            mask = (df_5m_indexed.index >= ts_4h) & (df_5m_indexed.index < ts_4h_end)
            mapping[ts_4h] = df_5m_indexed.index[mask]

        return mapping


def main():
    parser = argparse.ArgumentParser(description="OKX 数据获取和重采样")
    parser.add_argument("--fetch", action="store_true", help="获取/增量更新 5m 数据")
    parser.add_argument("--resample", action="store_true", help="重采样 5m 到 1h/4h")
    parser.add_argument("--compare", action="store_true", help="对比 4h 直连数据与重采样4h")
    parser.add_argument("--fetch_direct_tf", action="store_true", help="同时增量更新直连 1h/4h")
    parser.add_argument("--start", default="2019-12-16", help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="强制全量重新获取")
    parser.add_argument("--outdir", default="./data", help="输出目录")
    args = parser.parse_args()

    loader = DataLoader5m(args.outdir)

    if args.fetch:
        df_5m = loader.fetch_5m_data(args.start, args.force)

        # 默认自动重采样
        df_1h = loader.resample_to_1h(df_5m)
        df_4h = loader.resample_to_4h(df_5m)

        if args.fetch_direct_tf:
            loader.fetch_direct_timeframe_data("1h", args.start, args.force)
            loader.fetch_direct_timeframe_data("4h", args.start, args.force)
            loader.fetch_direct_timeframe_data("1d", args.start, args.force)
            loader.fetch_funding_rate_history(start_date_if_empty=args.start, force=args.force)

        if args.compare:
            loader.compare_with_original_4h(df_4h)

    elif args.resample:
        if not loader.file_5m.exists():
            print("[ERROR] 未找到5m数据，请先使用 --fetch 获取")
            return
        df_5m = pd.read_csv(loader.file_5m)
        df_1h = loader.resample_to_1h(df_5m)
        df_4h = loader.resample_to_4h(df_5m)
        if args.compare:
            loader.compare_with_original_4h(df_4h)

    elif args.compare:
        if not loader.file_4h_from_5m.exists():
            print("[ERROR] 未找到重采样4h数据，请先使用 --resample")
            return
        df_4h = pd.read_csv(loader.file_4h_from_5m)
        loader.compare_with_original_4h(df_4h)

    else:
        # 默认完整流程
        print("执行完整数据流程...")
        df_5m = loader.fetch_5m_data(args.start, args.force)
        df_1h = loader.resample_to_1h(df_5m)
        df_4h = loader.resample_to_4h(df_5m)
        loader.fetch_direct_timeframe_data("1h", args.start, args.force)
        loader.fetch_direct_timeframe_data("4h", args.start, args.force)
        loader.fetch_direct_timeframe_data("1d", args.start, args.force)
        loader.fetch_funding_rate_history(start_date_if_empty=args.start, force=args.force)
        loader.compare_with_original_4h(df_4h)

        print("\n测试数据加载接口...")
        loader.load_data()
        print("数据加载接口测试成功")


if __name__ == "__main__":
    main()
