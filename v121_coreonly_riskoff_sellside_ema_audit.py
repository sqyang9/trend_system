#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final sell-side EMA replacement audit for core-only Risk-Off overlays."""

from __future__ import annotations

import json
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
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v92_const1x_deployment_audit import loss_cluster_diagnostics, path_diagnostics
from v95_range_rotation_mean_reversion_audit import make_range_rotation_params
from v96_range_rotation_mean_reversion_s3_audit import scenario_systems
from v116_fullstack_riskoff_adoption_audit import SCENARIOS
from v90_riskoff_promotion_v2 import build_indicator_cache


OUT_DIR = Path("official_mainline")
AUDIT_MD = OUT_DIR / "COREONLY_RISKOFF_SELLSIDE_EMA_AUDIT.md"
REPORT_JSON = Path("coreonly_riskoff_sellside_ema_audit.json")
PLOTS_HTML = OUT_DIR / "COREONLY_RISKOFF_SELLSIDE_EMA_PLOTS.html"


CANDIDATES: List[Dict] = [
    {"name": "WRSI14_30_EMA220", "label": "Formal + WRSI14_30_EMA220", "reentry_family": "weekly_rsi_hold", "rsi_period": 14, "threshold": 30.0, "ema_len": 220},
    {"name": "WRSI14_30_EMA250", "label": "Formal + WRSI14_30_EMA250", "reentry_family": "weekly_rsi_hold", "rsi_period": 14, "threshold": 30.0, "ema_len": 250},
    {"name": "H4RSI14_10_EMA220", "label": "Formal + H4RSI14_10_EMA220", "reentry_family": "h4_rsi_hold", "rsi_period": 14, "threshold": 10.0, "ema_len": 220},
    {"name": "H4RSI14_10_EMA200", "label": "Formal + H4RSI14_10_EMA200", "reentry_family": "h4_rsi_hold", "rsi_period": 14, "threshold": 10.0, "ema_len": 200},
]


def compute_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def build_indicators(df_4h: pd.DataFrame, params, ema_len: int) -> pd.DataFrame:
    base = build_indicator_cache(df_4h, params, [ema_len], ensure_datetime(df_4h)["timestamp"])[ema_len].copy()
    out = base.copy()
    weekly_close = out["close"].resample("W-SUN").last()
    out["weekly_rsi_14"] = compute_rsi(weekly_close, 14).reindex(out.index, method="ffill")
    out["h4_rsi_14"] = compute_rsi(out["close"].astype(float), 14)
    return out


def build_target(indicators: pd.DataFrame, spec: Dict) -> pd.Series:
    bearish = (indicators["close"] < indicators["ema"]) & (indicators["ema_slope"] < 0)
    close_confirm = indicators["close"] > indicators["ema"]
    if spec["reentry_family"] == "weekly_rsi_hold":
        trigger = (indicators["weekly_rsi_14"] <= float(spec["threshold"])).fillna(False)
    elif spec["reentry_family"] == "h4_rsi_hold":
        trigger = (indicators["h4_rsi_14"] <= float(spec["threshold"])).fillna(False)
    else:
        raise ValueError(spec["reentry_family"])

    weights = []
    state = "normal"
    bear_count = 0
    close_count = 0
    for is_bear, is_close, trig in zip(bearish.fillna(False).tolist(), close_confirm.fillna(False).tolist(), trigger.tolist()):
        bear_count = bear_count + 1 if is_bear else 0
        close_count = close_count + 1 if is_close else 0
        if state == "normal":
            if bear_count >= 2:
                state = "flat"
            elif bear_count == 1:
                state = "soft_off"
        elif state == "soft_off":
            if bear_count >= 2:
                state = "flat"
            elif bear_count == 0:
                state = "normal"
        elif state == "flat":
            if close_count >= 3:
                state = "normal"
            elif trig:
                state = "override_hold"
                bear_count = 0
                close_count = 0
        elif state == "override_hold":
            if close_count >= 3:
                state = "normal"
        weights.append(1.0 if state in {"normal", "override_hold"} else 0.5 if state == "soft_off" else 0.0)
    return pd.Series(weights, index=indicators.index, dtype=float)


def path_bundle(equity: pd.Series) -> Dict:
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


def combine_core_only(formal_payload: Dict, core_sim: Dict) -> Dict:
    const1x = formal_payload["systems"]["Core+ConstAddOn[1.00x]"]
    formal_combo = formal_payload["systems"]["Core+ConstAddOn[1.00x]+RangeRotation"]
    candidate_sleeve = formal_payload["candidate_sleeve"]
    idx = formal_combo["combo_equity"].index

    sleeve1_equity = const1x["sleeve"]["equity"].reindex(idx).ffill().bfill().astype(float)
    sleeve1_weight = const1x["sleeve"]["weight"].reindex(idx).fillna(0.0).astype(float)
    sleeve2_equity = candidate_sleeve["equity"].reindex(idx).ffill().bfill().astype(float)
    sleeve2_weight = candidate_sleeve["weight"].reindex(idx).fillna(0.0).astype(float)
    init_equity = float(sleeve1_equity.iloc[0])

    core_equity = core_sim["equity"]["equity"].reindex(idx).ffill().bfill().astype(float)
    core_exposure = core_sim["equity"]["exposure"].reindex(idx).ffill().bfill().fillna(1.0).astype(float)

    combo_equity = (core_equity + (sleeve1_equity - init_equity) + (sleeve2_equity - init_equity)).ffill().bfill().astype(float)
    combo_exposure = (core_exposure + sleeve1_weight + sleeve2_weight).ffill().bfill().astype(float)
    metrics = extended_metrics({"combo_equity": combo_equity, "combo_metrics": compute_metrics(combo_equity, combo_exposure)})
    return {
        "combo_equity": combo_equity,
        "combo_exposure": combo_exposure,
        "metrics": metrics,
        "path": path_bundle(combo_equity),
        "avg_total_exposure_pct": float(combo_exposure.mean() * 100.0),
        "peak_total_exposure_pct": float(combo_exposure.max() * 100.0),
        "avg_core_exposure_pct": float(core_exposure.mean() * 100.0),
        "riskoff_active_ratio_pct": float((core_exposure < 0.9999).mean() * 100.0),
        "sleeve1_active_ratio_pct": float((sleeve1_weight > 1e-9).mean() * 100.0),
        "sleeve2_active_ratio_pct": float((sleeve2_weight > 1e-9).mean() * 100.0),
        "causality": core_sim["causality"],
    }


def evaluate_scenario(df_5m, df_4h, scenario: Dict) -> Dict:
    formal_params = formal_current_research_optimal(**scenario["formal_overrides"])
    range_params = make_range_rotation_params(**scenario["formal_overrides"])
    formal_payload = scenario_systems(formal_params, range_params, df_5m, df_4h)
    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])

    formal_sys = formal_payload["systems"]["Core+ConstAddOn[1.00x]+RangeRotation"]
    rows = {
        "FormalPortfolio": {
            "combo_equity": formal_sys["combo_equity"].astype(float),
            "combo_exposure": formal_sys["combo_exposure"].astype(float),
            "metrics": extended_metrics({"combo_equity": formal_sys["combo_equity"], "combo_metrics": formal_sys["combo_metrics"]}),
            "path": path_bundle(formal_sys["combo_equity"]),
            "avg_total_exposure_pct": float(formal_sys["combo_exposure"].mean() * 100.0),
            "peak_total_exposure_pct": float(formal_sys["combo_exposure"].max() * 100.0),
            "avg_core_exposure_pct": 100.0,
            "riskoff_active_ratio_pct": 0.0,
            "sleeve1_active_ratio_pct": float((formal_payload["systems"]["Core+ConstAddOn[1.00x]"]["sleeve"]["weight"] > 1e-9).mean() * 100.0),
            "sleeve2_active_ratio_pct": float((formal_payload["candidate_sleeve"]["weight"] > 1e-9).mean() * 100.0),
        }
    }

    indicator_cache = {ema_len: build_indicators(df_4h, riskoff_params, ema_len) for ema_len in sorted({c["ema_len"] for c in CANDIDATES})}
    for spec in CANDIDATES:
        target = build_target(indicator_cache[spec["ema_len"]], spec)
        core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
        rows[spec["name"]] = combine_core_only(formal_payload, core_sim)
        rows[spec["name"]]["spec"] = spec
    return rows


def write_report(report: Dict) -> None:
    default = report["default"]
    stress = report["stress"]
    harsh = report["harsh_friction"]
    order = ["FormalPortfolio"] + [c["name"] for c in CANDIDATES]
    labels = {"FormalPortfolio": "Formal"} | {c["name"]: c["label"] for c in CANDIDATES}
    lines = [
        "# Core-Only Risk-Off Sell-Side EMA Audit",
        "",
        "- Scope: re-entry fixed near the current incumbents, then compare sell-side EMA replacement value.",
        "- Architecture fixed: `Formal Portfolio = Core + ConstAddOn[1.00x] + RangeRotation` with core-only Risk-Off overlay.",
        "",
        "## Default",
        "",
        "| System | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgTotalExp% | AvgCoreExp% | RiskOffActive% |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key in order:
        row = default[key]
        lines.append(
            f"| {labels[key]} | {row['metrics']['TotalReturn_pct']:.2f} | {row['metrics']['Calmar']:.3f} | {row['metrics']['MaxDD_pct']:.2f} | "
            f"{row['path']['worst_3m_cluster_return_pct']:.2f} | {row['path']['worst_6m_cluster_return_pct']:.2f} | {row['path']['recovery_days_from_maxdd']:.1f} | "
            f"{row['avg_total_exposure_pct']:.2f} | {row['avg_core_exposure_pct']:.2f} | {row['riskoff_active_ratio_pct']:.2f} |"
        )
    lines.extend([
        "",
        "## Stress / Harsh Delta Vs Formal",
        "",
        "| System | Stress dReturn | Stress dCalmar | Stress dMaxDD | Harsh dReturn | Harsh dCalmar | Harsh dMaxDD |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for key in order[1:]:
        s = stress[key]["metrics"]
        sb = stress["FormalPortfolio"]["metrics"]
        h = harsh[key]["metrics"]
        hb = harsh["FormalPortfolio"]["metrics"]
        lines.append(
            f"| {labels[key]} | {s['TotalReturn_pct'] - sb['TotalReturn_pct']:+.2f}pp | {s['Calmar'] - sb['Calmar']:+.3f} | {s['MaxDD_pct'] - sb['MaxDD_pct']:+.2f}pp | "
            f"{h['TotalReturn_pct'] - hb['TotalReturn_pct']:+.2f}pp | {h['Calmar'] - hb['Calmar']:+.3f} | {h['MaxDD_pct'] - hb['MaxDD_pct']:+.2f}pp |"
        )
    lines.extend([
        "",
        "## Readout",
        "",
        "- This audit answers whether the incumbent EMA220 sell-side should survive once re-entry is fixed.",
        "- Weekly branch compare: `WRSI14_30_EMA220` vs `WRSI14_30_EMA250`.",
        "- 4h branch compare: `H4RSI14_10_EMA220` vs `H4RSI14_10_EMA200`.",
    ])
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_plot(default: Dict) -> None:
    order = [
        ("Formal", default["FormalPortfolio"]["combo_equity"], "#0f172a"),
        ("WRSI14_30_EMA220", default["WRSI14_30_EMA220"]["combo_equity"], "#059669"),
        ("WRSI14_30_EMA250", default["WRSI14_30_EMA250"]["combo_equity"], "#16a34a"),
        ("H4RSI14_10_EMA220", default["H4RSI14_10_EMA220"]["combo_equity"], "#dc2626"),
        ("H4RSI14_10_EMA200", default["H4RSI14_10_EMA200"]["combo_equity"], "#7c3aed"),
    ]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.62, 0.38], subplot_titles=("Equity Curves", "Underwater Curves"))
    for label, series, color in order:
        uw = (series / series.cummax() - 1.0) * 100.0
        fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=label, line=dict(width=2.0, color=color)), row=1, col=1)
        fig.add_trace(go.Scatter(x=uw.index, y=uw, mode="lines", name=f"{label} UW", line=dict(width=1.2, color=color), showlegend=False), row=2, col=1)
    fig.update_layout(template="plotly_white", height=980, hovermode="x unified", title="Core-Only Risk-Off Sell-Side EMA Audit")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Underwater %", row=2, col=1)
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def main():
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    report = {}
    for scenario in SCENARIOS:
        report[scenario["name"]] = evaluate_scenario(df_5m, df_4h, scenario)

    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    write_report(report)
    write_plot(report["default"])
    print(json.dumps({"audit": AUDIT_MD.name, "plots": PLOTS_HTML.name, "json": REPORT_JSON.name}, ensure_ascii=False))


if __name__ == "__main__":
    main()
