#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent audition for high-churn hybrid re-entry qualifications."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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
AUDIT_MD = OUT_DIR / "STATE_AWARE_HYBRID_QUALIFICATION_AUDIT.md"
SUMMARY_CSV = OUT_DIR / "state_aware_hybrid_qualification_summary.csv"
SUMMARY_JSON = OUT_DIR / "state_aware_hybrid_qualification_summary.json"
WINDOWS_CSV = OUT_DIR / "state_aware_hybrid_qualification_windows.csv"
PLOTS_HTML = OUT_DIR / "STATE_AWARE_HYBRID_QUALIFICATION_AUDIT.html"

WINDOWS = [
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
        "label": "Default tuple",
        "formal_overrides": {},
        "riskoff_overrides": {
            "entry_execution_mode": "next_bar_open",
            "intrabar_execution_model": "legacy_bar_extrema",
            "intrabar_path_mode": "midpoint",
        },
    },
    {
        "name": "stress",
        "label": "Stress tuple",
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
        "label": "Harsh friction",
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
class Candidate:
    key: str
    label: str
    description: str
    family: str
    color: str
    window_bars: int = 4


CANDIDATES = [
    Candidate("baseline_close3", "Baseline close3", "Current mainline full qualification.", "baseline", "#0f172a", 0),
    Candidate(
        "state_aware_highly_unstable_strict",
        "State-aware: high churn -> strict EMA50",
        "Stable windows keep baseline close3; highly unstable windows require strict EMA50.",
        "state_aware_strict",
        "#9333ea",
        0,
    ),
    Candidate(
        "state_aware_hybrid_strict_and_breakout4",
        "State-aware: high churn -> strict AND breakout (4 bars)",
        "Stable windows keep baseline close3; highly unstable windows require strict EMA50 first, then breakout_4 confirmation.",
        "hybrid_and",
        "#0ea5e9",
        4,
    ),
    Candidate(
        "state_aware_hybrid_strict_or_breakout4",
        "State-aware: high churn -> strict OR breakout (4 bars)",
        "Stable windows keep baseline close3; highly unstable windows pass immediately on strict, otherwise fall back to breakout_4.",
        "hybrid_or",
        "#059669",
        4,
    ),
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
        "formal_combo_equity": formal["combo_equity"].reindex(idx).ffill().bfill().astype(float),
        "formal_combo_exposure": formal["combo_exposure"].reindex(idx).ffill().bfill().astype(float),
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
    }


def core_state_events(df_5m: pd.DataFrame, df_4h: pd.DataFrame, riskoff_params) -> tuple[pd.Series, pd.Series]:
    indicators = build_core_indicators(df_4h, riskoff_params, ADOPTED_SPEC["ema_len"])
    target = build_core_target(indicators, ADOPTED_SPEC)
    core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
    core_exposure = core_sim["equity"]["exposure"].reindex(indicators.index).ffill().bfill().astype(float)
    transitions = pd.Series(0, index=core_exposure.index, dtype=int)
    transitions.loc[core_exposure.diff().abs().fillna(0.0) > 1e-9] = 1
    return core_exposure, transitions


def trailing_instability_flags(transitions: pd.Series) -> pd.DataFrame:
    out = pd.DataFrame(index=transitions.index)
    out["core_flips_30d"] = transitions.rolling(30 * 6, min_periods=1).sum().astype(float)
    out["core_flips_60d"] = transitions.rolling(60 * 6, min_periods=1).sum().astype(float)
    out["highly_unstable"] = (out["core_flips_30d"] >= 2) & (out["core_flips_60d"] >= 3)
    out["instability_state"] = np.where(out["highly_unstable"], "highly_unstable", "stable")
    return out


def strict_ema50_ok(row: pd.Series) -> bool:
    return bool(pd.notna(row["ema50"]) and pd.notna(row["ema50_slope"]) and row["ema50"] > row["ema"] and row["ema50_slope"] > 0)


def build_target_and_events(indicators: pd.DataFrame, instability: pd.DataFrame, candidate: Candidate) -> tuple[pd.Series, pd.DataFrame]:
    bearish = (indicators["close"] < indicators["ema"]) & (indicators["ema_slope"] < 0)
    close_confirm = indicators["close"] > indicators["ema"]
    weekly_trigger = (indicators["weekly_rsi_14"] <= 30.0).fillna(False)
    instability_state = instability["instability_state"].reindex(indicators.index).ffill().fillna("stable")

    state = "normal"
    bear_count = 0
    close_count = 0
    weights = []
    events = []

    qual_bars = 0
    armed_trigger_high = np.nan
    armed_gate = ""

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
        active_gate = "baseline_close3"

        if state == "armed":
            active_gate = armed_gate

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
            active_gate = "baseline_close3" if not hc else candidate.family
            if trig:
                state = "override_hold"
                event = "RE"
                reentry_path = "weekly_rsi30_hold"
                active_gate = "weekly_rsi30_hold"
                bear_count = 0
                close_count = 0
            elif close_count >= 3:
                if not hc or candidate.family == "baseline":
                    state = "normal"
                    event = "RE"
                    reentry_path = "normal_baseline_close3"
                    active_gate = "baseline_close3"
                    bear_count = 0
                    close_count = 0
                elif candidate.family == "state_aware_strict":
                    if strict_ok:
                        state = "normal"
                        event = "RE"
                        reentry_path = "normal_ema50_align_full"
                        active_gate = "strict"
                        bear_count = 0
                        close_count = 0
                elif candidate.family == "hybrid_and":
                    if strict_ok:
                        state = "armed"
                        event = "QUALIFY"
                        reentry_path = "qualify_strict_and_breakout4"
                        active_gate = "strict_and_breakout4"
                        armed_gate = "strict_and_breakout4"
                        qual_bars = 0
                        armed_trigger_high = float(row["high"])
                        bear_count = 0
                        close_count = 0
                elif candidate.family == "hybrid_or":
                    if strict_ok:
                        state = "normal"
                        event = "RE"
                        reentry_path = "normal_strict_or_breakout4_strict_leg"
                        active_gate = "strict"
                        bear_count = 0
                        close_count = 0
                    else:
                        state = "armed"
                        event = "QUALIFY"
                        reentry_path = "qualify_strict_or_breakout4"
                        active_gate = "breakout4_fallback"
                        armed_gate = "breakout4_fallback"
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
                active_gate = "weekly_rsi30_hold"
                qual_bars = 0
                armed_trigger_high = np.nan
                armed_gate = ""
                bear_count = 0
                close_count = 0
            elif bear_count >= 2 or qual_bars >= candidate.window_bars:
                state = "flat"
                event = "QUALIFY_FAIL"
                qual_bars = 0
                armed_trigger_high = np.nan
                armed_gate = ""
                bear_count = 0
                close_count = 0
            elif pd.notna(armed_trigger_high) and row["close"] > armed_trigger_high:
                state = "normal"
                event = "RE"
                reentry_path = f"normal_{candidate.key}"
                active_gate = armed_gate
                qual_bars = 0
                armed_trigger_high = np.nan
                armed_gate = ""
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
                    "candidate": candidate.key,
                    "from_state": prev_state,
                    "to_state": state,
                    "reentry_path": reentry_path,
                    "instability_state": env_state,
                    "active_gate": active_gate,
                }
            )

    target = pd.Series(weights, index=indicators.index, dtype=float)
    events_df = pd.DataFrame(events)
    if not events_df.empty:
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], utc=True)
    return target, events_df


def build_cycles(events: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "candidate",
        "flat_time",
        "re_time",
        "reentry_path",
        "instability_state",
        "active_gate",
        "days_re_to_next_flat",
        "quick_reflat_after_re_14d",
        "quick_reflat_after_re_30d",
    ]
    if events.empty:
        return pd.DataFrame(columns=columns)
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
                "active_gate": re["active_gate"],
                "days_re_to_next_flat": float((next_flat["timestamp"] - re["timestamp"]).total_seconds() / 86400.0) if next_flat is not None else np.nan,
                "quick_reflat_after_re_14d": bool(next_flat is not None and (next_flat["timestamp"] - re["timestamp"]).total_seconds() / 86400.0 <= 14.0),
                "quick_reflat_after_re_30d": bool(next_flat is not None and (next_flat["timestamp"] - re["timestamp"]).total_seconds() / 86400.0 <= 30.0),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def summarize_churn(cycles: pd.DataFrame, candidate_key: str) -> dict:
    sub = cycles[cycles["candidate"] == candidate_key].copy()
    unstable = sub[sub["instability_state"] == "highly_unstable"].copy()
    valid_all = sub["days_re_to_next_flat"].dropna()
    valid_unstable = unstable["days_re_to_next_flat"].dropna()
    return {
        "candidate": candidate_key,
        "full_re_count": int(len(sub)),
        "median_days_re_to_next_flat": float(valid_all.median()) if not valid_all.empty else np.nan,
        "quick_reflat_14d_ratio_pct": float(sub["quick_reflat_after_re_14d"].mean() * 100.0) if not sub.empty else np.nan,
        "quick_reflat_30d_ratio_pct": float(sub["quick_reflat_after_re_30d"].mean() * 100.0) if not sub.empty else np.nan,
        "highly_unstable_re_count": int(len(unstable)),
        "highly_unstable_median_days_re_to_next_flat": float(valid_unstable.median()) if not valid_unstable.empty else np.nan,
        "highly_unstable_quick_reflat_14d_ratio_pct": float(unstable["quick_reflat_after_re_14d"].mean() * 100.0) if not unstable.empty else np.nan,
        "highly_unstable_quick_reflat_30d_ratio_pct": float(unstable["quick_reflat_after_re_30d"].mean() * 100.0) if not unstable.empty else np.nan,
    }


def build_window_table(cycles: pd.DataFrame, candidate_key: str) -> List[dict]:
    sub = cycles[cycles["candidate"] == candidate_key].copy()
    rows = []
    for label, start, end in WINDOWS:
        win = sub[(sub["flat_time"] >= start) & (sub["flat_time"] < end)]
        rows.append(
            {
                "candidate": candidate_key,
                "window": label,
                "short14": int(win["quick_reflat_after_re_14d"].sum()) if not win.empty else 0,
                "short30": int(win["quick_reflat_after_re_30d"].sum()) if not win.empty else 0,
                "high_churn_short14": int(win[win["instability_state"] == "highly_unstable"]["quick_reflat_after_re_14d"].sum()) if not win.empty else 0,
                "high_churn_short30": int(win[win["instability_state"] == "highly_unstable"]["quick_reflat_after_re_30d"].sum()) if not win.empty else 0,
            }
        )
    return rows


def evaluate_scenario(df_5m: pd.DataFrame, df_4h: pd.DataFrame, scenario: Dict) -> Dict:
    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    indicators = build_indicators(df_4h, riskoff_params)
    _, transitions = core_state_events(df_5m, df_4h, riskoff_params)
    instability = trailing_instability_flags(transitions)
    bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])

    systems = {}
    windows = []
    churn_rows = []
    for candidate in CANDIDATES:
        target, events = build_target_and_events(indicators, instability, candidate)
        core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
        combo = evaluate_combo(bundle, core_sim)
        systems[candidate.key] = {**combo, "target": target, "events": events}
        if scenario["name"] == "default":
            cycles = build_cycles(events)
            windows.extend(build_window_table(cycles, candidate.key))
            churn_rows.append(summarize_churn(cycles, candidate.key))
    return {
        "systems": systems,
        "instability": instability if scenario["name"] == "default" else None,
        "windows": windows,
        "churn_rows": churn_rows,
    }


def write_plot(default_systems: Dict, default_instability: pd.DataFrame) -> None:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.48, 0.30, 0.22],
        subplot_titles=("Equity Curves", "Underwater", "High-Churn State"),
    )
    for candidate in CANDIDATES:
        series = default_systems[candidate.key]["combo_equity"]
        uw = (series / series.cummax() - 1.0) * 100.0
        fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=candidate.label, line=dict(width=2.0, color=candidate.color)), row=1, col=1)
        fig.add_trace(go.Scatter(x=uw.index, y=uw, mode="lines", name=f"{candidate.label} UW", line=dict(width=1.2, color=candidate.color), showlegend=False), row=2, col=1)
    hc = default_instability["highly_unstable"].astype(int)
    fig.add_trace(go.Scatter(x=hc.index, y=hc, mode="lines", name="Highly unstable", line=dict(width=1.4, color="#475569")), row=3, col=1)
    fig.update_layout(template="plotly_white", height=1100, hovermode="x unified", title="State-Aware Hybrid Qualification Audit")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Underwater %", row=2, col=1)
    fig.update_yaxes(title_text="High churn", tickmode="array", tickvals=[0, 1], ticktext=["off", "on"], row=3, col=1)
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def write_report(report: Dict, summary_df: pd.DataFrame, churn_df: pd.DataFrame, window_df: pd.DataFrame) -> None:
    default_df = summary_df[summary_df["scenario"] == "default"].copy()
    stress_df = summary_df[summary_df["scenario"] == "stress"].copy()
    harsh_df = summary_df[summary_df["scenario"] == "harsh_friction"].copy()
    base_default = default_df[default_df["candidate"] == "baseline_close3"].iloc[0]
    strict_default = default_df[default_df["candidate"] == "state_aware_highly_unstable_strict"].iloc[0]

    def scenario_delta(df: pd.DataFrame, cand_key: str) -> Dict[str, float]:
        base = df[df["candidate"] == "baseline_close3"].iloc[0]
        cand = df[df["candidate"] == cand_key].iloc[0]
        return {
            "d_return": float(cand["return_pct"] - base["return_pct"]),
            "d_calmar": float(cand["calmar"] - base["calmar"]),
            "d_maxdd": float(cand["maxdd_pct"] - base["maxdd_pct"]),
        }

    lines = [
        "# State-Aware Hybrid Qualification Audit",
        "",
        "## Scope",
        "",
        "- Mainline reference: `baseline close3`.",
        "- Keep `state-aware strict` as the standing strongest challenger and reference group.",
        "- Only test high-churn hybrid qualifications:",
        "  `strict AND breakout_4`",
        "  `strict OR breakout_4`",
        "- Sell-side and `weekly_rsi30_hold` stay fixed.",
        "- Audit focus: `default / stress / harsh_friction`, high-churn churn metrics, recent two windows, and whether FULL RE count gets over-compressed.",
        "",
        "## Default",
        "",
        "| System | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in CANDIDATES:
        row = default_df[default_df["candidate"] == candidate.key].iloc[0]
        lines.append(
            f"| {candidate.label} | {row['return_pct']:.2f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
            f"{row['worst3m_pct']:.2f} | {row['worst6m_pct']:.2f} | {row['recovery_days']:.1f} |"
        )

    lines.extend([
        "",
        "## Stress / Harsh Delta Vs Mainline",
        "",
        "| Candidate | Default dReturn | Default dCalmar | Default dMaxDD | Stress dReturn | Stress dCalmar | Stress dMaxDD | Harsh dReturn | Harsh dCalmar | Harsh dMaxDD |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for candidate in CANDIDATES:
        if candidate.key == "baseline_close3":
            continue
        d0 = scenario_delta(default_df, candidate.key)
        ds = scenario_delta(stress_df, candidate.key)
        dh = scenario_delta(harsh_df, candidate.key)
        lines.append(
            f"| {candidate.label} | {d0['d_return']:+.2f}pp | {d0['d_calmar']:+.3f} | {d0['d_maxdd']:+.2f}pp | "
            f"{ds['d_return']:+.2f}pp | {ds['d_calmar']:+.3f} | {ds['d_maxdd']:+.2f}pp | "
            f"{dh['d_return']:+.2f}pp | {dh['d_calmar']:+.3f} | {dh['d_maxdd']:+.2f}pp |"
        )

    lines.extend([
        "",
        "## Default Churn Audit",
        "",
        "| System | FULL RE | RE->next FLAT Median Days | Quick re-FLAT 14d | Quick re-FLAT 30d | High-Churn FULL RE | High-Churn Median Days | High-Churn Quick 14d | High-Churn Quick 30d |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for candidate in CANDIDATES:
        row = churn_df[churn_df["candidate"] == candidate.key].iloc[0]
        lines.append(
            f"| {candidate.label} | {int(row['full_re_count'])} | {row['median_days_re_to_next_flat']:.1f} | {row['quick_reflat_14d_ratio_pct']:.1f}% | "
            f"{row['quick_reflat_30d_ratio_pct']:.1f}% | {int(row['highly_unstable_re_count'])} | {row['highly_unstable_median_days_re_to_next_flat']:.1f} | "
            f"{row['highly_unstable_quick_reflat_14d_ratio_pct']:.1f}% | {row['highly_unstable_quick_reflat_30d_ratio_pct']:.1f}% |"
        )

    lines.extend(["", "## Recent Windows", ""])
    for candidate in CANDIDATES:
        lines.append(f"### {candidate.label}")
        lines.append("")
        sub = window_df[window_df["candidate"] == candidate.key]
        for _, row in sub.iterrows():
            lines.append(
                f"- {row['window']}: short 14d / 30d = `{int(row['short14'])}` / `{int(row['short30'])}`, high-churn short 14d / 30d = `{int(row['high_churn_short14'])}` / `{int(row['high_churn_short30'])}`"
            )
        lines.append("")

    and_default = default_df[default_df["candidate"] == "state_aware_hybrid_strict_and_breakout4"].iloc[0]
    or_default = default_df[default_df["candidate"] == "state_aware_hybrid_strict_or_breakout4"].iloc[0]
    lines.extend([
        "## Readout",
        "",
        f"- Standing challenger remains `state-aware strict`: Return `{strict_default['return_pct']:.2f}%`, Calmar `{strict_default['calmar']:.3f}`, MaxDD `{strict_default['maxdd_pct']:.2f}%`.",
        f"- `Strict AND breakout_4` vs standing challenger: dReturn `{and_default['return_pct'] - strict_default['return_pct']:+.2f}pp`, dCalmar `{and_default['calmar'] - strict_default['calmar']:+.3f}`, dMaxDD `{and_default['maxdd_pct'] - strict_default['maxdd_pct']:+.2f}pp`.",
        f"- `Strict OR breakout_4` vs standing challenger: dReturn `{or_default['return_pct'] - strict_default['return_pct']:+.2f}pp`, dCalmar `{or_default['calmar'] - strict_default['calmar']:+.3f}`, dMaxDD `{or_default['maxdd_pct'] - strict_default['maxdd_pct']:+.2f}pp`.",
        "- Promotion bar here is stricter than just reducing churn: the hybrid should survive default / stress / harsh without over-compressing FULL RE count and without losing too much total-return efficiency.",
    ])
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    report = {}
    summary_rows = []
    for scenario in SCENARIOS:
        result = evaluate_scenario(df_5m, df_4h, scenario)
        report[scenario["name"]] = result
        for candidate in CANDIDATES:
            combo = result["systems"][candidate.key]
            summary_rows.append(
                {
                    "scenario": scenario["name"],
                    "candidate": candidate.key,
                    "label": candidate.label,
                    "return_pct": combo["metrics"]["TotalReturn_pct"],
                    "calmar": combo["metrics"]["Calmar"],
                    "maxdd_pct": combo["metrics"]["MaxDD_pct"],
                    "worst3m_pct": combo["path"]["worst_3m_cluster_return_pct"],
                    "worst6m_pct": combo["path"]["worst_6m_cluster_return_pct"],
                    "recovery_days": combo["path"]["recovery_days_from_maxdd"],
                }
            )

    summary_df = pd.DataFrame(summary_rows)
    churn_df = pd.DataFrame(report["default"]["churn_rows"])
    window_df = pd.DataFrame(report["default"]["windows"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    if not window_df.empty:
        window_df.to_csv(WINDOWS_CSV, index=False)
    write_plot(report["default"]["systems"], report["default"]["instability"])
    write_report(report, summary_df, churn_df, window_df)
    payload = {
        "summary": summary_df.to_dict(orient="records"),
        "default_churn": churn_df.to_dict(orient="records"),
        "default_windows": window_df.to_dict(orient="records"),
    }
    SUMMARY_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"audit": AUDIT_MD.name, "summary_csv": SUMMARY_CSV.name, "windows_csv": WINDOWS_CSV.name, "plot": PLOTS_HTML.name}, ensure_ascii=False))


if __name__ == "__main__":
    main()
