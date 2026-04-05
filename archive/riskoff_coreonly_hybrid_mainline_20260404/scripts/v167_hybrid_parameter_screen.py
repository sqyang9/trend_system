#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight parameter screen for the promoted hybrid qualification."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_addon_grading_study import current_research_optimal as formal_current_research_optimal
from v90_asset_management_system_aligned import (
    compute_metrics,
    current_research_optimal as riskoff_current_research_optimal,
    simulate_core,
)
from v90_riskoff_promotion_v2 import build_indicator_cache
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v92_const1x_deployment_audit import loss_cluster_diagnostics, path_diagnostics
from v95_range_rotation_mean_reversion_audit import make_range_rotation_params
from v96_range_rotation_mean_reversion_s3_audit import scenario_systems
from v121_coreonly_riskoff_sellside_ema_audit import build_indicators as build_core_indicators
from v121_coreonly_riskoff_sellside_ema_audit import build_target as build_core_target


OUT_DIR = Path("reentry_qualification_research")
AUDIT_MD = OUT_DIR / "HYBRID_PARAMETER_SCREEN.md"
SUMMARY_CSV = OUT_DIR / "hybrid_parameter_screen_summary.csv"
WINDOWS_CSV = OUT_DIR / "hybrid_parameter_screen_windows.csv"
CHURN_CSV = OUT_DIR / "hybrid_parameter_screen_churn.csv"
SUMMARY_JSON = OUT_DIR / "hybrid_parameter_screen.json"

RECENT_WINDOWS = [
    ("2024-12_to_2025-06", pd.Timestamp("2024-12-01", tz="UTC"), pd.Timestamp("2025-06-01", tz="UTC")),
    ("2025-06_to_2025-12", pd.Timestamp("2025-06-01", tz="UTC"), pd.Timestamp("2025-12-01", tz="UTC")),
]

ADOPTED_SPEC = {
    "name": "WRSI14_30_EMA250",
    "reentry_family": "weekly_rsi_hold",
    "rsi_period": 14,
    "threshold": 30.0,
    "ema_len": 250,
}

SCENARIOS = [
    {
        "name": "default",
        "formal_overrides": {},
        "riskoff_overrides": {
            "entry_execution_mode": "next_bar_open",
            "intrabar_execution_model": "legacy_bar_extrema",
            "intrabar_path_mode": "midpoint",
        },
    },
    {
        "name": "stress",
        "formal_overrides": {
            "entry_execution_mode": "live_runner_next_5m_close",
            "intrabar_execution_model": "segment_path_same_bar",
            "intrabar_path_mode": "pessimistic",
        },
        "riskoff_overrides": {
            "entry_execution_mode": "live_runner_next_5m_close",
            "intrabar_execution_model": "segment_path_same_bar",
            "intrabar_path_mode": "pessimistic",
        },
    },
    {
        "name": "harsh_friction",
        "formal_overrides": {
            "entry_execution_mode": "live_runner_next_5m_close",
            "intrabar_execution_model": "segment_path_same_bar",
            "intrabar_path_mode": "pessimistic",
            "commission_pct": 0.12,
            "close_delay_bps": 12.0,
            "slippage_fixed_bps": 8.0,
            "slippage_breakout_extra_bps": 8.0,
            "slippage_stop_extra_bps": 12.0,
            "slippage_range_weight": 0.08,
            "slippage_max_bps": 35.0,
        },
        "riskoff_overrides": {
            "entry_execution_mode": "live_runner_next_5m_close",
            "intrabar_execution_model": "segment_path_same_bar",
            "intrabar_path_mode": "pessimistic",
            "commission_pct": 0.12,
            "close_delay_bps": 12.0,
            "slippage_fixed_bps": 8.0,
            "slippage_breakout_extra_bps": 8.0,
            "slippage_stop_extra_bps": 12.0,
            "slippage_range_weight": 0.08,
            "slippage_max_bps": 35.0,
        },
    },
]


@dataclass(frozen=True)
class ParamSpec:
    key: str
    label: str
    flips30_threshold: int
    flips60_threshold: int
    breakout_window: int


GRID: List[ParamSpec] = [
    ParamSpec("hc23_b3", "HC 2/3 + breakout_3", 2, 3, 3),
    ParamSpec("hc23_b4", "HC 2/3 + breakout_4", 2, 3, 4),
    ParamSpec("hc23_b5", "HC 2/3 + breakout_5", 2, 3, 5),
    ParamSpec("hc23_b6", "HC 2/3 + breakout_6", 2, 3, 6),
    ParamSpec("hc24_b4", "HC 2/4 + breakout_4", 2, 4, 4),
    ParamSpec("hc34_b4", "HC 3/4 + breakout_4", 3, 4, 4),
    ParamSpec("hc35_b4", "HC 3/5 + breakout_4", 3, 5, 4),
]


def compute_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def build_indicators(df_4h: pd.DataFrame, riskoff_params) -> pd.DataFrame:
    cache = build_indicator_cache(df_4h, riskoff_params, [50, 250], ensure_datetime(df_4h)["timestamp"])
    out = cache[250].copy()
    ema50 = cache[50]
    out["ema50"] = ema50["ema"]
    out["ema50_slope"] = ema50["ema_slope"]
    weekly_close = out["close"].resample("W-SUN").last()
    out["weekly_rsi_14"] = compute_rsi(weekly_close, 14).reindex(out.index, method="ffill")
    return out


def build_formal_bundle(df_5m: pd.DataFrame, df_4h: pd.DataFrame, formal_overrides: Dict) -> dict:
    formal_params = formal_current_research_optimal(**formal_overrides)
    range_params = make_range_rotation_params(**formal_overrides)
    payload = scenario_systems(formal_params, range_params, df_5m, df_4h)
    systems = payload["systems"]
    const1x = systems["Core+ConstAddOn[1.00x]"]
    formal = systems["Core+ConstAddOn[1.00x]+RangeRotation"]
    core_only = systems["CoreOnly"]
    candidate_sleeve = payload["candidate_sleeve"]
    idx = formal["combo_equity"].index
    const1x_equity = const1x["combo_equity"].reindex(idx).ffill().bfill().astype(float)
    formal_equity = formal["combo_equity"].reindex(idx).ffill().bfill().astype(float)
    base_coreonly_equity = core_only["combo_equity"].reindex(idx).ffill().bfill().astype(float)
    return {
        "index": idx,
        "base_s1_pnl": (const1x_equity.diff().fillna(0.0) - base_coreonly_equity.diff().fillna(0.0)).astype(float),
        "base_s1_weight": const1x["sleeve"]["weight"].reindex(idx).fillna(0.0).astype(float),
        "base_s2_pnl": (formal_equity.diff().fillna(0.0) - const1x_equity.diff().fillna(0.0)).astype(float),
        "base_s2_weight": candidate_sleeve["weight"].reindex(idx).fillna(0.0).astype(float),
    }


def path_bundle(equity: pd.Series) -> dict:
    pdx = path_diagnostics(equity)
    clusters = loss_cluster_diagnostics(equity)
    maxdd_episode = pdx["worst_underwater_episodes"][0] if pdx["worst_underwater_episodes"] else None
    return {
        "worst_3m_cluster_return_pct": float(clusters["worst_3m_cluster_return_pct"]),
        "worst_6m_cluster_return_pct": float(clusters["worst_6m_cluster_return_pct"]),
        "recovery_days_from_maxdd": float(maxdd_episode["recovery_days_from_trough"]) if maxdd_episode is not None else 0.0,
    }


def evaluate_combo(bundle: dict, core_sim: dict) -> dict:
    idx = bundle["index"]
    base_core_equity = core_sim["equity"]["equity"].reindex(idx).ffill().bfill().astype(float)
    base_core_pnl = base_core_equity.diff().fillna(0.0) * 0.75
    base_core_exposure = core_sim["equity"]["exposure"].reindex(idx).ffill().bfill().astype(float) * 0.75
    s1_pnl = bundle["base_s1_pnl"] * 1.25
    s1_weight = bundle["base_s1_weight"] * 1.25
    s2_pnl = bundle["base_s2_pnl"] * 1.00
    s2_weight = bundle["base_s2_weight"] * 1.00
    combo_equity = (10000.0 + (base_core_pnl + s1_pnl + s2_pnl).cumsum()).astype(float)
    combo_exposure = (base_core_exposure + s1_weight + s2_weight).astype(float)
    metrics = extended_metrics({"combo_equity": combo_equity, "combo_metrics": compute_metrics(combo_equity, combo_exposure)})
    return {
        "combo_equity": combo_equity,
        "combo_exposure": combo_exposure,
        "metrics": metrics,
        "path": path_bundle(combo_equity),
        "avg_core_exposure_pct": float(base_core_exposure.mean() * 100.0),
    }


def strict_ema50_ok(row: pd.Series) -> bool:
    return bool(pd.notna(row["ema50"]) and pd.notna(row["ema50_slope"]) and row["ema50"] > row["ema"] and row["ema50_slope"] > 0)


def baseline_core_transitions(df_5m: pd.DataFrame, df_4h: pd.DataFrame, riskoff_params) -> pd.Series:
    indicators = build_core_indicators(df_4h, riskoff_params, ADOPTED_SPEC["ema_len"])
    target = build_core_target(indicators, ADOPTED_SPEC)
    core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
    core_exposure = core_sim["equity"]["exposure"].reindex(indicators.index).ffill().bfill().astype(float)
    transitions = pd.Series(0, index=core_exposure.index, dtype=int)
    transitions.loc[core_exposure.diff().abs().fillna(0.0) > 1e-9] = 1
    return transitions


def instability_flags(transitions: pd.Series, flips30_threshold: int, flips60_threshold: int) -> pd.DataFrame:
    roll30 = transitions.rolling(30 * 6, min_periods=1).sum()
    roll60 = transitions.rolling(60 * 6, min_periods=1).sum()
    out = pd.DataFrame(index=transitions.index)
    out["instability_state"] = np.where((roll30 >= flips30_threshold) & (roll60 >= flips60_threshold), "highly_unstable", "stable")
    return out


def build_target_and_events(indicators: pd.DataFrame, instability: pd.DataFrame, spec: ParamSpec) -> tuple[pd.Series, pd.DataFrame]:
    bearish = (indicators["close"] < indicators["ema"]) & (indicators["ema_slope"] < 0)
    close_confirm = indicators["close"] > indicators["ema"]
    weekly_trigger = (indicators["weekly_rsi_14"] <= 30.0).fillna(False)
    instability_state = instability["instability_state"].reindex(indicators.index).ffill().fillna("stable")

    state = "normal"
    bear_count = 0
    close_count = 0
    qual_bars = 0
    armed_trigger_high = np.nan
    weights: list[float] = []
    events: list[dict] = []

    for ts, row in indicators.iterrows():
        is_bear = bool(bearish.loc[ts]) if pd.notna(bearish.loc[ts]) else False
        is_close = bool(close_confirm.loc[ts]) if pd.notna(close_confirm.loc[ts]) else False
        trig = bool(weekly_trigger.loc[ts])
        env_state = str(instability_state.loc[ts])
        hc = env_state == "highly_unstable"
        strict_ok = strict_ema50_ok(row)

        bear_count = bear_count + 1 if is_bear else 0
        close_count = close_count + 1 if is_close else 0

        prev_state = state
        event = ""
        reentry_path = ""

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
            if trig:
                state = "override_hold"
                event = "RE"
                reentry_path = "weekly_rsi30_hold"
                bear_count = 0
                close_count = 0
            elif close_count >= 3:
                if not hc:
                    state = "normal"
                    event = "RE"
                    reentry_path = "normal_baseline_close3"
                    bear_count = 0
                    close_count = 0
                elif strict_ok:
                    state = "armed"
                    event = "QUALIFY"
                    reentry_path = f"qualify_hc{spec.flips30_threshold}{spec.flips60_threshold}_breakout{spec.breakout_window}"
                    qual_bars = 0
                    armed_trigger_high = float(row["high"])
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
            elif bear_count >= 2 or qual_bars >= spec.breakout_window:
                state = "flat"
                event = "QUALIFY_FAIL"
                qual_bars = 0
                armed_trigger_high = np.nan
                bear_count = 0
                close_count = 0
            elif pd.notna(armed_trigger_high) and row["close"] > armed_trigger_high:
                state = "normal"
                event = "RE"
                reentry_path = f"normal_{spec.key}"
                qual_bars = 0
                armed_trigger_high = np.nan
                bear_count = 0
                close_count = 0
        elif state == "override_hold":
            if close_count >= 3:
                state = "normal"

        weight = 1.0 if state in {"normal", "override_hold"} else 0.5 if state == "soft_off" else 0.0
        weights.append(weight)
        if event:
            events.append(
                {
                    "timestamp": ts,
                    "event": event,
                    "candidate": spec.key,
                    "from_state": prev_state,
                    "to_state": state,
                    "reentry_path": reentry_path,
                    "instability_state": env_state,
                }
            )
    target = pd.Series(weights, index=indicators.index, dtype=float)
    events_df = pd.DataFrame(events)
    if not events_df.empty:
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], utc=True)
    return target, events_df


def build_cycles(events: pd.DataFrame) -> pd.DataFrame:
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
        rows.append(
            {
                "candidate": flat["candidate"],
                "flat_time": flat["timestamp"],
                "re_time": re["timestamp"],
                "reentry_path": re["reentry_path"],
                "instability_state": re["instability_state"],
                "days_re_to_next_flat": float((next_flat["timestamp"] - re["timestamp"]).total_seconds() / 86400.0) if next_flat is not None else np.nan,
                "quick_reflat_after_re_14d": bool(next_flat is not None and (next_flat["timestamp"] - re["timestamp"]).total_seconds() / 86400.0 <= 14.0),
                "quick_reflat_after_re_30d": bool(next_flat is not None and (next_flat["timestamp"] - re["timestamp"]).total_seconds() / 86400.0 <= 30.0),
            }
        )
    return pd.DataFrame(rows, columns=cols)


def summarize_churn(cycles: pd.DataFrame, spec: ParamSpec) -> dict:
    sub = cycles[cycles["candidate"] == spec.key].copy()
    unstable = sub[sub["instability_state"] == "highly_unstable"].copy()
    valid_all = sub["days_re_to_next_flat"].dropna()
    valid_unstable = unstable["days_re_to_next_flat"].dropna()
    return {
        "candidate": spec.key,
        "label": spec.label,
        "breakout_window": spec.breakout_window,
        "flips30_threshold": spec.flips30_threshold,
        "flips60_threshold": spec.flips60_threshold,
        "full_re_count": int(len(sub)),
        "median_days_re_to_next_flat": float(valid_all.median()) if not valid_all.empty else np.nan,
        "quick_reflat_14d_ratio_pct": float(sub["quick_reflat_after_re_14d"].mean() * 100.0) if not sub.empty else np.nan,
        "quick_reflat_30d_ratio_pct": float(sub["quick_reflat_after_re_30d"].mean() * 100.0) if not sub.empty else np.nan,
        "highly_unstable_re_count": int(len(unstable)),
        "highly_unstable_median_days_re_to_next_flat": float(valid_unstable.median()) if not valid_unstable.empty else np.nan,
        "highly_unstable_quick_reflat_14d_ratio_pct": float(unstable["quick_reflat_after_re_14d"].mean() * 100.0) if not unstable.empty else np.nan,
        "highly_unstable_quick_reflat_30d_ratio_pct": float(unstable["quick_reflat_after_re_30d"].mean() * 100.0) if not unstable.empty else np.nan,
    }


def build_window_table(cycles: pd.DataFrame, spec: ParamSpec) -> list[dict]:
    sub = cycles[cycles["candidate"] == spec.key].copy()
    rows = []
    for label, start, end in RECENT_WINDOWS:
        win = sub[(sub["flat_time"] >= start) & (sub["flat_time"] < end)]
        hc = win[win["instability_state"] == "highly_unstable"]
        rows.append(
            {
                "candidate": spec.key,
                "label": spec.label,
                "window": label,
                "short14": int(win["quick_reflat_after_re_14d"].sum()) if not win.empty else 0,
                "short30": int(win["quick_reflat_after_re_30d"].sum()) if not win.empty else 0,
                "high_churn_short14": int(hc["quick_reflat_after_re_14d"].sum()) if not hc.empty else 0,
                "high_churn_short30": int(hc["quick_reflat_after_re_30d"].sum()) if not hc.empty else 0,
            }
        )
    return rows


def evaluate_scenario(df_5m: pd.DataFrame, df_4h: pd.DataFrame, scenario: Dict) -> dict:
    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    indicators = build_indicators(df_4h, riskoff_params)
    transitions = baseline_core_transitions(df_5m, df_4h, riskoff_params)
    bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])

    systems = {}
    churn_rows: list[dict] = []
    window_rows: list[dict] = []
    for spec in GRID:
        instability = instability_flags(transitions, spec.flips30_threshold, spec.flips60_threshold)
        target, events = build_target_and_events(indicators, instability, spec)
        core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
        combo = evaluate_combo(bundle, core_sim)
        systems[spec.key] = {**combo, "events": events}
        if scenario["name"] == "default":
            cycles = build_cycles(events)
            churn_rows.append(summarize_churn(cycles, spec))
            window_rows.extend(build_window_table(cycles, spec))
    return {"systems": systems, "churn_rows": churn_rows, "window_rows": window_rows}


def pick_best(summary_df: pd.DataFrame, churn_df: pd.DataFrame) -> str:
    merged = summary_df[summary_df["scenario"] == "default"].merge(churn_df, on=["candidate", "label", "breakout_window", "flips30_threshold", "flips60_threshold"])
    stress = summary_df[summary_df["scenario"] == "stress"][["candidate", "calmar", "maxdd_pct"]].rename(columns={"calmar": "stress_calmar", "maxdd_pct": "stress_maxdd_pct"})
    harsh = summary_df[summary_df["scenario"] == "harsh_friction"][["candidate", "calmar", "maxdd_pct"]].rename(columns={"calmar": "harsh_calmar", "maxdd_pct": "harsh_maxdd_pct"})
    merged = merged.merge(stress, on="candidate").merge(harsh, on="candidate")
    eligible = merged[merged["full_re_count"] >= 35].copy()
    if eligible.empty:
        eligible = merged.copy()
    eligible = eligible.sort_values(
        [
            "calmar",
            "stress_calmar",
            "harsh_calmar",
            "return_pct",
            "highly_unstable_quick_reflat_14d_ratio_pct",
            "maxdd_pct",
        ],
        ascending=[False, False, False, False, True, False],
    )
    return str(eligible.iloc[0]["candidate"])


def write_report(summary_df: pd.DataFrame, churn_df: pd.DataFrame, window_df: pd.DataFrame, best_key: str) -> None:
    default_df = summary_df[summary_df["scenario"] == "default"].copy()
    best = default_df[default_df["candidate"] == best_key].iloc[0]
    current = default_df[default_df["candidate"] == "hc23_b4"].iloc[0]
    lines = [
        "# Hybrid Parameter Screen",
        "",
        "- Scope: only test two parameter classes for the promoted hybrid qualification.",
        "- Tuned dimensions:",
        "  - breakout window length",
        "  - high-churn trigger thresholds",
        "- Fixed:",
        "  - sell-side `EMA250`",
        "  - stable-environment `close3` full recovery",
        "  - high-churn gate family `strict EMA50 AND breakout`",
        "  - `weekly_rsi30_hold` override",
        "",
        "## Default Summary",
        "",
        "| Candidate | Return% | Calmar | MaxDD% | Full RE | HC quick 14d | HC quick 30d |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    merged = default_df.merge(
        churn_df[["candidate", "full_re_count", "highly_unstable_quick_reflat_14d_ratio_pct", "highly_unstable_quick_reflat_30d_ratio_pct"]],
        on="candidate",
    ).sort_values(["calmar", "return_pct"], ascending=[False, False])
    for _, row in merged.iterrows():
        lines.append(
            f"| {row['label']} | {row['return_pct']:.2f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
            f"{int(row['full_re_count'])} | {row['highly_unstable_quick_reflat_14d_ratio_pct']:.1f}% | {row['highly_unstable_quick_reflat_30d_ratio_pct']:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Readout",
            "",
            f"- Current promotion point `HC 2/3 + breakout_4`: Return `{current['return_pct']:.2f}%`, Calmar `{current['calmar']:.3f}`, MaxDD `{current['maxdd_pct']:.2f}%`.",
            f"- Best point in this lightweight screen: `{best['label']}` with Return `{best['return_pct']:.2f}%`, Calmar `{best['calmar']:.3f}`, MaxDD `{best['maxdd_pct']:.2f}%`.",
        ]
    )
    if best_key == "hc23_b4":
        lines.append("- Conclusion: the current promotion point remains the best or tied-best practical setting in this screen.")
    else:
        lines.append("- Conclusion: the current promotion point is not the screen winner and should be reviewed before promotion.")

    lines.extend(["", "## Recent Windows", ""])
    for spec in GRID:
        lines.extend(["", f"### {spec.label}", ""])
        sub = window_df[window_df["candidate"] == spec.key]
        for _, row in sub.iterrows():
            lines.append(
                f"- {row['window']}: short 14d / 30d = `{int(row['short14'])}` / `{int(row['short30'])}`, "
                f"high-churn short 14d / 30d = `{int(row['high_churn_short14'])}` / `{int(row['high_churn_short30'])}`"
            )
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    report = {}
    summary_rows: list[dict] = []
    churn_rows: list[dict] = []
    window_rows: list[dict] = []

    for scenario in SCENARIOS:
        result = evaluate_scenario(df_5m, df_4h, scenario)
        report[scenario["name"]] = result
        for spec in GRID:
            system = result["systems"][spec.key]
            summary_rows.append(
                {
                    "scenario": scenario["name"],
                    "candidate": spec.key,
                    "label": spec.label,
                    "breakout_window": spec.breakout_window,
                    "flips30_threshold": spec.flips30_threshold,
                    "flips60_threshold": spec.flips60_threshold,
                    "return_pct": float(system["metrics"]["TotalReturn_pct"]),
                    "calmar": float(system["metrics"]["Calmar"]),
                    "maxdd_pct": float(system["metrics"]["MaxDD_pct"]),
                    "worst3m_pct": float(system["path"]["worst_3m_cluster_return_pct"]),
                    "worst6m_pct": float(system["path"]["worst_6m_cluster_return_pct"]),
                    "recovery_days": float(system["path"]["recovery_days_from_maxdd"]),
                    "avg_core_exposure_pct": float(system["avg_core_exposure_pct"]),
                }
            )
        churn_rows.extend(result["churn_rows"])
        window_rows.extend(result["window_rows"])

    summary_df = pd.DataFrame(summary_rows)
    churn_df = pd.DataFrame(churn_rows)
    window_df = pd.DataFrame(window_rows)
    best_key = pick_best(summary_df, churn_df)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_CSV.write_text(summary_df.to_csv(index=False), encoding="utf-8")
    CHURN_CSV.write_text(churn_df.to_csv(index=False), encoding="utf-8")
    WINDOWS_CSV.write_text(window_df.to_csv(index=False), encoding="utf-8")
    write_report(summary_df, churn_df, window_df, best_key)
    SUMMARY_JSON.write_text(
        json.dumps(
            {
                "best_candidate": best_key,
                "summary": summary_rows,
                "churn": churn_rows,
                "windows": window_rows,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"best_candidate": best_key, "report": str(AUDIT_MD), "summary_csv": str(SUMMARY_CSV)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
