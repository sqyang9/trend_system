#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Screen core-only vs full-stack Risk-Off semantics on top of the formal portfolio."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_addon_grading_study import constant_weight_plan, current_research_optimal as formal_current_research_optimal, prepare_base_run
from v90_asset_management_system_aligned import compute_metrics, current_research_optimal as riskoff_current_research_optimal
from v90_riskoff_promotion_validation import load_overlay
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v92_const1x_deployment_audit import loss_cluster_diagnostics, path_diagnostics
from v95_range_rotation_mean_reversion_audit import make_range_rotation_params, run_range_rotation_candidate
from v96_range_rotation_mean_reversion_s3_audit import scenario_systems
from v110_riskoff_lowvalue_reentry_candidates import build_bundle as build_riskoff_bundle
from v116_fullstack_riskoff_adoption_audit import SCENARIOS, fullstack_combo


REPORT_MD = Path("RISKOFF_STRUCTURE_SCREEN.md")
REPORT_JSON = Path("riskoff_structure_screen.json")
PLOTS_HTML = Path("RISKOFF_STRUCTURE_SCREEN_PLOTS.html")
CANDIDATES = ["RO_LOWVALUE_WEEKLY_RSI30_HOLD", "RO_LOWVALUE_4H_RSI10_HOLD"]


def path_bundle(equity):
    pdx = path_diagnostics(equity)
    clusters = loss_cluster_diagnostics(equity)
    maxdd_episode = pdx["worst_underwater_episodes"][0] if pdx["worst_underwater_episodes"] else None
    return {
        "worst_3m_cluster_return_pct": float(clusters["worst_3m_cluster_return_pct"]),
        "worst_6m_cluster_return_pct": float(clusters["worst_6m_cluster_return_pct"]),
        "recovery_days_from_maxdd": float(maxdd_episode["recovery_days_from_trough"]) if maxdd_episode is not None else 0.0,
    }


def combine_core_only(formal_payload: Dict, riskoff_bundle: Dict, candidate_name: str) -> Dict:
    const1x = formal_payload["systems"]["Core+ConstAddOn[1.00x]"]
    formal_combo = formal_payload["systems"]["Core+ConstAddOn[1.00x]+RangeRotation"]
    candidate_sleeve = formal_payload["candidate_sleeve"]
    idx = formal_combo["combo_equity"].index

    sleeve1_equity = const1x["sleeve"]["equity"].reindex(idx).ffill().bfill().astype(float)
    sleeve1_weight = const1x["sleeve"]["weight"].reindex(idx).fillna(0.0).astype(float)
    sleeve2_equity = candidate_sleeve["equity"].reindex(idx).ffill().bfill().astype(float)
    sleeve2_weight = candidate_sleeve["weight"].reindex(idx).fillna(0.0).astype(float)
    init_equity = float(sleeve1_equity.iloc[0])

    risk_core = riskoff_bundle["systems"][f"Core+AddOnOverlay+{candidate_name}"]["core"]
    core_equity = risk_core["equity"]["equity"].reindex(idx).ffill().bfill().astype(float)
    core_exposure = risk_core["equity"]["exposure"].reindex(idx).ffill().bfill().fillna(1.0).astype(float)

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
    }


def evaluate_scenario(df_5m, df_4h, overlay, scenario: Dict) -> Dict:
    formal_params = formal_current_research_optimal(**scenario["formal_overrides"])
    range_params = make_range_rotation_params(**scenario["formal_overrides"])
    formal_payload = scenario_systems(formal_params, range_params, df_5m, df_4h)
    base = prepare_base_run(df_5m, df_4h, formal_params)
    plan = constant_weight_plan(base["entries"], 1.0)
    rr_result = run_range_rotation_candidate(df_5m, df_4h, range_params)

    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    riskoff_bundle = build_riskoff_bundle(df_5m, df_4h, overlay, riskoff_params, riskoff_params.entry_execution_mode)

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
    for name in CANDIDATES:
        rows[f"CoreOnly+{name}"] = combine_core_only(formal_payload, riskoff_bundle, name)
        core_target = (riskoff_bundle["systems"][f"Core+AddOnOverlay+{name}"]["target"].astype(float) >= 0.9999).astype(float)
        rows[f"FullStack+{name}"] = fullstack_combo(df_4h, df_5m, formal_payload, plan, rr_result, core_target, riskoff_params)
    return rows


def write_report(report: Dict) -> None:
    default = report["default"]
    stress = report["stress"]
    formal = default["FormalPortfolio"]
    order = [
        "FormalPortfolio",
        "CoreOnly+RO_LOWVALUE_WEEKLY_RSI30_HOLD",
        "FullStack+RO_LOWVALUE_WEEKLY_RSI30_HOLD",
        "CoreOnly+RO_LOWVALUE_4H_RSI10_HOLD",
        "FullStack+RO_LOWVALUE_4H_RSI10_HOLD",
    ]
    lines = [
        "# Risk-Off Structure Screen",
        "",
        "- Purpose: screen `core-only Risk-Off` vs `full-stack cash-like Risk-Off` on the current formal portfolio.",
        "- Base architecture fixed: `Core + ConstAddOn[1.00x] + RangeRotation`.",
        "- Re-entry candidates fixed: `RO_LOWVALUE_WEEKLY_RSI30_HOLD`, `RO_LOWVALUE_4H_RSI10_HOLD`.",
        "",
        "## Default",
        "",
        "| System | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgTotalExp% | RiskOffActive% | S1Active% | S2Active% |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    labels = {
        "FormalPortfolio": "Formal",
        "CoreOnly+RO_LOWVALUE_WEEKLY_RSI30_HOLD": "CoreOnly + Weekly30",
        "FullStack+RO_LOWVALUE_WEEKLY_RSI30_HOLD": "FullStack + Weekly30",
        "CoreOnly+RO_LOWVALUE_4H_RSI10_HOLD": "CoreOnly + 4H10",
        "FullStack+RO_LOWVALUE_4H_RSI10_HOLD": "FullStack + 4H10",
    }
    for key in order:
        row = default[key]
        lines.append(
            f"| {labels[key]} | {row['metrics']['TotalReturn_pct']:.2f} | {row['metrics']['Calmar']:.3f} | {row['metrics']['MaxDD_pct']:.2f} | "
            f"{row['path']['worst_3m_cluster_return_pct']:.2f} | {row['path']['worst_6m_cluster_return_pct']:.2f} | "
            f"{row['path']['recovery_days_from_maxdd']:.1f} | {row['avg_total_exposure_pct']:.2f} | {row['riskoff_active_ratio_pct']:.2f} | "
            f"{row['sleeve1_active_ratio_pct']:.2f} | {row['sleeve2_active_ratio_pct']:.2f} |"
        )
    lines.extend([
        "",
        "## Stress Delta Vs Formal",
        "",
        "| System | dReturn | dCalmar | dMaxDD | dWorst3m | dWorst6m | dRecoveryDays |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    stress_formal = stress["FormalPortfolio"]
    for key in order[1:]:
        row = stress[key]
        lines.append(
            f"| {labels[key]} | {row['metrics']['TotalReturn_pct'] - stress_formal['metrics']['TotalReturn_pct']:+.2f}pp | "
            f"{row['metrics']['Calmar'] - stress_formal['metrics']['Calmar']:+.3f} | "
            f"{row['metrics']['MaxDD_pct'] - stress_formal['metrics']['MaxDD_pct']:+.2f}pp | "
            f"{row['path']['worst_3m_cluster_return_pct'] - stress_formal['path']['worst_3m_cluster_return_pct']:+.2f}pp | "
            f"{row['path']['worst_6m_cluster_return_pct'] - stress_formal['path']['worst_6m_cluster_return_pct']:+.2f}pp | "
            f"{row['path']['recovery_days_from_maxdd'] - stress_formal['path']['recovery_days_from_maxdd']:+.1f} |"
        )
    lines.extend([
        "",
        "## Structure Readout",
        "",
        "- If full-stack wins, the edge is coming from flattening the whole portfolio ecology, not just the core.",
        "- If core-only wins, the edge is mainly a core carry timing fix and sleeves should remain independent.",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_plot(default: Dict) -> None:
    order = [
        ("Formal", default["FormalPortfolio"]["combo_equity"], "#0f172a"),
        ("CoreOnly + Weekly30", default["CoreOnly+RO_LOWVALUE_WEEKLY_RSI30_HOLD"]["combo_equity"], "#2563eb"),
        ("FullStack + Weekly30", default["FullStack+RO_LOWVALUE_WEEKLY_RSI30_HOLD"]["combo_equity"], "#059669"),
        ("CoreOnly + 4H10", default["CoreOnly+RO_LOWVALUE_4H_RSI10_HOLD"]["combo_equity"], "#7c3aed"),
        ("FullStack + 4H10", default["FullStack+RO_LOWVALUE_4H_RSI10_HOLD"]["combo_equity"], "#dc2626"),
    ]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.62, 0.38], subplot_titles=("Equity", "Underwater"))
    for label, series, color in order:
        uw = (series / series.cummax() - 1.0) * 100.0
        fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=label, line=dict(color=color, width=2.0)), row=1, col=1)
        fig.add_trace(go.Scatter(x=uw.index, y=uw, mode="lines", name=f"{label} UW", line=dict(color=color, width=1.1), showlegend=False), row=2, col=1)
    fig.update_layout(template="plotly_white", height=980, hovermode="x unified", title="Risk-Off Structure Screen")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Underwater %", row=2, col=1)
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def main():
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    overlay = load_overlay()

    report = {}
    for scenario in SCENARIOS[:2]:
        report[scenario["name"]] = evaluate_scenario(df_5m, df_4h, overlay, scenario)

    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    write_report(report)
    write_plot(report["default"])
    print(json.dumps({"report": REPORT_MD.name, "plots": PLOTS_HTML.name, "json": REPORT_JSON.name}, ensure_ascii=False))


if __name__ == "__main__":
    main()
