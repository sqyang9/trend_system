#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused ATRVT parameterization study around the H90 challenger."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig_system_defect_research")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import pandas as pd
import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from system_defect_research.v171_volatility_proxy_system_upgrade import (
    W06_END,
    W06_START,
    W11_END,
    W11_START,
    build_formal_bundle,
    evaluate_combo,
    w06_metrics,
    w11_metrics,
)
from system_defect_research.v176_atrvt_refinement_screen import (
    Candidate,
    ScaleSpec,
    build_atr_scale_custom,
    build_combo_core,
    scale_sleeve_custom,
)
from v123_formal_launch_and_layer2_weight_audit import SCENARIOS


OUT_DIR = Path("system_defect_research")
REPORT_MD = OUT_DIR / "ATRVT_H90_REFINEMENT_SCREEN.md"
SUMMARY_CSV = OUT_DIR / "atrvt_h90_refinement_summary.csv"
DETAIL_CSV = OUT_DIR / "atrvt_h90_refinement_candidate_detail.csv"
REPORT_JSON = OUT_DIR / "atrvt_h90_refinement_screen.json"
PLOTS_HTML = OUT_DIR / "ATRVT_H90_REFINEMENT_SCREEN.html"


H90 = ScaleSpec(ref_days=90, ref_stat="median", clip_min=0.35, clip_max=1.50)

CANDIDATES: List[Candidate] = [
    Candidate("combo_base180", "Reference: 180d med / 0.35-1.50 both", ScaleSpec(180, "median", 0.35, 1.50), ScaleSpec(180, "median", 0.35, 1.50)),
    Candidate("combo_h90", "Anchor: 90d med / 0.35-1.50 both", H90, H90),
    Candidate("combo_h60", "60d med / 0.35-1.50 both", ScaleSpec(60, "median", 0.35, 1.50), ScaleSpec(60, "median", 0.35, 1.50)),
    Candidate("combo_h120", "120d med / 0.35-1.50 both", ScaleSpec(120, "median", 0.35, 1.50), ScaleSpec(120, "median", 0.35, 1.50)),
    Candidate("combo_h90_mean90", "90d mean / 0.35-1.50 both", ScaleSpec(90, "mean", 0.35, 1.50), ScaleSpec(90, "mean", 0.35, 1.50)),
    Candidate("combo_h90_clip035_125", "90d med / 0.35-1.25 both", ScaleSpec(90, "median", 0.35, 1.25), ScaleSpec(90, "median", 0.35, 1.25)),
    Candidate("combo_h90_clip035_175", "90d med / 0.35-1.75 both", ScaleSpec(90, "median", 0.35, 1.75), ScaleSpec(90, "median", 0.35, 1.75)),
    Candidate("combo_h90_clip025_150", "90d med / 0.25-1.50 both", ScaleSpec(90, "median", 0.25, 1.50), ScaleSpec(90, "median", 0.25, 1.50)),
    Candidate("combo_h90_clip050_150", "90d med / 0.50-1.50 both", ScaleSpec(90, "median", 0.50, 1.50), ScaleSpec(90, "median", 0.50, 1.50)),
    Candidate("combo_h90_s1h60_s2h90", "S1 60d med / S2 90d med", ScaleSpec(60, "median", 0.35, 1.50), H90),
    Candidate("combo_h90_s1h90_s2h120", "S1 90d med / S2 120d med", H90, ScaleSpec(120, "median", 0.35, 1.50)),
    Candidate("combo_h90_s1tight_s2base", "S1 90d med 0.35-1.25 / S2 H90", ScaleSpec(90, "median", 0.35, 1.25), H90),
    Candidate("combo_h90_s1base_s2tight", "S1 H90 / S2 90d med 0.35-1.25", H90, ScaleSpec(90, "median", 0.35, 1.25)),
]


def evaluate_candidate(df_4h: pd.DataFrame, formal_bundle: dict, core_sim: dict, instability: pd.DataFrame, candidate: Candidate) -> dict:
    idx = formal_bundle["index"]
    s1_scale = build_atr_scale_custom(df_4h, candidate.s1).reindex(idx).ffill().fillna(1.0)
    s2_scale = build_atr_scale_custom(df_4h, candidate.s2).reindex(idx).ffill().fillna(1.0)
    s1_eq, s1_w = scale_sleeve_custom(formal_bundle["s1_equity"], formal_bundle["s1_weight"], s1_scale, candidate.s1.clip_min, candidate.s1.clip_max)
    s2_eq, s2_w = scale_sleeve_custom(formal_bundle["s2_equity"], formal_bundle["s2_weight"], s2_scale, candidate.s2.clip_min, candidate.s2.clip_max)
    combo = evaluate_combo(formal_bundle, core_sim, s1_eq, s1_w, s2_eq, s2_w)
    return {
        "combo": combo,
        "w06": w06_metrics(combo),
        "w11": w11_metrics(combo, pd.DataFrame(columns=["re_time", "quick_reflat_after_re_14d", "quick_reflat_after_re_30d"])),
        "avg_s1_scale": float(s1_scale.mean()),
        "avg_s2_scale": float(s2_scale.mean()),
        "w06_med_s1_scale": float(s1_scale[(s1_scale.index >= W06_START) & (s1_scale.index <= W06_END)].median()),
        "w06_med_s2_scale": float(s2_scale[(s2_scale.index >= W06_START) & (s2_scale.index <= W06_END)].median()),
        "w11_med_s1_scale": float(s1_scale[(s1_scale.index >= W11_START) & (s1_scale.index <= W11_END)].median()),
        "w11_med_s2_scale": float(s2_scale[(s2_scale.index >= W11_START) & (s2_scale.index <= W11_END)].median()),
    }


def write_plot(default_map: Dict[str, dict]) -> None:
    rank_df = (
        pd.DataFrame(
            [
                {
                    "key": cand.key,
                    "calmar": default_map[cand.key]["combo"]["metrics"]["Calmar"],
                    "ret": default_map[cand.key]["combo"]["metrics"]["TotalReturn_pct"],
                }
                for cand in CANDIDATES
            ]
        )
        .sort_values(["calmar", "ret"], ascending=[False, False])
        .head(5)
    )
    color_map = {
        "combo_base180": "#0f172a",
        "combo_h90": "#0ea5e9",
        "combo_h60": "#16a34a",
        "combo_h120": "#9333ea",
        "combo_h90_mean90": "#ea580c",
        "combo_h90_clip035_125": "#a16207",
        "combo_h90_clip035_175": "#7c3aed",
        "combo_h90_clip025_150": "#059669",
        "combo_h90_clip050_150": "#dc2626",
        "combo_h90_s1h60_s2h90": "#2563eb",
        "combo_h90_s1h90_s2h120": "#0891b2",
        "combo_h90_s1tight_s2base": "#be123c",
        "combo_h90_s1base_s2tight": "#0d9488",
    }
    fig = go.Figure()
    for key in rank_df["key"]:
        eq = default_map[key]["combo"]["combo_equity"]
        fig.add_trace(go.Scatter(x=eq.index, y=eq, mode="lines", name=key, line=dict(width=2.0, color=color_map.get(key, "#64748b"))))
    fig.update_layout(template="plotly_white", hovermode="x unified", height=620, title="ATRVT H90 Refinement Screen: Top Default Equity Curves")
    fig.update_yaxes(title_text="Equity")
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    scenario_maps: dict[str, dict] = {}
    for scenario in SCENARIOS:
        formal_bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])
        core_sim, instability = build_combo_core(df_5m, df_4h, scenario)
        results = {}
        for candidate in CANDIDATES:
            results[candidate.key] = evaluate_candidate(df_4h, formal_bundle, core_sim, instability, candidate)
        scenario_maps[scenario["name"]] = results

    rows = []
    detail_rows = []
    for candidate in CANDIDATES:
        default = scenario_maps["default"][candidate.key]
        stress = scenario_maps["stress"][candidate.key]
        harsh = scenario_maps["harsh_friction"][candidate.key]
        rows.append(
            {
                "candidate": candidate.key,
                "label": candidate.label,
                "s1_ref_days": candidate.s1.ref_days,
                "s1_ref_stat": candidate.s1.ref_stat,
                "s1_clip_min": candidate.s1.clip_min,
                "s1_clip_max": candidate.s1.clip_max,
                "s2_ref_days": candidate.s2.ref_days,
                "s2_ref_stat": candidate.s2.ref_stat,
                "s2_clip_min": candidate.s2.clip_min,
                "s2_clip_max": candidate.s2.clip_max,
                "default_return_pct": float(default["combo"]["metrics"]["TotalReturn_pct"]),
                "default_calmar": float(default["combo"]["metrics"]["Calmar"]),
                "default_maxdd_pct": float(default["combo"]["metrics"]["MaxDD_pct"]),
                "stress_calmar": float(stress["combo"]["metrics"]["Calmar"]),
                "harsh_calmar": float(harsh["combo"]["metrics"]["Calmar"]),
                "w06_dd_over_avg_exposure_pct": float(default["w06"]["w06_dd_over_avg_exposure_pct"]),
                "w06_maxdd_pct": float(default["w06"]["w06_maxdd_pct"]),
                "w11_avg_total_exposure": float(default["w11"]["w11_avg_total_exposure"]),
                "avg_s1_scale": float(default["avg_s1_scale"]),
                "avg_s2_scale": float(default["avg_s2_scale"]),
                "w06_med_s1_scale": float(default["w06_med_s1_scale"]),
                "w06_med_s2_scale": float(default["w06_med_s2_scale"]),
                "w11_med_s1_scale": float(default["w11_med_s1_scale"]),
                "w11_med_s2_scale": float(default["w11_med_s2_scale"]),
            }
        )
        for scenario_name in ["default", "stress", "harsh_friction"]:
            combo = scenario_maps[scenario_name][candidate.key]["combo"]
            detail_rows.append(
                {
                    "candidate": candidate.key,
                    "label": candidate.label,
                    "scenario": scenario_name,
                    "return_pct": float(combo["metrics"]["TotalReturn_pct"]),
                    "calmar": float(combo["metrics"]["Calmar"]),
                    "maxdd_pct": float(combo["metrics"]["MaxDD_pct"]),
                    "worst3m_pct": float(combo["path"]["worst_3m_cluster_return_pct"]),
                    "worst6m_pct": float(combo["path"]["worst_6m_cluster_return_pct"]),
                    "recovery_days": float(combo["path"]["recovery_days_from_maxdd"]),
                    "avg_total_exposure_pct": float(combo["combo_exposure"].mean() * 100.0),
                }
            )

    summary_df = pd.DataFrame(rows).sort_values(["default_calmar", "default_return_pct"], ascending=[False, False]).reset_index(drop=True)
    detail_df = pd.DataFrame(detail_rows)
    SUMMARY_CSV.write_text(summary_df.to_csv(index=False), encoding="utf-8")
    DETAIL_CSV.write_text(detail_df.to_csv(index=False), encoding="utf-8")

    anchor = summary_df[summary_df["candidate"] == "combo_h90"].iloc[0]
    best = summary_df.iloc[0]
    lines = [
        "# ATRVT H90 Refinement Screen",
        "",
        "- Scope: keep the corrected combo mainline structure fixed, and refine only the ATR vol-targeting layer around the H90 challenger.",
        "- Core side stays fixed at current combo logic:",
        "  - `EMA250` sell-side",
        "  - stable `close3`",
        "  - high-churn `strict EMA50 + breakout_4`",
        "  - `HV percentile >= 85` forces the stricter gate earlier",
        "- H90 anchor carried through this screen explicitly.",
        "",
        "## Default Summary",
        "",
        "| Candidate | Return% | Calmar | MaxDD% | Stress Calmar | Harsh Calmar | W06 DD/Exp | W11 AvgExp |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in summary_df.iterrows():
        lines.append(
            f"| {row['label']} | {row['default_return_pct']:.2f} | {row['default_calmar']:.3f} | {row['default_maxdd_pct']:.2f} | "
            f"{row['stress_calmar']:.3f} | {row['harsh_calmar']:.3f} | {row['w06_dd_over_avg_exposure_pct']:.1f}% | {row['w11_avg_total_exposure']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Readout",
            "",
            f"- H90 anchor: `Return {anchor['default_return_pct']:.2f}% / Calmar {anchor['default_calmar']:.3f} / MaxDD {anchor['default_maxdd_pct']:.2f}%`.",
            f"- Best screened candidate: `{best['label']}` with `Return {best['default_return_pct']:.2f}% / Calmar {best['default_calmar']:.3f} / MaxDD {best['default_maxdd_pct']:.2f}%`.",
            f"- Best-vs-H90 delta: `dReturn {best['default_return_pct'] - anchor['default_return_pct']:+.2f}pp / dCalmar {best['default_calmar'] - anchor['default_calmar']:+.3f} / dMaxDD {best['default_maxdd_pct'] - anchor['default_maxdd_pct']:+.2f}pp`.",
            "",
            "## Interpretation Hints",
            "",
            "- `W11` entries and quick re-FLAT do not move here because the Core gate is fixed; this screen is only about sleeve sizing.",
            "- The useful reads are therefore:",
            "  - headline economics",
            "  - `W06 DD/Exp`",
            "  - `W11` average exposure",
            "  - `S1 / S2` median scales inside `W06` and `W11`.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    write_plot(scenario_maps["default"])

    payload = {
        "report_md": str(REPORT_MD),
        "summary_csv": str(SUMMARY_CSV),
        "detail_csv": str(DETAIL_CSV),
        "plot_html": str(PLOTS_HTML),
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
