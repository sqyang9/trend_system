#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Formal audition for ATRVT refinement winners after fixing ATR alignment."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_asset_management_system_aligned import compute_metrics
from v91_exposure_engine_e1_constant_mapping import extended_metrics

from system_defect_research.v171_volatility_proxy_system_upgrade import (
    W06_END,
    W06_START,
    W11_END,
    W11_START,
    build_formal_bundle,
    path_bundle,
)
from system_defect_research.v176_atrvt_refinement_screen import (
    Candidate as AtrCandidate,
    ScaleSpec,
    build_combo_core,
    evaluate_candidate,
)
from v123_formal_launch_and_layer2_weight_audit import SCENARIOS


OUT_DIR = Path("system_defect_research")
AUDIT_MD = OUT_DIR / "ATRVT_H90_AUDITION.md"
SUMMARY_CSV = OUT_DIR / "atrvt_h90_audition_summary.csv"
WINDOWS_CSV = OUT_DIR / "atrvt_h90_audition_windows.csv"
ANNUAL_CSV = OUT_DIR / "atrvt_h90_audition_annual_starts.csv"
SUMMARY_JSON = OUT_DIR / "atrvt_h90_audition.json"
PLOTS_HTML = OUT_DIR / "ATRVT_H90_AUDITION.html"

ANNUAL_STARTS = [
    pd.Timestamp("2020-01-01", tz="UTC"),
    pd.Timestamp("2021-01-01", tz="UTC"),
    pd.Timestamp("2022-01-01", tz="UTC"),
    pd.Timestamp("2023-01-01", tz="UTC"),
    pd.Timestamp("2024-01-01", tz="UTC"),
    pd.Timestamp("2025-01-01", tz="UTC"),
    pd.Timestamp("2026-01-01", tz="UTC"),
]

RECENT_WINDOWS = [
    ("2024-12_to_2025-06", pd.Timestamp("2024-12-01", tz="UTC"), pd.Timestamp("2025-06-01", tz="UTC")),
    ("2025-06_to_2025-12", pd.Timestamp("2025-06-01", tz="UTC"), pd.Timestamp("2025-12-01", tz="UTC")),
]


@dataclass(frozen=True)
class Candidate:
    key: str
    label: str
    color: str
    atr: AtrCandidate


CANDIDATES: List[Candidate] = [
    Candidate(
        "combo_base",
        "Current combo base: 180d med / 0.35-1.50 both",
        "#0f172a",
        AtrCandidate("combo_base", "Combo base: 180d med / 0.35-1.50 both", ScaleSpec(180, "median", 0.35, 1.50), ScaleSpec(180, "median", 0.35, 1.50)),
    ),
    Candidate(
        "combo_h90",
        "Challenger: 90d med / 0.35-1.50 both",
        "#0ea5e9",
        AtrCandidate("combo_h90", "Combo h90: 90d med / 0.35-1.50 both", ScaleSpec(90, "median", 0.35, 1.50), ScaleSpec(90, "median", 0.35, 1.50)),
    ),
    Candidate(
        "combo_s1h90_s2base",
        "Reserve: S1 90d med / S2 base",
        "#16a34a",
        AtrCandidate("combo_s1h90_s2base", "Combo asym: S1 90d med / S2 base", ScaleSpec(90, "median", 0.35, 1.50), ScaleSpec(180, "median", 0.35, 1.50)),
    ),
]


def annual_start_metrics(equity: pd.Series, exposure: pd.Series) -> Dict[str, float]:
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


def build_window_rows(bundle: dict, candidate_key: str, candidate_label: str) -> List[dict]:
    eq = bundle["combo"]["combo_equity"]
    exp = bundle["combo"]["combo_exposure"]
    rows = []
    for label, start, end in [("W06", W06_START, W06_END), ("W11", W11_START, W11_END), *RECENT_WINDOWS]:
        mask = (eq.index >= start) & (eq.index <= end)
        sub_eq = eq.loc[mask]
        sub_exp = exp.loc[mask]
        if len(sub_eq) >= 2:
            maxdd_pct = float((sub_eq / sub_eq.cummax() - 1.0).min() * 100.0)
            ret_pct = float(sub_eq.iloc[-1] / sub_eq.iloc[0] - 1.0) * 100.0
            avg_exp = float(sub_exp.mean())
        else:
            maxdd_pct = 0.0
            ret_pct = 0.0
            avg_exp = 0.0
        rows.append(
            {
                "candidate": candidate_key,
                "label": candidate_label,
                "window": label,
                "return_pct": ret_pct,
                "maxdd_pct": maxdd_pct,
                "avg_total_exposure": avg_exp,
                "dd_over_avg_exposure_pct": float(maxdd_pct / avg_exp) if avg_exp > 1e-9 else 0.0,
                "w06_med_s1_scale": float(bundle["w06_med_s1_scale"]) if label == "W06" else float("nan"),
                "w06_med_s2_scale": float(bundle["w06_med_s2_scale"]) if label == "W06" else float("nan"),
                "w11_med_s1_scale": float(bundle["w11_med_s1_scale"]) if label == "W11" else float("nan"),
                "w11_med_s2_scale": float(bundle["w11_med_s2_scale"]) if label == "W11" else float("nan"),
            }
        )
    return rows


def build_annual_table(default_map: Dict[str, dict]) -> pd.DataFrame:
    rows = []
    for start in ANNUAL_STARTS:
        for candidate in CANDIDATES:
            system = default_map[candidate.key]["combo"]
            sub_eq = system["combo_equity"][system["combo_equity"].index >= start]
            sub_ex = system["combo_exposure"][system["combo_exposure"].index >= start]
            if sub_eq.empty:
                continue
            rows.append({"start": start.date().isoformat(), "candidate": candidate.key, "label": candidate.label, **annual_start_metrics(sub_eq, sub_ex)})
    return pd.DataFrame(rows)


def annual_scorecard(annual_df: pd.DataFrame, cand: str, ref: str) -> Dict[str, int]:
    merged = (
        annual_df[annual_df["candidate"] == cand].set_index("start").add_suffix("_cand").join(
            annual_df[annual_df["candidate"] == ref].set_index("start").add_suffix("_ref"),
            how="inner",
        )
    )
    return {
        "calmar_better": int((merged["calmar_cand"] > merged["calmar_ref"]).sum()),
        "maxdd_better": int((merged["maxdd_pct_cand"] > merged["maxdd_pct_ref"]).sum()),
        "return_better": int((merged["return_pct_cand"] > merged["return_pct_ref"]).sum()),
        "n": int(len(merged)),
    }


def write_plot(default_map: Dict[str, dict]) -> None:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.46, 0.28, 0.26],
        subplot_titles=("Equity Curves", "Underwater", "Total Exposure"),
    )
    for candidate in CANDIDATES:
        system = default_map[candidate.key]["combo"]
        eq = system["combo_equity"]
        uw = (eq / eq.cummax() - 1.0) * 100.0
        ex = system["combo_exposure"] * 100.0
        fig.add_trace(go.Scatter(x=eq.index, y=eq, mode="lines", name=candidate.label, line=dict(width=2.0, color=candidate.color)), row=1, col=1)
        fig.add_trace(go.Scatter(x=uw.index, y=uw, mode="lines", name=f"{candidate.label} UW", line=dict(width=1.2, color=candidate.color), showlegend=False), row=2, col=1)
        fig.add_trace(go.Scatter(x=ex.index, y=ex, mode="lines", name=f"{candidate.label} Exposure", line=dict(width=1.2, color=candidate.color), showlegend=False), row=3, col=1)
    fig.update_layout(template="plotly_white", height=1120, hovermode="x unified", title="ATRVT H90 Audition")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Underwater %", row=2, col=1)
    fig.update_yaxes(title_text="Exposure %", row=3, col=1)
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def write_report(summary_df: pd.DataFrame, windows_df: pd.DataFrame, annual_df: pd.DataFrame) -> None:
    default_df = summary_df[summary_df["scenario"] == "default"]
    stress_df = summary_df[summary_df["scenario"] == "stress"]
    harsh_df = summary_df[summary_df["scenario"] == "harsh_friction"]

    base = default_df[default_df["candidate"] == "combo_base"].iloc[0]
    h90 = default_df[default_df["candidate"] == "combo_h90"].iloc[0]
    reserve = default_df[default_df["candidate"] == "combo_s1h90_s2base"].iloc[0]
    ann_vs_base = annual_scorecard(annual_df, "combo_h90", "combo_base")

    window_map = windows_df.set_index(["candidate", "window"])
    h90_w06 = window_map.loc[("combo_h90", "W06")]
    base_w06 = window_map.loc[("combo_base", "W06")]
    h90_w11 = window_map.loc[("combo_h90", "W11")]
    base_w11 = window_map.loc[("combo_base", "W11")]

    lines = [
        "# ATRVT H90 Audition",
        "",
        "## Scope",
        "",
        "- Mainline not changed.",
        "- This audition only revisits the ATR vol-targeting layer after fixing the ATR alignment bug.",
        "- Core side is held fixed at the current combo structure:",
        "  - `EMA250` sell-side",
        "  - stable `close3`",
        "  - high-churn `strict EMA50 + breakout_4`",
        "  - `HV percentile >= 85` forces the stricter gate earlier",
        "",
        "## Default",
        "",
        "| Candidate | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgExp% | AvgS1Scale | AvgS2Scale |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in CANDIDATES:
        row = default_df[default_df["candidate"] == candidate.key].iloc[0]
        lines.append(
            f"| {candidate.label} | {row['return_pct']:.2f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
            f"{row['worst_3m_cluster_return_pct']:.2f} | {row['worst_6m_cluster_return_pct']:.2f} | "
            f"{row['recovery_days_from_maxdd']:.1f} | {row['avg_total_exposure_pct']:.2f} | "
            f"{row['avg_s1_scale']:.3f} | {row['avg_s2_scale']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Readout",
            "",
            f"- Current combo base replay: `Return {base['return_pct']:.2f}% / Calmar {base['calmar']:.3f} / MaxDD {base['maxdd_pct']:.2f}%`.",
            f"- H90 challenger: `Return {h90['return_pct']:.2f}% / Calmar {h90['calmar']:.3f} / MaxDD {h90['maxdd_pct']:.2f}%`.",
            f"- Reserve asym candidate: `Return {reserve['return_pct']:.2f}% / Calmar {reserve['calmar']:.3f} / MaxDD {reserve['maxdd_pct']:.2f}%`.",
            f"- H90 vs base default delta: `dReturn {h90['return_pct'] - base['return_pct']:+.2f}pp / dCalmar {h90['calmar'] - base['calmar']:+.3f} / dMaxDD {h90['maxdd_pct'] - base['maxdd_pct']:+.2f}pp`.",
            f"- H90 vs base stress delta: `dCalmar {float(stress_df[stress_df['candidate'] == 'combo_h90'].iloc[0]['calmar'] - stress_df[stress_df['candidate'] == 'combo_base'].iloc[0]['calmar']):+.3f}`.",
            f"- H90 vs base harsh delta: `dCalmar {float(harsh_df[harsh_df['candidate'] == 'combo_h90'].iloc[0]['calmar'] - harsh_df[harsh_df['candidate'] == 'combo_base'].iloc[0]['calmar']):+.3f}`.",
            "",
            "## W06 / W11",
            "",
            f"- W06 `DD/Exp`: base `{base_w06['dd_over_avg_exposure_pct']:.1f}%` -> H90 `{h90_w06['dd_over_avg_exposure_pct']:.1f}%`.",
            f"- W06 median scales: base `S1 {base_w06['w06_med_s1_scale']:.3f} / S2 {base_w06['w06_med_s2_scale']:.3f}` -> H90 `S1 {h90_w06['w06_med_s1_scale']:.3f} / S2 {h90_w06['w06_med_s2_scale']:.3f}`.",
            f"- W11 avg exposure: base `{base_w11['avg_total_exposure']:.3f}` -> H90 `{h90_w11['avg_total_exposure']:.3f}`.",
            f"- W11 median scales: base `S1 {base_w11['w11_med_s1_scale']:.3f} / S2 {base_w11['w11_med_s2_scale']:.3f}` -> H90 `S1 {h90_w11['w11_med_s1_scale']:.3f} / S2 {h90_w11['w11_med_s2_scale']:.3f}`.",
            "",
            "## Annual Starts",
            "",
            f"- H90 vs base: Calmar better `{ann_vs_base['calmar_better']}/{ann_vs_base['n']}`, MaxDD better `{ann_vs_base['maxdd_better']}/{ann_vs_base['n']}`, Return better `{ann_vs_base['return_better']}/{ann_vs_base['n']}`.",
        ]
    )
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    scenario_maps: Dict[str, Dict[str, dict]] = {}
    for scenario in SCENARIOS:
        formal_bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])
        core_sim, instability = build_combo_core(df_5m, df_4h, scenario)
        result_map = {}
        for candidate in CANDIDATES:
            result_map[candidate.key] = evaluate_candidate(df_4h, formal_bundle, core_sim, instability, candidate.atr)
        scenario_maps[scenario["name"]] = result_map

    rows = []
    window_rows = []
    for scenario_name, result_map in scenario_maps.items():
        for candidate in CANDIDATES:
            result = result_map[candidate.key]
            combo = result["combo"]
            rows.append(
                {
                    "candidate": candidate.key,
                    "label": candidate.label,
                    "scenario": scenario_name,
                    "return_pct": float(combo["metrics"]["TotalReturn_pct"]),
                    "calmar": float(combo["metrics"]["Calmar"]),
                    "maxdd_pct": float(combo["metrics"]["MaxDD_pct"]),
                    "worst_3m_cluster_return_pct": float(combo["path"]["worst_3m_cluster_return_pct"]),
                    "worst_6m_cluster_return_pct": float(combo["path"]["worst_6m_cluster_return_pct"]),
                    "recovery_days_from_maxdd": float(combo["path"]["recovery_days_from_maxdd"]),
                    "avg_total_exposure_pct": float(combo["combo_exposure"].mean() * 100.0),
                    "avg_s1_scale": float(result["avg_s1_scale"]),
                    "avg_s2_scale": float(result["avg_s2_scale"]),
                }
            )
            if scenario_name == "default":
                window_rows.extend(build_window_rows(result, candidate.key, candidate.label))

    summary_df = pd.DataFrame(rows)
    windows_df = pd.DataFrame(window_rows)
    annual_df = build_annual_table(scenario_maps["default"])

    SUMMARY_CSV.write_text(summary_df.to_csv(index=False), encoding="utf-8")
    WINDOWS_CSV.write_text(windows_df.to_csv(index=False), encoding="utf-8")
    ANNUAL_CSV.write_text(annual_df.to_csv(index=False), encoding="utf-8")
    write_plot(scenario_maps["default"])
    write_report(summary_df, windows_df, annual_df)

    payload = {
        "audit_md": str(AUDIT_MD),
        "summary_csv": str(SUMMARY_CSV),
        "windows_csv": str(WINDOWS_CSV),
        "annual_csv": str(ANNUAL_CSV),
        "plots_html": str(PLOTS_HTML),
    }
    SUMMARY_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
