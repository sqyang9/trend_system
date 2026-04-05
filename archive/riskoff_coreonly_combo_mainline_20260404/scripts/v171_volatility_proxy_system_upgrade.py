#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Volatility-proxy system upgrade screen for P0/P1 defect research."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig_system_defect_research")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_addon_grading_study import current_research_optimal as formal_current_research_optimal
from v90_asset_management_system_aligned import compute_metrics, current_research_optimal as riskoff_current_research_optimal, simulate_core
from v90_riskoff_promotion_v2 import build_indicator_cache
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v92_const1x_deployment_audit import loss_cluster_diagnostics, path_diagnostics
from v95_range_rotation_mean_reversion_audit import make_range_rotation_params
from v96_range_rotation_mean_reversion_s3_audit import scenario_systems
from v121_coreonly_riskoff_sellside_ema_audit import build_indicators as build_core_indicators
from v121_coreonly_riskoff_sellside_ema_audit import build_instability_flags, build_target
from v123_formal_launch_and_layer2_weight_audit import ADOPTED_SPEC, SCENARIOS


OUT_DIR = Path("system_defect_research")
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_MD = OUT_DIR / "VOLATILITY_PROXY_SYSTEM_UPGRADE.md"
SUMMARY_CSV = OUT_DIR / "volatility_proxy_system_upgrade_summary.csv"
WINDOWS_CSV = OUT_DIR / "volatility_proxy_system_upgrade_windows.csv"
BACKGROUND_CSV = OUT_DIR / "volatility_proxy_background_data.csv"
SUMMARY_JSON = OUT_DIR / "volatility_proxy_system_upgrade_summary.json"

W06_START = pd.Timestamp("2022-06-16 04:00:00", tz="UTC")
W06_END = pd.Timestamp("2022-12-16 00:00:00", tz="UTC")
W11_START = pd.Timestamp("2024-12-16 04:00:00", tz="UTC")
W11_END = pd.Timestamp("2025-06-16 00:00:00", tz="UTC")

ATR_LEN = 14
HV_LOOKBACK_BARS = 14 * 6
PCTL_LOOKBACK_BARS = 180 * 6
ATR_SCALE_MIN = 0.35
ATR_SCALE_MAX = 1.50
INIT_EQUITY = 10000.0


@dataclass(frozen=True)
class Candidate:
    key: str
    label: str
    atrvt_s1: bool
    atrvt_s2: bool
    hv_force_hc_threshold: float | None


GRID: List[Candidate] = [
    Candidate("baseline", "Current mainline", False, False, None),
    Candidate("p0_atrvt_s2", "P0: ATR vol-targeting on S2", False, True, None),
    Candidate("p0_atrvt_all", "P0: ATR vol-targeting on S1+S2", True, True, None),
    Candidate("p1_hv85_coregate", "P1: HV pct >= 85 -> force HC gate", False, False, 0.85),
    Candidate("p1_hv90_coregate", "P1: HV pct >= 90 -> force HC gate", False, False, 0.90),
    Candidate("combo_s2_hv85", "Combo: S2 ATR VT + HV85 core gate", False, True, 0.85),
    Candidate("combo_all_hv85", "Combo: S1+S2 ATR VT + HV85 core gate", True, True, 0.85),
]


def compute_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


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


def build_background(df_4h: pd.DataFrame) -> pd.DataFrame:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    atr = compute_atr(d4.reset_index(), ATR_LEN).reindex(d4.index)
    atr_pct = (atr / d4["close"].astype(float)).replace([np.inf, -np.inf], np.nan)
    atr_target_pct = atr_pct.rolling(PCTL_LOOKBACK_BARS, min_periods=120).median().shift(1)
    atr_scale = (atr_target_pct / atr_pct).clip(lower=ATR_SCALE_MIN, upper=ATR_SCALE_MAX)
    atr_scale = atr_scale.replace([np.inf, -np.inf], np.nan).fillna(1.0)

    log_ret = np.log(d4["close"].astype(float) / d4["close"].astype(float).shift(1))
    hv_ann = log_ret.rolling(HV_LOOKBACK_BARS, min_periods=30).std() * np.sqrt(6.0 * 365.0)
    hv_pct_180d = rolling_last_percentile(hv_ann, PCTL_LOOKBACK_BARS)

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


def _strict_ema50_ok(row: pd.Series) -> bool:
    return bool(pd.notna(row["ema50"]) and pd.notna(row["ema50_slope"]) and row["ema50"] > row["ema"] and row["ema50_slope"] > 0)


def build_target_and_events(indicators: pd.DataFrame, env_state: pd.Series, breakout_window: int) -> tuple[pd.Series, pd.DataFrame]:
    bearish = (indicators["close"] < indicators["ema"]) & (indicators["ema_slope"] < 0)
    close_confirm = indicators["close"] > indicators["ema"]
    weekly_trigger = (indicators["weekly_rsi_14"] <= 30.0).fillna(False)
    env = env_state.reindex(indicators.index).ffill().fillna("stable")

    rows: list[float] = []
    events: list[dict] = []
    state = "normal"
    bear_count = 0
    close_count = 0
    qual_bars = 0
    armed_trigger_high = np.nan

    for ts, row in indicators.iterrows():
        is_bear = bool(bearish.loc[ts]) if pd.notna(bearish.loc[ts]) else False
        is_close = bool(close_confirm.loc[ts]) if pd.notna(close_confirm.loc[ts]) else False
        trig = bool(weekly_trigger.loc[ts])
        current_env = str(env.loc[ts])
        prev_state = state
        event = ""
        reentry_path = ""

        bear_count = bear_count + 1 if is_bear else 0
        close_count = close_count + 1 if is_close else 0

        if state == "normal":
            if bear_count >= 2:
                state = "flat"
                event = "FLAT"
            elif bear_count == 1:
                state = "soft_off"
        elif state == "soft_off":
            if bear_count >= 2:
                state = "flat"
                event = "FLAT"
            elif bear_count == 0:
                state = "normal"
        elif state == "flat":
            if close_count >= 3:
                if current_env != "highly_unstable":
                    state = "normal"
                    event = "RE"
                    reentry_path = "stable_close3"
                    bear_count = 0
                    close_count = 0
                elif _strict_ema50_ok(row):
                    state = "armed"
                    event = "QUALIFY"
                    reentry_path = f"high_churn_breakout{breakout_window}"
                    qual_bars = 0
                    armed_trigger_high = float(row["high"])
                    bear_count = 0
                    close_count = 0
            elif trig:
                state = "override_hold"
                event = "RE"
                reentry_path = "weekly_rsi30_hold"
                bear_count = 0
                close_count = 0
        elif state == "armed":
            qual_bars += 1
            if trig:
                state = "override_hold"
                event = "RE"
                reentry_path = "weekly_rsi30_hold"
                qual_bars = 0
                armed_trigger_high = np.nan
                bear_count = 0
                close_count = 0
            elif bear_count >= 2 or qual_bars >= breakout_window:
                state = "flat"
                event = "QUALIFY_FAIL"
                qual_bars = 0
                armed_trigger_high = np.nan
                bear_count = 0
                close_count = 0
            elif pd.notna(armed_trigger_high) and float(row["close"]) > float(armed_trigger_high):
                state = "normal"
                event = "RE"
                reentry_path = f"high_churn_strict_breakout{breakout_window}"
                qual_bars = 0
                armed_trigger_high = np.nan
                bear_count = 0
                close_count = 0
        elif state == "override_hold":
            if close_count >= 3:
                state = "normal"

        weight = 1.0 if state in {"normal", "override_hold"} else 0.5 if state == "soft_off" else 0.0
        rows.append(weight)
        if event:
            events.append(
                {
                    "timestamp": ts,
                    "event": event,
                    "from_state": prev_state,
                    "to_state": state,
                    "reentry_path": reentry_path,
                    "instability_state": current_env,
                }
            )
    target = pd.Series(rows, index=indicators.index, dtype=float)
    events_df = pd.DataFrame(events)
    if not events_df.empty:
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], utc=True)
    return target, events_df


def build_cycles(events: pd.DataFrame, candidate_key: str) -> pd.DataFrame:
    cols = [
        "candidate",
        "flat_time",
        "re_time",
        "reentry_path",
        "instability_state",
        "days_re_to_next_flat",
        "quick_reflat_after_re_14d",
        "quick_reflat_after_re_30d",
    ]
    if events.empty:
        return pd.DataFrame(columns=cols)
    flats = events[events["event"] == "FLAT"].sort_values("timestamp").reset_index(drop=True)
    res = events[events["event"] == "RE"].sort_values("timestamp").reset_index(drop=True)
    rows = []
    for _, flat in flats.iterrows():
        later_re = res[res["timestamp"] > flat["timestamp"]]
        if later_re.empty:
            continue
        re = later_re.iloc[0]
        later_flat = flats[flats["timestamp"] > re["timestamp"]]
        next_flat = later_flat.iloc[0] if not later_flat.empty else None
        days = float((next_flat["timestamp"] - re["timestamp"]).total_seconds() / 86400.0) if next_flat is not None else np.nan
        rows.append(
            {
                "candidate": candidate_key,
                "flat_time": flat["timestamp"],
                "re_time": re["timestamp"],
                "reentry_path": re["reentry_path"],
                "instability_state": re["instability_state"],
                "days_re_to_next_flat": days,
                "quick_reflat_after_re_14d": bool(pd.notna(days) and days <= 14.0),
                "quick_reflat_after_re_30d": bool(pd.notna(days) and days <= 30.0),
            }
        )
    return pd.DataFrame(rows, columns=cols)


def path_bundle(equity: pd.Series) -> dict:
    pdx = path_diagnostics(equity)
    clusters = loss_cluster_diagnostics(equity)
    maxdd_episode = pdx["worst_underwater_episodes"][0] if pdx["worst_underwater_episodes"] else None
    return {
        "worst_3m_cluster_return_pct": float(clusters["worst_3m_cluster_return_pct"]),
        "worst_6m_cluster_return_pct": float(clusters["worst_6m_cluster_return_pct"]),
        "recovery_days_from_maxdd": float(maxdd_episode["recovery_days_from_trough"]) if maxdd_episode is not None else 0.0,
    }


def scale_sleeve(equity: pd.Series, weight: pd.Series, scale: pd.Series) -> tuple[pd.Series, pd.Series]:
    eq = equity.astype(float).copy()
    wt = weight.astype(float).reindex(eq.index).ffill().fillna(0.0)
    scl = scale.reindex(eq.index).ffill().fillna(1.0).clip(lower=ATR_SCALE_MIN, upper=ATR_SCALE_MAX)
    ret = eq.pct_change().fillna(0.0)
    eff = scl.shift(1).fillna(1.0)
    eff = eff.where(wt.shift(1).fillna(0.0) > 1e-9, 0.0)

    scaled = pd.Series(index=eq.index, dtype=float)
    scaled.iloc[0] = INIT_EQUITY
    for i in range(1, len(eq)):
        scaled.iloc[i] = scaled.iloc[i - 1] * (1.0 + ret.iloc[i] * eff.iloc[i])
    scaled_weight = (wt * scl).astype(float)
    return scaled.astype(float), scaled_weight


def build_formal_bundle(df_5m: pd.DataFrame, df_4h: pd.DataFrame, formal_overrides: Dict) -> dict:
    formal_params = formal_current_research_optimal(**formal_overrides)
    range_params = make_range_rotation_params(**formal_overrides)
    payload = scenario_systems(formal_params, range_params, df_5m, df_4h)
    systems = payload["systems"]
    const1x = systems["Core+ConstAddOn[1.00x]"]
    candidate_sleeve = payload["candidate_sleeve"]
    idx = const1x["combo_equity"].index
    return {
        "index": idx,
        "s1_equity": const1x["sleeve"]["equity"].reindex(idx).ffill().bfill().astype(float),
        "s1_weight": const1x["sleeve"]["weight"].reindex(idx).fillna(0.0).astype(float),
        "s2_equity": candidate_sleeve["equity"].reindex(idx).ffill().bfill().astype(float),
        "s2_weight": candidate_sleeve["weight"].reindex(idx).fillna(0.0).astype(float),
    }


def evaluate_combo(bundle: dict, core_sim: dict, s1_equity: pd.Series, s1_weight: pd.Series, s2_equity: pd.Series, s2_weight: pd.Series) -> dict:
    idx = bundle["index"]
    core_equity = core_sim["equity"]["equity"].reindex(idx).ffill().bfill().astype(float)
    core_exposure = core_sim["equity"]["exposure"].reindex(idx).ffill().bfill().astype(float)
    combo_equity = (core_equity + (s1_equity.reindex(idx).ffill().bfill() - INIT_EQUITY) + (s2_equity.reindex(idx).ffill().bfill() - INIT_EQUITY)).astype(float)
    combo_exposure = (core_exposure + s1_weight.reindex(idx).ffill().fillna(0.0) + s2_weight.reindex(idx).ffill().fillna(0.0)).astype(float)
    metrics = extended_metrics({"combo_equity": combo_equity, "combo_metrics": compute_metrics(combo_equity, combo_exposure)})
    return {
        "combo_equity": combo_equity,
        "combo_exposure": combo_exposure,
        "core_exposure": core_exposure,
        "s1_exposure": s1_weight.reindex(idx).ffill().fillna(0.0).astype(float),
        "s2_exposure": s2_weight.reindex(idx).ffill().fillna(0.0).astype(float),
        "metrics": metrics,
        "path": path_bundle(combo_equity),
    }


def w06_metrics(bundle: dict) -> dict:
    mask = (bundle["combo_equity"].index >= W06_START) & (bundle["combo_equity"].index <= W06_END)
    equity = bundle["combo_equity"].loc[mask].astype(float)
    exposure = bundle["combo_exposure"].loc[mask].astype(float)
    s2_exposure = bundle["s2_exposure"].loc[mask].astype(float)
    if len(equity) < 2:
        return {
            "w06_return_pct": 0.0,
            "w06_maxdd_pct": 0.0,
            "w06_avg_total_exposure": 0.0,
            "w06_avg_s2_exposure": 0.0,
            "w06_dd_over_avg_exposure_pct": 0.0,
        }
    maxdd_pct = float((equity / equity.cummax() - 1.0).min() * 100.0)
    avg_exp = float(exposure.mean())
    return {
        "w06_return_pct": float(equity.iloc[-1] / equity.iloc[0] - 1.0) * 100.0,
        "w06_maxdd_pct": maxdd_pct,
        "w06_avg_total_exposure": avg_exp,
        "w06_avg_s2_exposure": float(s2_exposure.mean()),
        "w06_dd_over_avg_exposure_pct": float(maxdd_pct / avg_exp) if avg_exp > 1e-9 else 0.0,
    }


def w11_metrics(bundle: dict, cycles: pd.DataFrame) -> dict:
    mask = (bundle["combo_equity"].index >= W11_START) & (bundle["combo_equity"].index <= W11_END)
    exposure = bundle["combo_exposure"].loc[mask].astype(float)
    sub = cycles[(cycles["re_time"] >= W11_START) & (cycles["re_time"] <= W11_END)].copy()
    return {
        "w11_entries": int(len(sub)),
        "w11_quick14_pct": float(sub["quick_reflat_after_re_14d"].mean() * 100.0) if not sub.empty else 0.0,
        "w11_quick30_pct": float(sub["quick_reflat_after_re_30d"].mean() * 100.0) if not sub.empty else 0.0,
        "w11_avg_total_exposure": float(exposure.mean()) if not exposure.empty else 0.0,
    }


def scenario_results(df_5m: pd.DataFrame, df_4h: pd.DataFrame, background: pd.DataFrame, scenario: Dict) -> dict:
    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    indicators = build_core_indicators(df_4h, riskoff_params, ADOPTED_SPEC["ema_len"])
    weekly_close = indicators["close"].resample("W-SUN").last()
    indicators["weekly_rsi_14"] = compute_rsi(weekly_close, 14).reindex(indicators.index, method="ffill")
    base_instability = build_instability_flags(
        df_5m,
        df_4h,
        riskoff_params,
        ema_len=ADOPTED_SPEC["ema_len"],
        threshold=ADOPTED_SPEC["threshold"],
        flips30_threshold=ADOPTED_SPEC["flips30_threshold"],
        flips60_threshold=ADOPTED_SPEC["flips60_threshold"],
    )
    hv_pct = background["hv_pct_180d"].reindex(indicators.index).ffill()

    core_variants: dict[str, dict] = {}
    for hv_thr in [None, 0.85, 0.90]:
        env = base_instability["instability_state"].reindex(indicators.index).ffill().fillna("stable").copy()
        variant_key = "baseline" if hv_thr is None else f"hv{int(hv_thr * 100)}"
        if hv_thr is None:
            target = build_target(indicators, ADOPTED_SPEC, env)
            events = pd.DataFrame()
        else:
            env.loc[(hv_pct >= hv_thr).fillna(False)] = "highly_unstable"
            target, events = build_target_and_events(indicators, env, int(ADOPTED_SPEC["breakout_window"]))
        core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
        if hv_thr is None:
            trace = pd.DataFrame({"weight": target.astype(float)}, index=target.index)
            re_mask = (trace["weight"] >= 0.9999) & (trace["weight"].shift(1).fillna(trace["weight"].iloc[0]) < 0.9999)
            flat_mask = (trace["weight"] <= 1e-9) & (trace["weight"].shift(1).fillna(trace["weight"].iloc[0]) > 1e-9)
            ev = []
            for ts in trace.index[flat_mask]:
                ev.append({"timestamp": ts, "event": "FLAT", "reentry_path": "", "instability_state": env.loc[ts]})
            for ts in trace.index[re_mask]:
                ev.append({"timestamp": ts, "event": "RE", "reentry_path": "baseline_mainline", "instability_state": env.loc[ts]})
            events = pd.DataFrame(ev)
            if not events.empty:
                events["timestamp"] = pd.to_datetime(events["timestamp"], utc=True)
        cycles = build_cycles(events, variant_key)
        core_variants[variant_key] = {"core_sim": core_sim, "cycles": cycles}

    formal_bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])
    atr_scale = background["atr_scale"].reindex(formal_bundle["index"]).ffill().fillna(1.0)
    s1_scaled_eq, s1_scaled_w = scale_sleeve(formal_bundle["s1_equity"], formal_bundle["s1_weight"], atr_scale)
    s2_scaled_eq, s2_scaled_w = scale_sleeve(formal_bundle["s2_equity"], formal_bundle["s2_weight"], atr_scale)

    out: dict[str, dict] = {}
    for cand in GRID:
        core_key = "baseline" if cand.hv_force_hc_threshold is None else f"hv{int(cand.hv_force_hc_threshold * 100)}"
        core_variant = core_variants[core_key]
        s1_eq = s1_scaled_eq if cand.atrvt_s1 else formal_bundle["s1_equity"]
        s1_w = s1_scaled_w if cand.atrvt_s1 else formal_bundle["s1_weight"]
        s2_eq = s2_scaled_eq if cand.atrvt_s2 else formal_bundle["s2_equity"]
        s2_w = s2_scaled_w if cand.atrvt_s2 else formal_bundle["s2_weight"]
        combo = evaluate_combo(formal_bundle, core_variant["core_sim"], s1_eq, s1_w, s2_eq, s2_w)
        out[cand.key] = {
            "combo": combo,
            "cycles": core_variant["cycles"],
            "w06": w06_metrics(combo),
            "w11": w11_metrics(combo, core_variant["cycles"]),
        }
    return out


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    background = build_background(df_4h)
    background.reset_index().rename(columns={"index": "timestamp"}).to_csv(BACKGROUND_CSV, index=False)

    scenario_maps: dict[str, dict] = {}
    for scenario in SCENARIOS:
        scenario_maps[scenario["name"]] = scenario_results(df_5m, df_4h, background, scenario)

    rows = []
    window_rows = []
    for cand in GRID:
        default = scenario_maps["default"][cand.key]
        stress = scenario_maps["stress"][cand.key]
        harsh = scenario_maps["harsh_friction"][cand.key]
        row = {
            "candidate": cand.key,
            "label": cand.label,
            "atrvt_s1": cand.atrvt_s1,
            "atrvt_s2": cand.atrvt_s2,
            "hv_force_hc_threshold": cand.hv_force_hc_threshold,
            "default_return_pct": float(default["combo"]["metrics"]["TotalReturn_pct"]),
            "default_calmar": float(default["combo"]["metrics"]["Calmar"]),
            "default_maxdd_pct": float(default["combo"]["metrics"]["MaxDD_pct"]),
            "stress_return_pct": float(stress["combo"]["metrics"]["TotalReturn_pct"]),
            "stress_calmar": float(stress["combo"]["metrics"]["Calmar"]),
            "stress_maxdd_pct": float(stress["combo"]["metrics"]["MaxDD_pct"]),
            "harsh_return_pct": float(harsh["combo"]["metrics"]["TotalReturn_pct"]),
            "harsh_calmar": float(harsh["combo"]["metrics"]["Calmar"]),
            "harsh_maxdd_pct": float(harsh["combo"]["metrics"]["MaxDD_pct"]),
        }
        row.update(default["w06"])
        row.update(default["w11"])
        rows.append(row)

        window_rows.append(
            {
                "candidate": cand.key,
                "label": cand.label,
                "window": "W06",
                **default["w06"],
            }
        )
        window_rows.append(
            {
                "candidate": cand.key,
                "label": cand.label,
                "window": "W11",
                **default["w11"],
            }
        )

    summary_df = pd.DataFrame(rows)
    windows_df = pd.DataFrame(window_rows)
    SUMMARY_CSV.write_text(summary_df.to_csv(index=False), encoding="utf-8")
    WINDOWS_CSV.write_text(windows_df.to_csv(index=False), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    baseline = summary_df[summary_df["candidate"] == "baseline"].iloc[0]
    best_p0 = summary_df[summary_df["candidate"].isin(["p0_atrvt_s2", "p0_atrvt_all"])].sort_values(
        ["w06_dd_over_avg_exposure_pct", "default_calmar", "default_return_pct"],
        ascending=[False, False, False],
    ).iloc[0]
    best_p1 = summary_df[summary_df["candidate"].isin(["p1_hv85_coregate", "p1_hv90_coregate"])].sort_values(
        ["w11_entries", "w11_quick14_pct", "default_calmar", "default_return_pct"],
        ascending=[True, True, False, False],
    ).iloc[0]
    best_combo = summary_df[summary_df["candidate"].isin(["combo_s2_hv85", "combo_all_hv85"])].sort_values(
        ["default_calmar", "default_return_pct"],
        ascending=[False, False],
    ).iloc[0]

    bg = background.copy()
    w06_bg = bg[(bg.index >= W06_START) & (bg.index <= W06_END)]
    w11_bg = bg[(bg.index >= W11_START) & (bg.index <= W11_END)]

    lines = [
        "# Volatility Proxy System Upgrade",
        "",
        "- Scope: independent system-level research for the two defects surfaced by `W06` and `W11`.",
        "- Mainline not changed.",
        "- P0 route: ATR-based vol-targeting for sleeves.",
        "- P1 route: HV percentile as a background detector that can force high-churn core qualification earlier.",
        "",
        "## Background Data",
        "",
        f"- `ATR14` proxy built on 4h bars; position scaler uses trailing `180d` ATR%% median / current ATR%%, clipped to `{ATR_SCALE_MIN:.2f}x ~ {ATR_SCALE_MAX:.2f}x`.",
        f"- `HV14` uses 14-day rolling log-return volatility on 4h bars, annualized with `sqrt(6*365)`.",
        f"- `HV percentile` is current HV's rolling rank inside trailing `180d`.",
        f"- `W06` background: median ATR scale `{w06_bg['atr_scale'].median():.2f}x`, HV>=85 share `{w06_bg['hv_ge_85'].mean() * 100.0:.1f}%`, HV>=90 share `{w06_bg['hv_ge_90'].mean() * 100.0:.1f}%`.",
        f"- `W11` background: median ATR scale `{w11_bg['atr_scale'].median():.2f}x`, HV>=85 share `{w11_bg['hv_ge_85'].mean() * 100.0:.1f}%`, HV>=90 share `{w11_bg['hv_ge_90'].mean() * 100.0:.1f}%`.",
        "",
        "## Full-Sample Summary",
        "",
        "| Candidate | Default Return% | Default Calmar | Default MaxDD% | Stress Calmar | Harsh Calmar | W06 DD/Exp | W11 Entries | W11 Quick14 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in summary_df.sort_values(["default_calmar", "default_return_pct"], ascending=[False, False]).iterrows():
        lines.append(
            f"| {row['label']} | {row['default_return_pct']:.2f} | {row['default_calmar']:.3f} | {row['default_maxdd_pct']:.2f} | "
            f"{row['stress_calmar']:.3f} | {row['harsh_calmar']:.3f} | {row['w06_dd_over_avg_exposure_pct']:.1f}% | "
            f"{int(row['w11_entries'])} | {row['w11_quick14_pct']:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Readout",
            "",
            f"- Baseline mainline: default `Return {baseline['default_return_pct']:.2f}% / Calmar {baseline['default_calmar']:.3f} / MaxDD {baseline['default_maxdd_pct']:.2f}%`; W06 `DD/Exp {baseline['w06_dd_over_avg_exposure_pct']:.1f}%`; W11 `entries {int(baseline['w11_entries'])}, quick14 {baseline['w11_quick14_pct']:.1f}%`.",
            f"- Best P0-only candidate: `{best_p0['label']}` with default `Return {best_p0['default_return_pct']:.2f}% / Calmar {best_p0['default_calmar']:.3f} / MaxDD {best_p0['default_maxdd_pct']:.2f}%`; W06 `DD/Exp {best_p0['w06_dd_over_avg_exposure_pct']:.1f}%`.",
            f"- Best P1-only candidate: `{best_p1['label']}` with default `Return {best_p1['default_return_pct']:.2f}% / Calmar {best_p1['default_calmar']:.3f} / MaxDD {best_p1['default_maxdd_pct']:.2f}%`; W11 `entries {int(best_p1['w11_entries'])}, quick14 {best_p1['w11_quick14_pct']:.1f}%`.",
            f"- Best combined candidate: `{best_combo['label']}` with default `Return {best_combo['default_return_pct']:.2f}% / Calmar {best_combo['default_calmar']:.3f} / MaxDD {best_combo['default_maxdd_pct']:.2f}%`; W06 `DD/Exp {best_combo['w06_dd_over_avg_exposure_pct']:.1f}%`; W11 `entries {int(best_combo['w11_entries'])}, quick14 {best_combo['w11_quick14_pct']:.1f}%`.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_MD), "summary_csv": str(SUMMARY_CSV), "background_csv": str(BACKGROUND_CSV)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
