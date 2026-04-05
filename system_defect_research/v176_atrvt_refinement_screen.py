#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused ATRVT refinement screen for the promoted combo mainline."""

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
import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_asset_management_system_aligned import current_research_optimal as riskoff_current_research_optimal, simulate_core
from v121_coreonly_riskoff_sellside_ema_audit import build_indicators as build_core_indicators
from v121_coreonly_riskoff_sellside_ema_audit import build_instability_flags, build_target
from volatility_background import build_volatility_background

from system_defect_research.v171_volatility_proxy_system_upgrade import (
    INIT_EQUITY,
    W06_END,
    W06_START,
    W11_END,
    W11_START,
    build_formal_bundle,
    compute_atr,
    evaluate_combo,
    w06_metrics,
    w11_metrics,
)
from v123_formal_launch_and_layer2_weight_audit import ADOPTED_SPEC, SCENARIOS


OUT_DIR = Path("system_defect_research")
REPORT_MD = OUT_DIR / "ATRVT_REFINEMENT_SCREEN.md"
SUMMARY_CSV = OUT_DIR / "atrvt_refinement_summary.csv"
DETAIL_CSV = OUT_DIR / "atrvt_refinement_candidate_detail.csv"
REPORT_JSON = OUT_DIR / "atrvt_refinement_screen.json"
PLOTS_HTML = OUT_DIR / "ATRVT_REFINEMENT_SCREEN.html"

ATR_LEN = 14


@dataclass(frozen=True)
class ScaleSpec:
    ref_days: int
    ref_stat: str
    clip_min: float
    clip_max: float


@dataclass(frozen=True)
class Candidate:
    key: str
    label: str
    s1: ScaleSpec
    s2: ScaleSpec


BASE_SCALE = ScaleSpec(ref_days=180, ref_stat="median", clip_min=0.35, clip_max=1.50)

CANDIDATES: List[Candidate] = [
    Candidate("combo_base", "Combo base: 180d med / 0.35-1.50 both", BASE_SCALE, BASE_SCALE),
    Candidate("combo_h90", "Combo h90: 90d med / 0.35-1.50 both", ScaleSpec(90, "median", 0.35, 1.50), ScaleSpec(90, "median", 0.35, 1.50)),
    Candidate("combo_h365", "Combo h365: 365d med / 0.35-1.50 both", ScaleSpec(365, "median", 0.35, 1.50), ScaleSpec(365, "median", 0.35, 1.50)),
    Candidate("combo_mean180", "Combo mean180: 180d mean / 0.35-1.50 both", ScaleSpec(180, "mean", 0.35, 1.50), ScaleSpec(180, "mean", 0.35, 1.50)),
    Candidate("combo_clip025_150", "Combo clip: 180d med / 0.25-1.50 both", ScaleSpec(180, "median", 0.25, 1.50), ScaleSpec(180, "median", 0.25, 1.50)),
    Candidate("combo_clip050_150", "Combo clip: 180d med / 0.50-1.50 both", ScaleSpec(180, "median", 0.50, 1.50), ScaleSpec(180, "median", 0.50, 1.50)),
    Candidate("combo_clip035_125", "Combo clip: 180d med / 0.35-1.25 both", ScaleSpec(180, "median", 0.35, 1.25), ScaleSpec(180, "median", 0.35, 1.25)),
    Candidate("combo_clip035_175", "Combo clip: 180d med / 0.35-1.75 both", ScaleSpec(180, "median", 0.35, 1.75), ScaleSpec(180, "median", 0.35, 1.75)),
    Candidate("combo_s1h90_s2base", "Combo asym: S1 90d med / S2 base", ScaleSpec(90, "median", 0.35, 1.50), BASE_SCALE),
    Candidate("combo_s1base_s2tight", "Combo asym: S1 base / S2 tight", BASE_SCALE, ScaleSpec(180, "median", 0.25, 1.25)),
    Candidate("combo_s1loose_s2tight", "Combo asym: S1 loose / S2 tight", ScaleSpec(180, "median", 0.50, 1.75), ScaleSpec(180, "median", 0.25, 1.25)),
]


def build_atr_scale_custom(df_4h: pd.DataFrame, spec: ScaleSpec) -> pd.Series:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    atr = compute_atr(d4.reset_index(), ATR_LEN)
    atr.index = d4.index
    atr_pct = (atr / d4["close"].astype(float)).replace([np.inf, -np.inf], np.nan)
    window = spec.ref_days * 6
    min_periods = max(60, window // 4)
    if spec.ref_stat == "median":
        ref = atr_pct.rolling(window, min_periods=min_periods).median().shift(1)
    elif spec.ref_stat == "mean":
        ref = atr_pct.rolling(window, min_periods=min_periods).mean().shift(1)
    else:
        raise ValueError(spec.ref_stat)
    scale = (ref / atr_pct).clip(lower=spec.clip_min, upper=spec.clip_max)
    return scale.replace([np.inf, -np.inf], np.nan).fillna(1.0).astype(float)


def scale_sleeve_custom(equity: pd.Series, weight: pd.Series, scale: pd.Series, clip_min: float, clip_max: float) -> tuple[pd.Series, pd.Series]:
    eq = equity.astype(float).copy()
    wt = weight.astype(float).reindex(eq.index).ffill().fillna(0.0)
    scl = scale.reindex(eq.index).ffill().fillna(1.0).clip(lower=clip_min, upper=clip_max)
    ret = eq.pct_change().fillna(0.0)
    eff = scl.shift(1).fillna(1.0)
    eff = eff.where(wt.shift(1).fillna(0.0) > 1e-9, 0.0)

    scaled = pd.Series(index=eq.index, dtype=float)
    scaled.iloc[0] = INIT_EQUITY
    for i in range(1, len(eq)):
        scaled.iloc[i] = scaled.iloc[i - 1] * (1.0 + ret.iloc[i] * eff.iloc[i])
    scaled_weight = (wt * scl).astype(float)
    return scaled.astype(float), scaled_weight


def build_combo_core(df_5m: pd.DataFrame, df_4h: pd.DataFrame, scenario: Dict) -> tuple[dict, pd.DataFrame]:
    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    shared_bg = build_volatility_background(df_4h)
    indicators = build_core_indicators(df_4h, riskoff_params, ADOPTED_SPEC["ema_len"], background=shared_bg)
    instability = build_instability_flags(
        df_5m,
        df_4h,
        riskoff_params,
        ema_len=ADOPTED_SPEC["ema_len"],
        threshold=ADOPTED_SPEC["threshold"],
        flips30_threshold=ADOPTED_SPEC["flips30_threshold"],
        flips60_threshold=ADOPTED_SPEC["flips60_threshold"],
        hv_force_threshold=0.85,
        background=shared_bg,
    )
    target = build_target(indicators, ADOPTED_SPEC, instability["instability_state"])
    core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
    return core_sim, instability


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
    top_keys = list(
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
        .head(5)["key"]
    )
    color_map = {
        "combo_base": "#0f172a",
        "combo_h90": "#0ea5e9",
        "combo_h365": "#9333ea",
        "combo_mean180": "#ea580c",
        "combo_clip025_150": "#059669",
        "combo_clip050_150": "#dc2626",
        "combo_clip035_125": "#a16207",
        "combo_clip035_175": "#7c3aed",
        "combo_s1h90_s2base": "#2563eb",
        "combo_s1base_s2tight": "#0d9488",
        "combo_s1loose_s2tight": "#be123c",
    }
    fig = go.Figure()
    for key in top_keys:
        eq = default_map[key]["combo"]["combo_equity"]
        fig.add_trace(go.Scatter(x=eq.index, y=eq, mode="lines", name=key, line=dict(width=2.0, color=color_map.get(key, "#64748b"))))
    fig.update_layout(template="plotly_white", hovermode="x unified", height=620, title="ATRVT Refinement Screen: Top Default Equity Curves")
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
        row = {
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
        rows.append(row)
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

    base = summary_df[summary_df["candidate"] == "combo_base"].iloc[0]
    best = summary_df.iloc[0]
    lines = [
        "# ATRVT Refinement Screen",
        "",
        "- Scope: keep the promoted combo mainline structure fixed, and refine only the ATR vol-targeting layer.",
        "- Core side stays fixed at current combo logic:",
        "  - `EMA250` sell-side",
        "  - stable `close3`",
        "  - high-churn `strict EMA50 + breakout_4`",
        "  - `HV percentile >= 85` forces the stricter gate earlier",
        "- Only three ATRVT dimensions are tested:",
        "  - reference horizon / statistic",
        "  - clip band",
        "  - `S1 / S2` asymmetry",
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
            f"- Current combo base: `Return {base['default_return_pct']:.2f}% / Calmar {base['default_calmar']:.3f} / MaxDD {base['default_maxdd_pct']:.2f}%`.",
            f"- Best screened candidate: `{best['label']}` with `Return {best['default_return_pct']:.2f}% / Calmar {best['default_calmar']:.3f} / MaxDD {best['default_maxdd_pct']:.2f}%`.",
            f"- Best-vs-base delta: `dReturn {best['default_return_pct'] - base['default_return_pct']:+.2f}pp / dCalmar {best['default_calmar'] - base['default_calmar']:+.3f} / dMaxDD {best['default_maxdd_pct'] - base['default_maxdd_pct']:+.2f}pp`.",
            "",
            "## Interpretation Hints",
            "",
            "- `W11` entries and quick re-FLAT do not move here because the Core gate is fixed; this screen is only about sleeve sizing.",
            "- The useful reads are therefore:",
            "  - headline economics",
            "  - `W06 DD/Exp`",
            "  - how the scale changes in `W06` and `W11` for `S1` and `S2` separately.",
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
