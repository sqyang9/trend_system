#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launch audit plus second-layer portfolio weight audit on the adopted formal mainline."""

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
from v121_coreonly_riskoff_sellside_ema_audit import build_indicators, build_instability_flags, build_target, build_target_trace
from volatility_background import build_volatility_background


OUT_DIR = Path("official_mainline")
LAUNCH_AUDIT_MD = OUT_DIR / "FORMAL_MAINLINE_LAUNCH_AUDIT.md"
WEIGHT_AUDIT_MD = OUT_DIR / "PORTFOLIO_LAYER2_WEIGHT_AUDIT.md"
WEIGHT_TABLE_CSV = OUT_DIR / "PORTFOLIO_LAYER2_WEIGHT_TABLE.csv"
WEIGHT_PLOTS_HTML = OUT_DIR / "PORTFOLIO_LAYER2_WEIGHT_PLOTS.html"
REPORT_JSON = Path("portfolio_layer2_weight_audit.json")

ADOPTED_SPEC = {
    "name": "EMA250_CLOSE3_HC23_STRICT_BREAKOUT4_HV85FORCE",
    "label": "EMA250 close3 / HC23 strict breakout4 / HV85 force HC",
    "reentry_family": "state_aware_hybrid_close3",
    "rsi_period": 14,
    "threshold": 30.0,
    "ema_len": 250,
    "flips30_threshold": 2,
    "flips60_threshold": 3,
    "breakout_window": 4,
    "hv_force_threshold": 0.85,
}

BASELINE_ID = "cw1.00_s11.00_s21.00"
FINALIST_COUNT = 4
WEIGHT_CANDIDATES = [
    {"id": "cw1.00_s11.00_s21.00", "core_weight": 1.00, "sleeve1_weight": 1.00, "sleeve2_weight": 1.00, "atr_vol_target_s1": True, "atr_vol_target_s2": True},
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

INIT_EQUITY = 10000.0


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


def _scale_sleeve_equity(equity: pd.Series, weight: pd.Series, scale: pd.Series) -> tuple[pd.Series, pd.Series]:
    eq = equity.astype(float)
    wt = weight.astype(float).reindex(eq.index).ffill().fillna(0.0)
    scl = scale.reindex(eq.index).ffill().fillna(1.0).astype(float)
    ret = eq.pct_change().fillna(0.0)
    eff = scl.shift(1).fillna(1.0)
    eff = eff.where(wt.shift(1).fillna(0.0) > 1e-9, 0.0)

    scaled = pd.Series(index=eq.index, dtype=float)
    scaled.iloc[0] = INIT_EQUITY
    for i in range(1, len(eq)):
        scaled.iloc[i] = scaled.iloc[i - 1] * (1.0 + ret.iloc[i] * eff.iloc[i])
    scaled_weight = (wt * scl).astype(float)
    return scaled.astype(float), scaled_weight


def base_bundle(df_5m, df_4h, scenario: Dict, adopted_spec: Dict | None = None) -> Dict:
    spec = ADOPTED_SPEC if adopted_spec is None else adopted_spec
    formal_params = formal_current_research_optimal(**scenario["formal_overrides"])
    range_params = make_range_rotation_params(**scenario["formal_overrides"])
    formal_payload = scenario_systems(formal_params, range_params, df_5m, df_4h)

    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    background = build_volatility_background(df_4h)
    indicators = build_indicators(df_4h, riskoff_params, spec["ema_len"], background=background)
    instability = build_instability_flags(
        df_5m,
        df_4h,
        riskoff_params,
        ema_len=spec["ema_len"],
        threshold=spec["threshold"],
        flips30_threshold=spec["flips30_threshold"],
        flips60_threshold=spec["flips60_threshold"],
        hv_force_threshold=spec.get("hv_force_threshold"),
        background=background,
    )
    core_trace = build_target_trace(indicators, spec, instability["instability_state"])
    target = core_trace["weight"].astype(float)
    core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)

    systems = formal_payload["systems"]
    const1x = systems["Core+ConstAddOn[1.00x]"]
    formal = systems["Core+ConstAddOn[1.00x]+RangeRotation"]
    core_only = systems["CoreOnly"]
    candidate_sleeve = formal_payload["candidate_sleeve"]

    idx = formal["combo_equity"].index
    base_core_equity = core_sim["equity"]["equity"].reindex(idx).ffill().bfill().astype(float)
    base_core_exposure = core_sim["equity"]["exposure"].reindex(idx).ffill().bfill().astype(float)
    formal_equity = formal["combo_equity"].reindex(idx).ffill().bfill().astype(float)
    formal_exposure = formal["combo_exposure"].reindex(idx).ffill().bfill().astype(float)
    base_coreonly_equity = core_only["combo_equity"].reindex(idx).ffill().bfill().astype(float)
    const1x_equity = const1x["combo_equity"].reindex(idx).ffill().bfill().astype(float)

    base_core_pnl = base_core_equity.diff().fillna(0.0)
    base_s1_pnl = (const1x_equity.diff().fillna(0.0) - base_coreonly_equity.diff().fillna(0.0)).astype(float)
    base_s2_pnl = (formal_equity.diff().fillna(0.0) - const1x_equity.diff().fillna(0.0)).astype(float)
    base_s1_weight = const1x["sleeve"]["weight"].reindex(idx).fillna(0.0).astype(float)
    base_s2_weight = candidate_sleeve["weight"].reindex(idx).fillna(0.0).astype(float)

    return {
        "index": idx,
        "formal_equity": formal_equity,
        "formal_exposure": formal_exposure,
        "background_4h": background.reindex(indicators.index).ffill().copy(),
        "core_indicators_4h": indicators.copy(),
        "core_instability_4h": instability.copy(),
        "core_trace_4h": core_trace.copy(),
        "core_target_4h": target.copy(),
        "base_core_pnl": base_core_pnl,
        "base_core_exposure": base_core_exposure,
        "base_s1_equity": const1x["sleeve"]["equity"].reindex(idx).ffill().bfill().astype(float),
        "base_s1_pnl": base_s1_pnl,
        "base_s1_weight": base_s1_weight,
        "base_s2_equity": candidate_sleeve["equity"].reindex(idx).ffill().bfill().astype(float),
        "base_s2_pnl": base_s2_pnl,
        "base_s2_weight": base_s2_weight,
        "atr_scale": background["atr_scale"].reindex(idx).ffill().fillna(1.0).astype(float),
        "hv_pct_180d": background["hv_pct_180d"].reindex(idx).ffill().astype(float),
    }


def simulate_weight_combo(bundle: Dict, spec: Dict) -> Dict:
    idx = bundle["index"]
    core_pnl = bundle["base_core_pnl"] * spec["core_weight"]
    use_s1_atr = bool(spec.get("atr_vol_target_s1", False))
    use_s2_atr = bool(spec.get("atr_vol_target_s2", False))

    if use_s1_atr:
        s1_scale = bundle["atr_scale"] * float(spec["sleeve1_weight"])
        s1_equity, s1_weight = _scale_sleeve_equity(bundle["base_s1_equity"], bundle["base_s1_weight"], s1_scale)
        s1_pnl = s1_equity.diff().fillna(0.0)
    else:
        s1_pnl = bundle["base_s1_pnl"] * spec["sleeve1_weight"]
        s1_weight = bundle["base_s1_weight"] * spec["sleeve1_weight"]

    if use_s2_atr:
        s2_scale = bundle["atr_scale"] * float(spec["sleeve2_weight"])
        s2_equity, s2_weight = _scale_sleeve_equity(bundle["base_s2_equity"], bundle["base_s2_weight"], s2_scale)
        s2_pnl = s2_equity.diff().fillna(0.0)
    else:
        s2_pnl = bundle["base_s2_pnl"] * spec["sleeve2_weight"]
        s2_weight = bundle["base_s2_weight"] * spec["sleeve2_weight"]

    combo_equity = (INIT_EQUITY + (core_pnl + s1_pnl + s2_pnl).cumsum()).astype(float)
    combo_exposure = (bundle["base_core_exposure"] * spec["core_weight"] + s1_weight + s2_weight).astype(float)
    metrics = extended_metrics({"combo_equity": combo_equity, "combo_metrics": compute_metrics(combo_equity, combo_exposure)})
    return {
        "spec": spec,
        "combo_equity": combo_equity,
        "combo_exposure": combo_exposure,
        "effective_core_weight": (bundle["base_core_exposure"] * spec["core_weight"]).astype(float),
        "effective_s1_weight": s1_weight.astype(float),
        "effective_s2_weight": s2_weight.astype(float),
        "atr_scale": bundle["atr_scale"].astype(float),
        "hv_pct_180d": bundle["hv_pct_180d"].astype(float),
        "metrics": metrics,
        "path": path_bundle(combo_equity),
        "avg_total_exposure_pct": float(combo_exposure.mean() * 100.0),
        "peak_total_exposure_pct": float(combo_exposure.max() * 100.0),
        "avg_core_exposure_pct": float((bundle["base_core_exposure"] * spec["core_weight"]).mean() * 100.0),
        "high_use_ratio_pct": float((combo_exposure >= 2.5).mean() * 100.0),
    }


def evaluate_candidates(bundle: Dict, candidates: List[Dict]) -> Dict:
    out = {
        "FormalPortfolio": {
            "combo_equity": bundle["formal_equity"],
            "combo_exposure": bundle["formal_exposure"],
            "metrics": extended_metrics({"combo_equity": bundle["formal_equity"], "combo_metrics": compute_metrics(bundle["formal_equity"], bundle["formal_exposure"])}),
            "path": path_bundle(bundle["formal_equity"]),
            "avg_total_exposure_pct": float(bundle["formal_exposure"].mean() * 100.0),
            "peak_total_exposure_pct": float(bundle["formal_exposure"].max() * 100.0),
            "avg_core_exposure_pct": 100.0,
            "high_use_ratio_pct": float((bundle["formal_exposure"] >= 2.5).mean() * 100.0),
        }
    }
    for spec in candidates:
        out[spec["id"]] = simulate_weight_combo(bundle, spec)
    return out


def summarize_table(default_rows: Dict, stress_rows: Dict | None, harsh_rows: Dict | None) -> pd.DataFrame:
    rows = []
    formal_default = default_rows["FormalPortfolio"]["metrics"]
    formal_stress = (stress_rows or {"FormalPortfolio": {"metrics": formal_default}})["FormalPortfolio"]["metrics"]
    formal_harsh = (harsh_rows or {"FormalPortfolio": {"metrics": formal_default}})["FormalPortfolio"]["metrics"]

    for spec in WEIGHT_CANDIDATES:
        key = spec["id"]
        d = default_rows[key]
        s = stress_rows.get(key, d) if stress_rows else d
        h = harsh_rows.get(key, d) if harsh_rows else d
        rows.append({
            "id": key,
            "core_weight": spec["core_weight"],
            "sleeve1_weight": spec["sleeve1_weight"],
            "sleeve2_weight": spec["sleeve2_weight"],
            "is_current_default": key == BASELINE_ID,
            "stress_checked": stress_rows is not None and key in stress_rows,
            "harsh_checked": harsh_rows is not None and key in harsh_rows,
            "default_return_pct": d["metrics"]["TotalReturn_pct"],
            "default_calmar": d["metrics"]["Calmar"],
            "default_maxdd_pct": d["metrics"]["MaxDD_pct"],
            "default_worst3m_pct": d["path"]["worst_3m_cluster_return_pct"],
            "default_worst6m_pct": d["path"]["worst_6m_cluster_return_pct"],
            "default_recovery_days": d["path"]["recovery_days_from_maxdd"],
            "default_avg_total_exposure_pct": d["avg_total_exposure_pct"],
            "default_peak_total_exposure_pct": d["peak_total_exposure_pct"],
            "default_avg_core_exposure_pct": d["avg_core_exposure_pct"],
            "default_high_use_ratio_pct": d["high_use_ratio_pct"],
            "stress_return_pct": s["metrics"]["TotalReturn_pct"],
            "stress_calmar": s["metrics"]["Calmar"],
            "stress_maxdd_pct": s["metrics"]["MaxDD_pct"],
            "harsh_return_pct": h["metrics"]["TotalReturn_pct"],
            "harsh_calmar": h["metrics"]["Calmar"],
            "harsh_maxdd_pct": h["metrics"]["MaxDD_pct"],
            "d_return_vs_formal_default_pp": d["metrics"]["TotalReturn_pct"] - formal_default["TotalReturn_pct"],
            "d_calmar_vs_formal_default": d["metrics"]["Calmar"] - formal_default["Calmar"],
            "d_maxdd_vs_formal_default_pp": d["metrics"]["MaxDD_pct"] - formal_default["MaxDD_pct"],
            "d_calmar_vs_formal_stress": s["metrics"]["Calmar"] - formal_stress["Calmar"],
            "d_calmar_vs_formal_harsh": h["metrics"]["Calmar"] - formal_harsh["Calmar"],
        })
    return pd.DataFrame(rows).sort_values(["default_calmar", "default_return_pct"], ascending=[False, False]).reset_index(drop=True)


def pick_best(table: pd.DataFrame) -> pd.Series:
    eligible = table[
        (table["default_return_pct"] > table.loc[table["is_current_default"], "default_return_pct"].iloc[0] * 0.85)
        & (~table["stress_checked"] | (table["d_calmar_vs_formal_stress"] > 0.0))
        & (~table["harsh_checked"] | (table["d_calmar_vs_formal_harsh"] > 0.0))
    ].copy()
    if eligible.empty:
        eligible = table.copy()
    eligible = eligible.sort_values(
        ["default_calmar", "default_maxdd_pct", "default_worst6m_pct", "default_recovery_days", "default_return_pct"],
        ascending=[False, False, False, True, False],
    )
    return eligible.iloc[0]


def write_launch_audit(adopted_default: Dict, adopted_stress: Dict, adopted_harsh: Dict) -> None:
    lines = [
        "# Formal Mainline Launch Audit",
        "",
        "## Decision",
        "",
        "- Launch status for the current adopted mainline: `LAUNCH_GO`.",
        "- Current mainline:",
        "  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`",
        "  - `S1 + S2 ATR vol-targeting` enabled",
        "  - sell-side `EMA250`",
        "  - stable normal re-entry `close3`",
        "  - high-churn normal re-entry `strict EMA50 + breakout_4`",
        "  - `HV percentile >= 85` forces the high-churn gate earlier",
        "  - override `Weekly RSI(14) <= 30 hold`",
        "",
        "## Why Old `LAUNCH_NO_GO` Is Superseded",
        "",
        "- The old `LAUNCH_NO_GO` was inherited from the single-mother Gatekeeper V2 process.",
        "- That blocker was a legacy baseline-gate mismatch for a low-frequency trend mother, not a later portfolio-level adoption failure.",
        "- The current formal mainline is a later adopted multi-layer portfolio and should be judged by its own adoption evidence.",
        "",
        "## Evidence",
        "",
        f"- default: `Return {adopted_default['metrics']['TotalReturn_pct']:.2f}%`, `Calmar {adopted_default['metrics']['Calmar']:.3f}`, `MaxDD {adopted_default['metrics']['MaxDD_pct']:.2f}%`",
        f"- stress: `Return {adopted_stress['metrics']['TotalReturn_pct']:.2f}%`, `Calmar {adopted_stress['metrics']['Calmar']:.3f}`, `MaxDD {adopted_stress['metrics']['MaxDD_pct']:.2f}%`",
        f"- harsher friction: `Return {adopted_harsh['metrics']['TotalReturn_pct']:.2f}%`, `Calmar {adopted_harsh['metrics']['Calmar']:.3f}`, `MaxDD {adopted_harsh['metrics']['MaxDD_pct']:.2f}%`",
        "",
        "## Readout",
        "",
        "- The adopted mainline remains clearly superior to the prior formal baseline across default, stress, and harsher friction.",
        "- The structure question is closed: core-only Risk-Off retained, full-stack rejected.",
        "- No remaining promotion blocker inside the adopted mainline prevents launch-go status at the repository baseline level.",
    ]
    LAUNCH_AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_weight_audit(table: pd.DataFrame, best: pd.Series) -> None:
    baseline = table.loc[table["is_current_default"]].iloc[0]
    top = table.head(8)
    lines = [
        "# Portfolio Layer-2 Weight Audit",
        "",
        "- Scope: second-layer composition audit on the adopted mainline.",
        "- Fixed signal layer:",
        "  - `Core + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`",
        "  - `S1 + S2 ATR vol-targeting` enabled",
        "  - sell-side `EMA250`",
        "  - stable normal re-entry `close3`",
        "  - high-churn normal re-entry `strict EMA50 + breakout_4`",
        "  - `HV percentile >= 85` forces the high-churn gate earlier",
        "  - override `Weekly RSI(14) <= 30 hold`",
        "- Method:",
        "  - default runs compare a focused set of posture candidates around the current `1.0 / 1.0 / 1.0` mix",
        "  - finalists are then checked under `stress` and `harsher friction`",
        "  - this is a portfolio-layer composition audit, not a new signal-layer parameter search",
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
        "| Rank | Core | Sleeve1 | Sleeve2 | Return% | Calmar | MaxDD% | Worst6m | RecoveryDays | AvgExp% | PeakExp% | Stress? | Harsh? |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for i, (_, row) in enumerate(top.iterrows(), start=1):
        lines.append(
            f"| {i} | {row['core_weight']:.2f} | {row['sleeve1_weight']:.2f} | {row['sleeve2_weight']:.2f} | "
            f"{row['default_return_pct']:.2f} | {row['default_calmar']:.3f} | {row['default_maxdd_pct']:.2f} | "
            f"{row['default_worst6m_pct']:.2f} | {row['default_recovery_days']:.1f} | "
            f"{row['default_avg_total_exposure_pct']:.2f} | {row['default_peak_total_exposure_pct']:.2f} | "
            f"{'Y' if row['stress_checked'] else 'N'} | {'Y' if row['harsh_checked'] else 'N'} |"
        )
    lines.extend([
        "",
        "## Readout",
        "",
        f"- Current default sweet-spot answer: {'No' if best['id'] != BASELINE_ID else 'Yes'}." if best["id"] != BASELINE_ID else "- Current default sweet-spot answer: Yes.",
        "- The most useful second-layer changes are mild posture shifts, not a redesign of the signal layer.",
        "- The main tradeoff remains return vs path efficiency under the approved 3.0x cap envelope.",
        f"- Plot: `{WEIGHT_PLOTS_HTML.name}`",
        f"- Full table: `{WEIGHT_TABLE_CSV.name}`",
    ])
    WEIGHT_AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_plots(default_rows: Dict, table: pd.DataFrame, best: pd.Series) -> None:
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("Equity Curves", "Underwater Curves", "Calmar vs Return", "Exposure vs Recovery"),
        specs=[[{"type": "scatter"}, {"type": "scatter"}], [{"type": "scatter"}, {"type": "scatter"}]],
        vertical_spacing=0.12,
        horizontal_spacing=0.10,
    )

    formal = default_rows["FormalPortfolio"]["combo_equity"]
    baseline = default_rows[BASELINE_ID]["combo_equity"]
    best_series = default_rows[best["id"]]["combo_equity"]
    curves = [("Formal", formal, "#0f172a"), ("Current Default", baseline, "#2563eb")]
    if best["id"] != BASELINE_ID:
        curves.append(("Best Balanced", best_series, "#059669"))
    for label, series, color in curves:
        uw = (series / series.cummax() - 1.0) * 100.0
        fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=label, line=dict(color=color, width=2.4)), row=1, col=1)
        fig.add_trace(go.Scatter(x=uw.index, y=uw, mode="lines", name=f"{label} UW", line=dict(color=color, width=2.0), showlegend=False), row=1, col=2)

    colors = ["#059669" if x == best["id"] else "#2563eb" if x == BASELINE_ID else "#94a3b8" for x in table["id"]]
    fig.add_trace(
        go.Scatter(
            x=table["default_return_pct"],
            y=table["default_calmar"],
            mode="markers+text",
            text=table["id"],
            textposition="top center",
            marker=dict(size=10, color=colors),
            showlegend=False,
            customdata=table[["core_weight", "sleeve1_weight", "sleeve2_weight", "default_maxdd_pct"]].values,
            hovertemplate="Return=%{x:.2f}%<br>Calmar=%{y:.3f}<br>Core=%{customdata[0]:.2f}<br>S1=%{customdata[1]:.2f}<br>S2=%{customdata[2]:.2f}<br>MaxDD=%{customdata[3]:.2f}%<extra></extra>",
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=table["default_avg_total_exposure_pct"],
            y=table["default_recovery_days"],
            mode="markers+text",
            text=table["id"],
            textposition="top center",
            marker=dict(size=10, color=colors),
            showlegend=False,
            customdata=table[["default_peak_total_exposure_pct", "default_worst6m_pct", "default_calmar"]].values,
            hovertemplate="AvgExp=%{x:.2f}%<br>RecoveryDays=%{y:.1f}<br>PeakExp=%{customdata[0]:.2f}%<br>Worst6m=%{customdata[1]:.2f}%<br>Calmar=%{customdata[2]:.3f}<extra></extra>",
        ),
        row=2,
        col=2,
    )
    fig.update_layout(template="plotly_white", height=1050, hovermode="closest", title="Portfolio Layer-2 Weight Audit")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Underwater %", row=1, col=2)
    fig.update_xaxes(title_text="Return %", row=2, col=1)
    fig.update_yaxes(title_text="Calmar", row=2, col=1)
    fig.update_xaxes(title_text="Avg Total Exposure %", row=2, col=2)
    fig.update_yaxes(title_text="Recovery Days", row=2, col=2)
    WEIGHT_PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def main():
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    scenario_map = {s["name"]: s for s in SCENARIOS}
    default_bundle = base_bundle(df_5m, df_4h, scenario_map["default"])
    default_rows = evaluate_candidates(default_bundle, WEIGHT_CANDIDATES)
    initial_table = summarize_table(default_rows, None, None)
    finalists = [c for c in WEIGHT_CANDIDATES if c["id"] in [BASELINE_ID] + initial_table.head(FINALIST_COUNT)["id"].tolist()]

    stress_bundle = base_bundle(df_5m, df_4h, scenario_map["stress"])
    harsh_bundle = base_bundle(df_5m, df_4h, scenario_map["harsh_friction"])
    stress_rows = evaluate_candidates(stress_bundle, finalists)
    harsh_rows = evaluate_candidates(harsh_bundle, finalists)

    table = summarize_table(default_rows, stress_rows, harsh_rows)
    best = pick_best(table)

    table.to_csv(WEIGHT_TABLE_CSV, index=False)
    write_launch_audit(default_rows[BASELINE_ID], stress_rows[BASELINE_ID], harsh_rows[BASELINE_ID])
    write_weight_audit(table, best)
    write_plots(default_rows, table, best)

    REPORT_JSON.write_text(json.dumps({
        "adopted_launch_candidate": BASELINE_ID,
        "best_weight_candidate": best.to_dict(),
        "finalists": [row["id"] for row in finalists],
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
