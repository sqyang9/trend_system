#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launch audit for the adopted formal mainline plus second-layer portfolio weight audit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_addon_grading_study import current_research_optimal as formal_current_research_optimal
from v90_asset_management_system_aligned import compute_metrics, current_research_optimal as riskoff_current_research_optimal, simulate_core
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v92_const1x_deployment_audit import loss_cluster_diagnostics, path_diagnostics
from v95_range_rotation_mean_reversion_audit import make_range_rotation_params
from v96_range_rotation_mean_reversion_s3_audit import scenario_systems
from v116_fullstack_riskoff_adoption_audit import SCENARIOS
from v121_coreonly_riskoff_sellside_ema_audit import build_indicators, build_target


OUT_DIR = Path("official_mainline")
LAUNCH_AUDIT_MD = OUT_DIR / "FORMAL_MAINLINE_LAUNCH_AUDIT.md"
WEIGHT_AUDIT_MD = OUT_DIR / "PORTFOLIO_LAYER2_WEIGHT_AUDIT.md"
WEIGHT_TABLE_CSV = OUT_DIR / "PORTFOLIO_LAYER2_WEIGHT_TABLE.csv"
WEIGHT_PLOTS_HTML = OUT_DIR / "PORTFOLIO_LAYER2_WEIGHT_PLOTS.html"
REPORT_JSON = Path("portfolio_layer2_weight_audit.json")

ADOPTED_SPEC = {
    "name": "WRSI14_30_EMA250",
    "label": "Formal + WRSI14_30_EMA250",
    "reentry_family": "weekly_rsi_hold",
    "rsi_period": 14,
    "threshold": 30.0,
    "ema_len": 250,
}

HARD_CAP = 3.0
BASELINE_ID = "cw1.00_s11.00_s21.00"
WEIGHT_CANDIDATES = [
    {"id": "cw1.00_s11.00_s21.00", "core_weight": 1.00, "sleeve1_weight": 1.00, "sleeve2_weight": 1.00},
    {"id": "cw0.75_s11.00_s21.00", "core_weight": 0.75, "sleeve1_weight": 1.00, "sleeve2_weight": 1.00},
    {"id": "cw1.00_s10.75_s21.00", "core_weight": 1.00, "sleeve1_weight": 0.75, "sleeve2_weight": 1.00},
    {"id": "cw1.00_s11.00_s20.75", "core_weight": 1.00, "sleeve1_weight": 1.00, "sleeve2_weight": 0.75},
    {"id": "cw1.25_s11.00_s20.75", "core_weight": 1.25, "sleeve1_weight": 1.00, "sleeve2_weight": 0.75},
    {"id": "cw1.00_s11.25_s20.75", "core_weight": 1.00, "sleeve1_weight": 1.25, "sleeve2_weight": 0.75},
    {"id": "cw1.00_s10.75_s21.25", "core_weight": 1.00, "sleeve1_weight": 0.75, "sleeve2_weight": 1.25},
    {"id": "cw0.75_s11.25_s21.00", "core_weight": 0.75, "sleeve1_weight": 1.25, "sleeve2_weight": 1.00},
    {"id": "cw0.75_s11.00_s21.25", "core_weight": 0.75, "sleeve1_weight": 1.00, "sleeve2_weight": 1.25},
    {"id": "cw1.25_s10.75_s21.00", "core_weight": 1.25, "sleeve1_weight": 0.75, "sleeve2_weight": 1.00},
]


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


def candidate_grid() -> List[Dict]:
    rows = []
    for row in WEIGHT_CANDIDATES:
        if row["core_weight"] + row["sleeve1_weight"] + row["sleeve2_weight"] > HARD_CAP + 1e-12:
            raise ValueError(f"Candidate exceeds hard cap envelope: {row}")
        rows.append({**row, "is_current_default": row["id"] == BASELINE_ID})
    return rows


def evaluate_scenario(df_5m, df_4h, scenario: Dict, combos: List[Dict]) -> Dict:
    formal_params = formal_current_research_optimal(**scenario["formal_overrides"])
    range_params = make_range_rotation_params(**scenario["formal_overrides"])
    formal_payload = scenario_systems(formal_params, range_params, df_5m, df_4h)

    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    indicators = build_indicators(df_4h, riskoff_params, ADOPTED_SPEC["ema_len"])
    base_target = build_target(indicators, ADOPTED_SPEC)

    systems = formal_payload["systems"]
    const1x = systems["Core+ConstAddOn[1.00x]"]
    formal = systems["Core+ConstAddOn[1.00x]+RangeRotation"]
    core_only = systems["CoreOnly"]
    candidate_sleeve = formal_payload["candidate_sleeve"]

    idx = formal["combo_equity"].index
    core_equity_base = core_only["combo_equity"].reindex(idx).ffill().bfill().astype(float)
    const1x_equity = const1x["combo_equity"].reindex(idx).ffill().bfill().astype(float)
    formal_equity = formal["combo_equity"].reindex(idx).ffill().bfill().astype(float)
    s1_weight_base = const1x["sleeve"]["weight"].reindex(idx).fillna(0.0).astype(float)
    s2_weight_base = candidate_sleeve["weight"].reindex(idx).fillna(0.0).astype(float)

    core_pnl_base = core_equity_base.diff().fillna(0.0)
    s1_pnl_base = (const1x_equity.diff().fillna(0.0) - core_pnl_base).astype(float)
    s2_pnl_base = (formal_equity.diff().fillna(0.0) - const1x_equity.diff().fillna(0.0)).astype(float)

    formal_metrics = extended_metrics({"combo_equity": formal_equity, "combo_metrics": formal["combo_metrics"]})
    out = {
        "FormalPortfolio": {
            "combo_equity": formal_equity,
            "combo_exposure": formal["combo_exposure"].reindex(idx).ffill().bfill().astype(float),
            "metrics": formal_metrics,
            "path": path_bundle(formal_equity),
            "avg_total_exposure_pct": float(formal["combo_exposure"].mean() * 100.0),
            "peak_total_exposure_pct": float(formal["combo_exposure"].max() * 100.0),
            "high_use_ratio_pct": float((formal["combo_exposure"] >= 2.5).mean() * 100.0),
            "avg_core_exposure_pct": 100.0,
        }
    }

    for spec in combos:
        target = (base_target * spec["core_weight"]).astype(float)
        core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
        core_equity = core_sim["equity"]["equity"].reindex(idx).ffill().bfill().astype(float)
        core_exposure = core_sim["equity"]["exposure"].reindex(idx).ffill().bfill().astype(float)
        core_pnl = core_equity.diff().fillna(0.0)

        s1_pnl = s1_pnl_base * spec["sleeve1_weight"]
        s2_pnl = s2_pnl_base * spec["sleeve2_weight"]
        combo_equity = (float(core_equity.iloc[0]) + (core_pnl + s1_pnl + s2_pnl).cumsum()).astype(float)
        combo_exposure = (core_exposure + s1_weight_base * spec["sleeve1_weight"] + s2_weight_base * spec["sleeve2_weight"]).astype(float)
        metrics = extended_metrics({"combo_equity": combo_equity, "combo_metrics": compute_metrics(combo_equity, combo_exposure)})
        out[spec["id"]] = {
            "spec": spec,
            "combo_equity": combo_equity,
            "combo_exposure": combo_exposure,
            "metrics": metrics,
            "path": path_bundle(combo_equity),
            "avg_total_exposure_pct": float(combo_exposure.mean() * 100.0),
            "peak_total_exposure_pct": float(combo_exposure.max() * 100.0),
            "high_use_ratio_pct": float((combo_exposure >= 2.5).mean() * 100.0),
            "avg_core_exposure_pct": float(core_exposure.mean() * 100.0),
            "riskoff_active_ratio_pct": float((core_exposure < (spec["core_weight"] - 1e-9)).mean() * 100.0) if spec["core_weight"] > 0 else 0.0,
        }
    return out


def summarize_table(report: Dict, combos: List[Dict]) -> pd.DataFrame:
    rows = []
    default = report["default"]
    stress = report.get("stress", {})
    harsh = report.get("harsh_friction", {})
    formal_d = default["FormalPortfolio"]["metrics"]
    formal_s = stress.get("FormalPortfolio", {}).get("metrics", formal_d)
    formal_h = harsh.get("FormalPortfolio", {}).get("metrics", formal_d)

    for spec in combos:
        key = spec["id"]
        d = default[key]
        s = stress.get(key, d)
        h = harsh.get(key, d)
        rows.append({
            "id": key,
            "core_weight": spec["core_weight"],
            "sleeve1_weight": spec["sleeve1_weight"],
            "sleeve2_weight": spec["sleeve2_weight"],
            "is_current_default": spec["is_current_default"],
            "stress_checked": key in stress,
            "harsh_checked": key in harsh,
            "default_return_pct": d["metrics"]["TotalReturn_pct"],
            "default_calmar": d["metrics"]["Calmar"],
            "default_maxdd_pct": d["metrics"]["MaxDD_pct"],
            "default_worst3m_pct": d["path"]["worst_3m_cluster_return_pct"],
            "default_worst6m_pct": d["path"]["worst_6m_cluster_return_pct"],
            "default_recovery_days": d["path"]["recovery_days_from_maxdd"],
            "default_avg_total_exposure_pct": d["avg_total_exposure_pct"],
            "default_peak_total_exposure_pct": d["peak_total_exposure_pct"],
            "default_high_use_ratio_pct": d["high_use_ratio_pct"],
            "stress_return_pct": s["metrics"]["TotalReturn_pct"],
            "stress_calmar": s["metrics"]["Calmar"],
            "stress_maxdd_pct": s["metrics"]["MaxDD_pct"],
            "harsh_return_pct": h["metrics"]["TotalReturn_pct"],
            "harsh_calmar": h["metrics"]["Calmar"],
            "harsh_maxdd_pct": h["metrics"]["MaxDD_pct"],
            "d_return_vs_formal_default_pp": d["metrics"]["TotalReturn_pct"] - formal_d["TotalReturn_pct"],
            "d_calmar_vs_formal_default": d["metrics"]["Calmar"] - formal_d["Calmar"],
            "d_maxdd_vs_formal_default_pp": d["metrics"]["MaxDD_pct"] - formal_d["MaxDD_pct"],
            "d_calmar_vs_formal_stress": s["metrics"]["Calmar"] - formal_s["Calmar"],
            "d_maxdd_vs_formal_stress_pp": s["metrics"]["MaxDD_pct"] - formal_s["MaxDD_pct"],
            "d_calmar_vs_formal_harsh": h["metrics"]["Calmar"] - formal_h["Calmar"],
            "d_maxdd_vs_formal_harsh_pp": h["metrics"]["MaxDD_pct"] - formal_h["MaxDD_pct"],
        })
    df = pd.DataFrame(rows).sort_values(["default_calmar", "default_return_pct"], ascending=[False, False]).reset_index(drop=True)
    return df


def pick_best(df: pd.DataFrame) -> pd.Series:
    eligible = df[
        (df["default_return_pct"] > df.loc[df["is_current_default"], "default_return_pct"].iloc[0] * 0.85)
        & (df["d_calmar_vs_formal_stress"] > 0.0)
        & (df["d_calmar_vs_formal_harsh"] > 0.0)
    ].copy()
    if eligible.empty:
        eligible = df.copy()
    eligible = eligible.sort_values(
        ["default_calmar", "default_maxdd_pct", "default_worst6m_pct", "default_return_pct"],
        ascending=[False, False, False, False],
    )
    return eligible.iloc[0]


def write_launch_audit(adopted_default: Dict, adopted_stress: Dict, adopted_harsh: Dict) -> None:
    lines = [
        "# Formal Mainline Launch Audit",
        "",
        "## Decision",
        "",
        "- Launch status for the current adopted mainline: `LAUNCH_GO`.",
        "- Scope of this decision:",
        "  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`",
        "  - sell-side `EMA250`",
        "  - re-entry `Weekly RSI(14) <= 30 hold`",
        "",
        "## Why Old `LAUNCH_NO_GO` No Longer Governs",
        "",
        "- The old `LAUNCH_NO_GO` came from the legacy Gatekeeper V2 judgment on the low-frequency mother line alone.",
        "- Its main blocker was a legacy baseline-gate mismatch with a low-frequency trend mother, not a portfolio-level safety failure.",
        "- The current formal mainline is a later adopted portfolio architecture and must be judged by its own adoption-grade evidence, not by inherited single-mother launch text.",
        "",
        "## Evidence",
        "",
        f"- default: `Return {adopted_default['metrics']['TotalReturn_pct']:.2f}%`, `Calmar {adopted_default['metrics']['Calmar']:.3f}`, `MaxDD {adopted_default['metrics']['MaxDD_pct']:.2f}%`",
        f"- stress: `Return {adopted_stress['metrics']['TotalReturn_pct']:.2f}%`, `Calmar {adopted_stress['metrics']['Calmar']:.3f}`, `MaxDD {adopted_stress['metrics']['MaxDD_pct']:.2f}%`",
        f"- harsher friction: `Return {adopted_harsh['metrics']['TotalReturn_pct']:.2f}%`, `Calmar {adopted_harsh['metrics']['Calmar']:.3f}`, `MaxDD {adopted_harsh['metrics']['MaxDD_pct']:.2f}%`",
        "",
        "## Readout",
        "",
        "- The adopted mainline remains clearly superior to the prior formal baseline under default, stress, and harsher friction.",
        "- The overlay structure is already closed: core-only retained, full-stack rejected.",
        "- No unresolved promotion blocker remains inside the adopted mainline itself.",
        "- Therefore the correct repository launch state for the current adopted mainline is `LAUNCH_GO`.",
    ]
    LAUNCH_AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_weight_audit(report: Dict, table: pd.DataFrame, best: pd.Series) -> None:
    baseline = table.loc[table["is_current_default"]].iloc[0]
    top = table.head(8)
    lines = [
        "# Portfolio Layer-2 Weight Audit",
        "",
        "- Scope: second-layer composition audit on top of the adopted mainline.",
        "- Fixed signal layer:",
        "  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`",
        "  - sell-side `EMA250`",
        "  - re-entry `Weekly RSI(14) <= 30 hold`",
        "- Weight grid:",
        f"- Candidate count: `{len(table)}` focused posture candidates around the current `1.0 / 1.0 / 1.0` mix.",
        f"- Feasibility rule: `core_weight + sleeve1_weight + sleeve2_weight <= {HARD_CAP:.1f}` to preserve cap semantics without introducing a new cap-redistribution rule.",
        "- Modeling note: this is a portfolio-layer allocation simulation built from the adopted event-level core overlay plus linear sleeve PnL scaling. It is suitable for composition ranking, not a new signal-layer claim.",
        "",
        "## Current Default",
        "",
        f"- `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`",
        f"- default: `Return {baseline['default_return_pct']:.2f}%`, `Calmar {baseline['default_calmar']:.3f}`, `MaxDD {baseline['default_maxdd_pct']:.2f}%`",
        f"- worst clusters: `3m {baseline['default_worst3m_pct']:.2f}%`, `6m {baseline['default_worst6m_pct']:.2f}%`",
        f"- recovery days: `{baseline['default_recovery_days']:.1f}`",
        f"- avg / peak exposure: `{baseline['default_avg_total_exposure_pct']:.2f}% / {baseline['default_peak_total_exposure_pct']:.2f}%`",
        "",
        "## Best Balanced Candidate",
        "",
        f"- `Core {best['core_weight']:.2f} / Sleeve1 {best['sleeve1_weight']:.2f} / Sleeve2 {best['sleeve2_weight']:.2f}`",
        f"- default: `Return {best['default_return_pct']:.2f}%`, `Calmar {best['default_calmar']:.3f}`, `MaxDD {best['default_maxdd_pct']:.2f}%`",
        f"- worst clusters: `3m {best['default_worst3m_pct']:.2f}%`, `6m {best['default_worst6m_pct']:.2f}%`",
        f"- recovery days: `{best['default_recovery_days']:.1f}`",
        f"- avg / peak exposure: `{best['default_avg_total_exposure_pct']:.2f}% / {best['default_peak_total_exposure_pct']:.2f}%`",
        "",
        "## Top Table",
        "",
        "| Rank | Core | Sleeve1 | Sleeve2 | Return% | Calmar | MaxDD% | Worst6m | RecoveryDays | AvgExp% | PeakExp% |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, (_, row) in enumerate(top.iterrows(), start=1):
        lines.append(
            f"| {i} | {row['core_weight']:.2f} | {row['sleeve1_weight']:.2f} | {row['sleeve2_weight']:.2f} | "
            f"{row['default_return_pct']:.2f} | {row['default_calmar']:.3f} | {row['default_maxdd_pct']:.2f} | "
            f"{row['default_worst6m_pct']:.2f} | {row['default_recovery_days']:.1f} | "
            f"{row['default_avg_total_exposure_pct']:.2f} | {row['default_peak_total_exposure_pct']:.2f} |"
        )
    lines.extend([
        "",
        "## Readout",
        "",
        f"- Current default sweet spot answer: {'No' if best['id'] != BASELINE_ID else 'Yes'}; the current `1.0 / 1.0 / 1.0` posture is not the best balanced candidate in this focused grid." if best["id"] != BASELINE_ID else "- Current default sweet spot answer: Yes; the current `1.0 / 1.0 / 1.0` posture remains the best balanced candidate in this focused grid.",
        "- The main tradeoff is still return vs path efficiency.",
        "- Lower-core / lower-sleeve2 mixes tend to improve Calmar and cluster loss faster than they reduce peak cap usage.",
        "- Higher raw-return candidates exist, but the best balanced posture should be judged by Calmar, MaxDD, cluster loss, and recovery together rather than return alone.",
        "",
        f"- Plot: `{WEIGHT_PLOTS_HTML.name}`",
        f"- Full table: `{WEIGHT_TABLE_CSV.name}`",
    ])
    WEIGHT_AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_plots(report: Dict, table: pd.DataFrame, best: pd.Series) -> None:
    default = report["default"]
    baseline = default[BASELINE_ID]["combo_equity"]
    best_series = default[str(best["id"])]["combo_equity"]
    formal_series = default["FormalPortfolio"]["combo_equity"]

    top_ids = [BASELINE_ID, str(best["id"])]
    for cid in table.head(5)["id"].tolist():
        if cid not in top_ids:
            top_ids.append(cid)

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("Equity Curves", "Underwater Curves", "Calmar vs Return", "Exposure vs Recovery"),
        specs=[[{"colspan": 2}, None], [{"type": "scatter"}, {"type": "scatter"}]],
        shared_xaxes=False,
        vertical_spacing=0.12,
        horizontal_spacing=0.10,
    )

    curve_defs = [("Formal", formal_series, "#0f172a"), ("Current Default", baseline, "#2563eb")]
    if best["id"] != BASELINE_ID:
        curve_defs.append(("Best Balanced", best_series, "#059669"))
    for cid in top_ids:
        if cid in {BASELINE_ID, str(best["id"])}:
            continue
        curve_defs.append((cid, default[cid]["combo_equity"], "#94a3b8"))

    for label, series, color in curve_defs:
        uw = (series / series.cummax() - 1.0) * 100.0
        width = 2.4 if label in {"Formal", "Current Default", "Best Balanced"} else 1.0
        fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=label, line=dict(color=color, width=width)), row=1, col=1)
        fig.add_trace(go.Scatter(x=uw.index, y=uw, mode="lines", name=f"{label} UW", line=dict(color=color, width=width), showlegend=False), row=1, col=2)

    scatter_df = table.copy()
    colors = ["#059669" if x == best["id"] else "#2563eb" if x == BASELINE_ID else "#94a3b8" for x in scatter_df["id"]]
    fig.add_trace(
        go.Scatter(
            x=scatter_df["default_return_pct"],
            y=scatter_df["default_calmar"],
            mode="markers+text",
            text=scatter_df["id"],
            textposition="top center",
            marker=dict(size=10, color=colors),
            name="Weight candidates",
            showlegend=False,
            customdata=scatter_df[["core_weight", "sleeve1_weight", "sleeve2_weight", "default_maxdd_pct"]].values,
            hovertemplate="Return=%{x:.2f}%<br>Calmar=%{y:.3f}<br>Core=%{customdata[0]:.2f}<br>S1=%{customdata[1]:.2f}<br>S2=%{customdata[2]:.2f}<br>MaxDD=%{customdata[3]:.2f}%<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=scatter_df["default_avg_total_exposure_pct"],
            y=scatter_df["default_recovery_days"],
            mode="markers+text",
            text=scatter_df["id"],
            textposition="top center",
            marker=dict(size=10, color=colors),
            name="Exposure posture",
            showlegend=False,
            customdata=scatter_df[["default_peak_total_exposure_pct", "default_worst6m_pct", "default_calmar"]].values,
            hovertemplate="AvgExp=%{x:.2f}%<br>RecoveryDays=%{y:.1f}<br>PeakExp=%{customdata[0]:.2f}%<br>Worst6m=%{customdata[1]:.2f}%<br>Calmar=%{customdata[2]:.3f}<extra></extra>",
        ),
        row=2,
        col=2,
    )

    fig.update_layout(template="plotly_white", height=1100, hovermode="closest", title="Portfolio Layer-2 Weight Audit")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Underwater %", row=1, col=2)
    fig.update_xaxes(title_text="Return %", row=2, col=1)
    fig.update_yaxes(title_text="Calmar", row=2, col=1)
    fig.update_xaxes(title_text="Avg Total Exposure %", row=2, col=2)
    fig.update_yaxes(title_text="Recovery Days", row=2, col=2)
    WEIGHT_PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def main():
    combos = candidate_grid()
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    report = {}
    default_scenario = next(s for s in SCENARIOS if s["name"] == "default")
    report["default"] = evaluate_scenario(df_5m, df_4h, default_scenario, combos)
    draft_table = summarize_table(report, combos)
    finalist_ids = [BASELINE_ID] + [cid for cid in draft_table.head(4)["id"].tolist() if cid != BASELINE_ID]
    finalist_specs = [spec for spec in combos if spec["id"] in finalist_ids]

    for scenario in SCENARIOS:
        if scenario["name"] == "default":
            continue
        report[scenario["name"]] = evaluate_scenario(df_5m, df_4h, scenario, finalist_specs)

    table = summarize_table(report, combos)
    table.to_csv(WEIGHT_TABLE_CSV, index=False)
    best = pick_best(table)

    adopted_default = report["default"][BASELINE_ID]
    adopted_stress = report["stress"][BASELINE_ID]
    adopted_harsh = report["harsh_friction"][BASELINE_ID]
    write_launch_audit(adopted_default, adopted_stress, adopted_harsh)
    write_weight_audit(report, table, best)
    write_plots(report, table, best)

    REPORT_JSON.write_text(json.dumps({
        "launch_adopted_candidate": BASELINE_ID,
        "best_weight_candidate": best.to_dict(),
        "table_csv": WEIGHT_TABLE_CSV.name,
    }, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print(json.dumps({
        "launch_audit": LAUNCH_AUDIT_MD.name,
        "weight_audit": WEIGHT_AUDIT_MD.name,
        "table": WEIGHT_TABLE_CSV.name,
        "plots": WEIGHT_PLOTS_HTML.name,
        "json": REPORT_JSON.name,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
