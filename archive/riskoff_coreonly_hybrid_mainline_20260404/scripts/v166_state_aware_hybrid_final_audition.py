#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final audition-style audit for the strongest state-aware hybrid qualification."""

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
AUDIT_MD = OUT_DIR / "STATE_AWARE_HYBRID_FINAL_AUDITION.md"
SUMMARY_CSV = OUT_DIR / "state_aware_hybrid_final_audition_summary.csv"
SUMMARY_JSON = OUT_DIR / "state_aware_hybrid_final_audition.json"
WINDOWS_CSV = OUT_DIR / "state_aware_hybrid_final_audition_windows.csv"
CHURN_CSV = OUT_DIR / "state_aware_hybrid_final_audition_churn.csv"
ANNUAL_CSV = OUT_DIR / "state_aware_hybrid_final_audition_annual_starts.csv"
PLOTS_HTML = OUT_DIR / "STATE_AWARE_HYBRID_FINAL_AUDITION.html"

WINDOWS = [
    ("2024-12_to_2025-06", pd.Timestamp("2024-12-01", tz="UTC"), pd.Timestamp("2025-06-01", tz="UTC")),
    ("2025-06_to_2025-12", pd.Timestamp("2025-06-01", tz="UTC"), pd.Timestamp("2025-12-01", tz="UTC")),
]

ANNUAL_STARTS = [
    pd.Timestamp("2020-01-01", tz="UTC"),
    pd.Timestamp("2021-01-01", tz="UTC"),
    pd.Timestamp("2022-01-01", tz="UTC"),
    pd.Timestamp("2023-01-01", tz="UTC"),
    pd.Timestamp("2024-01-01", tz="UTC"),
    pd.Timestamp("2025-01-01", tz="UTC"),
    pd.Timestamp("2026-01-01", tz="UTC"),
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
    family: str
    color: str
    window_bars: int = 4


CANDIDATES = [
    Candidate("baseline_close3", "Mainline baseline close3", "baseline", "#0f172a", 0),
    Candidate("state_aware_highly_unstable_strict", "Reference: high churn -> strict EMA50", "state_aware_strict", "#9333ea", 0),
    Candidate("state_aware_hybrid_strict_and_breakout4", "Challenger: high churn -> strict AND breakout (4 bars)", "hybrid_and", "#0ea5e9", 4),
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
        "sleeve1_active_ratio_pct": float((const1x["sleeve"]["weight"].reindex(idx).fillna(0.0) > 1e-9).mean() * 100.0),
        "sleeve2_active_ratio_pct": float((candidate_sleeve["weight"].reindex(idx).fillna(0.0) > 1e-9).mean() * 100.0),
    }


def path_bundle(equity: pd.Series) -> dict:
    pdx = path_diagnostics(equity)
    clusters = loss_cluster_diagnostics(equity)
    maxdd_episode = pdx["worst_underwater_episodes"][0] if pdx["worst_underwater_episodes"] else None
    return {
        "worst_3m_cluster_return_pct": float(clusters["worst_3m_cluster_return_pct"]),
        "worst_6m_cluster_return_pct": float(clusters["worst_6m_cluster_return_pct"]),
        "rolling_180d_worst_maxdd_pct": float(pdx["rolling_180d"]["worst_maxdd_pct"]),
        "rolling_365d_worst_return_pct": float(pdx["rolling_365d"]["worst_return_pct"]),
        "longest_negative_month_streak": int(clusters["longest_negative_month_streak"]),
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
        "avg_total_exposure_pct": float(combo_exposure.mean() * 100.0),
        "peak_total_exposure_pct": float(combo_exposure.max() * 100.0),
        "avg_core_exposure_pct": float(base_core_exposure.mean() * 100.0),
        "riskoff_active_ratio_pct": float((base_core_exposure < 0.7499).mean() * 100.0),
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
    roll30 = transitions.rolling(30 * 6, min_periods=1).sum()
    roll60 = transitions.rolling(60 * 6, min_periods=1).sum()
    out = pd.DataFrame(index=transitions.index)
    out["core_flips_30d"] = roll30.astype(float)
    out["core_flips_60d"] = roll60.astype(float)
    out["highly_unstable"] = (roll30 >= 2) & (roll60 >= 3)
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
        active_gate = "baseline_close3" if not hc else candidate.family
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


def annual_start_metrics(equity: pd.Series, exposure: pd.Series) -> Dict:
    metrics = extended_metrics({"combo_equity": equity, "combo_metrics": compute_metrics(equity, exposure)})
    path = path_bundle(equity)
    return {
        "return_pct": float(metrics["TotalReturn_pct"]),
        "calmar": float(metrics["Calmar"]),
        "maxdd_pct": float(metrics["MaxDD_pct"]),
        "worst3m_pct": float(path["worst_3m_cluster_return_pct"]),
        "worst6m_pct": float(path["worst_6m_cluster_return_pct"]),
        "recovery_days": float(path["recovery_days_from_maxdd"]),
        "avg_total_exposure_pct": float(exposure.mean() * 100.0),
    }


def evaluate_scenario(df_5m: pd.DataFrame, df_4h: pd.DataFrame, scenario: Dict) -> Dict:
    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    indicators = build_indicators(df_4h, riskoff_params)
    _, transitions = core_state_events(df_5m, df_4h, riskoff_params)
    instability = trailing_instability_flags(transitions)
    bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])

    systems = {}
    churn_rows = []
    window_rows = []
    for candidate in CANDIDATES:
        target, events = build_target_and_events(indicators, instability, candidate)
        core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
        combo = evaluate_combo(bundle, core_sim)
        systems[candidate.key] = {**combo, "target": target, "events": events}
        if scenario["name"] == "default":
            cycles = build_cycles(events)
            churn_rows.append(summarize_churn(cycles, candidate.key))
            window_rows.extend(build_window_table(cycles, candidate.key))
    return {
        "systems": systems,
        "instability": instability if scenario["name"] == "default" else None,
        "churn_rows": churn_rows,
        "window_rows": window_rows,
    }


def build_annual_table(default_systems: Dict) -> pd.DataFrame:
    rows = []
    for start in ANNUAL_STARTS:
        for candidate in CANDIDATES:
            system = default_systems[candidate.key]
            sub_eq = system["combo_equity"][system["combo_equity"].index >= start]
            sub_ex = system["combo_exposure"][system["combo_exposure"].index >= start]
            if sub_eq.empty:
                continue
            metrics = annual_start_metrics(sub_eq, sub_ex)
            rows.append({"start": start.date().isoformat(), "candidate": candidate.key, "label": candidate.label, **metrics})
    return pd.DataFrame(rows)


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
    fig.update_layout(template="plotly_white", height=1100, hovermode="x unified", title="State-Aware Hybrid Final Audition")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Underwater %", row=2, col=1)
    fig.update_yaxes(title_text="High churn", tickmode="array", tickvals=[0, 1], ticktext=["off", "on"], row=3, col=1)
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def write_report(report: Dict, summary_df: pd.DataFrame, churn_df: pd.DataFrame, annual_df: pd.DataFrame, window_df: pd.DataFrame) -> None:
    default_df = summary_df[summary_df["scenario"] == "default"]
    stress_df = summary_df[summary_df["scenario"] == "stress"]
    harsh_df = summary_df[summary_df["scenario"] == "harsh_friction"]
    base = default_df[default_df["candidate"] == "baseline_close3"].iloc[0]
    ref = default_df[default_df["candidate"] == "state_aware_highly_unstable_strict"].iloc[0]
    chall = default_df[default_df["candidate"] == "state_aware_hybrid_strict_and_breakout4"].iloc[0]

    def delta(df: pd.DataFrame, key_a: str, key_b: str) -> Dict[str, float]:
        a = df[df["candidate"] == key_a].iloc[0]
        b = df[df["candidate"] == key_b].iloc[0]
        return {
            "return_pct": float(a["return_pct"] - b["return_pct"]),
            "calmar": float(a["calmar"] - b["calmar"]),
            "maxdd_pct": float(a["maxdd_pct"] - b["maxdd_pct"]),
        }

    d0 = delta(default_df, "state_aware_hybrid_strict_and_breakout4", "baseline_close3")
    ds = delta(stress_df, "state_aware_hybrid_strict_and_breakout4", "baseline_close3")
    dh = delta(harsh_df, "state_aware_hybrid_strict_and_breakout4", "baseline_close3")

    if not annual_df.empty:
        base_ann = annual_df[annual_df["candidate"] == "baseline_close3"].set_index("start").add_suffix("_base")
        ref_ann = annual_df[annual_df["candidate"] == "state_aware_highly_unstable_strict"].set_index("start").add_suffix("_ref")
        chall_ann = annual_df[annual_df["candidate"] == "state_aware_hybrid_strict_and_breakout4"].set_index("start").add_suffix("_chall")
        ann_merge = chall_ann.join(base_ann).join(ref_ann)
        ann_rows = []
        for start, row in ann_merge.iterrows():
            ann_rows.append(
                {
                    "start": start,
                    "d_return_vs_base": row["return_pct_chall"] - row["return_pct_base"],
                    "d_calmar_vs_base": row["calmar_chall"] - row["calmar_base"],
                    "d_maxdd_vs_base": row["maxdd_pct_chall"] - row["maxdd_pct_base"],
                    "d_return_vs_ref": row["return_pct_chall"] - row["return_pct_ref"],
                    "d_calmar_vs_ref": row["calmar_chall"] - row["calmar_ref"],
                    "d_maxdd_vs_ref": row["maxdd_pct_chall"] - row["maxdd_pct_ref"],
                }
            )
        ann_comp = pd.DataFrame(ann_rows)
    else:
        ann_comp = pd.DataFrame()

    lines: List[str] = [
        "# State-Aware Hybrid Final Audition",
        "",
        "## Scope",
        "",
        "- Mainline reference: `baseline close3`.",
        "- Standing reference: `state-aware strict`.",
        "- Challenger: `high churn -> strict AND breakout_4`.",
        "- Sell-side and `weekly_rsi30_hold` stay fixed.",
        "- Adoption framing: compare the challenger against both the mainline and the standing reference across `default`, `stress`, and `harsh_friction`.",
        "",
        "## Default",
        "",
        "| System | Return% | CAGR% | Sharpe | Calmar | MaxDD% | RecoveryDays | Worst3m | Worst6m | AvgTotalExp% | AvgCoreExp% | RiskOffActive% |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in CANDIDATES:
        row = report["default"]["systems"][candidate.key]
        lines.append(
            f"| {candidate.label} | {row['metrics']['TotalReturn_pct']:.2f} | {row['metrics']['CAGR_pct']:.2f} | {row['metrics']['Sharpe']:.3f} | "
            f"{row['metrics']['Calmar']:.3f} | {row['metrics']['MaxDD_pct']:.2f} | {row['path']['recovery_days_from_maxdd']:.1f} | "
            f"{row['path']['worst_3m_cluster_return_pct']:.2f} | {row['path']['worst_6m_cluster_return_pct']:.2f} | {row['avg_total_exposure_pct']:.2f} | "
            f"{row['avg_core_exposure_pct']:.2f} | {row['riskoff_active_ratio_pct']:.2f} |"
        )

    lines.extend([
        "",
        "## Stress / Harsh Delta Vs Mainline",
        "",
        "| Scenario | dReturn | dCalmar | dMaxDD |",
        "| --- | --- | --- | --- |",
        f"| Default | {d0['return_pct']:+.2f}pp | {d0['calmar']:+.3f} | {d0['maxdd_pct']:+.2f}pp |",
        f"| Stress | {ds['return_pct']:+.2f}pp | {ds['calmar']:+.3f} | {ds['maxdd_pct']:+.2f}pp |",
        f"| Harsh friction | {dh['return_pct']:+.2f}pp | {dh['calmar']:+.3f} | {dh['maxdd_pct']:+.2f}pp |",
        "",
        "## Default Churn Audit",
        "",
        "| System | Full RE | RE->next FLAT Median Days | Quick re-FLAT 14d | Quick re-FLAT 30d | High-Churn RE | High-Churn Median Days | High-Churn Quick 14d | High-Churn Quick 30d |",
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

    lines.extend(["## Annual Starts", "", "| Start | dReturn vs Mainline | dCalmar vs Mainline | dMaxDD vs Mainline | dReturn vs Strict | dCalmar vs Strict | dMaxDD vs Strict |", "| --- | --- | --- | --- | --- | --- | --- |"])
    if not ann_comp.empty:
        for _, row in ann_comp.iterrows():
            lines.append(
                f"| {row['start']} | {row['d_return_vs_base']:+.2f}pp | {row['d_calmar_vs_base']:+.3f} | {row['d_maxdd_vs_base']:+.2f}pp | "
                f"{row['d_return_vs_ref']:+.2f}pp | {row['d_calmar_vs_ref']:+.3f} | {row['d_maxdd_vs_ref']:+.2f}pp |"
            )

    positive_calmar_vs_base = int((ann_comp["d_calmar_vs_base"] > 0).sum()) if not ann_comp.empty else 0
    better_maxdd_vs_base = int((ann_comp["d_maxdd_vs_base"] > 0).sum()) if not ann_comp.empty else 0
    positive_calmar_vs_ref = int((ann_comp["d_calmar_vs_ref"] > 0).sum()) if not ann_comp.empty else 0
    better_maxdd_vs_ref = int((ann_comp["d_maxdd_vs_ref"] > 0).sum()) if not ann_comp.empty else 0

    lines.extend([
        "",
        "## Readout",
        "",
        f"- Standing reference: Return `{ref['return_pct']:.2f}%`, Calmar `{ref['calmar']:.3f}`, MaxDD `{ref['maxdd_pct']:.2f}%`.",
        f"- Challenger: Return `{chall['return_pct']:.2f}%`, Calmar `{chall['calmar']:.3f}`, MaxDD `{chall['maxdd_pct']:.2f}%`.",
        f"- Challenger vs standing reference in default: dReturn `{chall['return_pct'] - ref['return_pct']:+.2f}pp`, dCalmar `{chall['calmar'] - ref['calmar']:+.3f}`, dMaxDD `{chall['maxdd_pct'] - ref['maxdd_pct']:+.2f}pp`.",
        f"- Annual starts where challenger improves Calmar vs mainline: `{positive_calmar_vs_base}` / `{len(ann_comp)}`.",
        f"- Annual starts where challenger improves MaxDD vs mainline: `{better_maxdd_vs_base}` / `{len(ann_comp)}`.",
        f"- Annual starts where challenger improves Calmar vs strict: `{positive_calmar_vs_ref}` / `{len(ann_comp)}`.",
        f"- Annual starts where challenger improves MaxDD vs strict: `{better_maxdd_vs_ref}` / `{len(ann_comp)}`.",
        "- Promotion bar: the challenger should not only reduce churn, but also survive default / stress / harsh and keep that advantage credible across annual start offsets.",
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
                    "cagr_pct": combo["metrics"]["CAGR_pct"],
                    "sharpe": combo["metrics"]["Sharpe"],
                    "calmar": combo["metrics"]["Calmar"],
                    "maxdd_pct": combo["metrics"]["MaxDD_pct"],
                    "worst3m_pct": combo["path"]["worst_3m_cluster_return_pct"],
                    "worst6m_pct": combo["path"]["worst_6m_cluster_return_pct"],
                    "recovery_days": combo["path"]["recovery_days_from_maxdd"],
                }
            )

    summary_df = pd.DataFrame(summary_rows)
    churn_df = pd.DataFrame(report["default"]["churn_rows"])
    window_df = pd.DataFrame(report["default"]["window_rows"])
    annual_df = build_annual_table(report["default"]["systems"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    if not churn_df.empty:
        churn_df.to_csv(CHURN_CSV, index=False)
    if not window_df.empty:
        window_df.to_csv(WINDOWS_CSV, index=False)
    if not annual_df.empty:
        annual_df.to_csv(ANNUAL_CSV, index=False)
    write_plot(report["default"]["systems"], report["default"]["instability"])
    write_report(report, summary_df, churn_df, annual_df, window_df)
    payload = {
        "summary": summary_df.to_dict(orient="records"),
        "default_churn": churn_df.to_dict(orient="records"),
        "default_windows": window_df.to_dict(orient="records"),
        "annual_starts": annual_df.to_dict(orient="records"),
    }
    SUMMARY_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"audit": AUDIT_MD.name, "summary_csv": SUMMARY_CSV.name, "churn_csv": CHURN_CSV.name, "annual_csv": ANNUAL_CSV.name, "plot": PLOTS_HTML.name}, ensure_ascii=False))


if __name__ == "__main__":
    main()
