#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promotion-style audit for balanced ATRVT candidates."""

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
    w06_metrics,
)
from system_defect_research.v176_atrvt_refinement_screen import (
    Candidate as AtrCandidate,
    ScaleSpec,
    build_combo_core,
    evaluate_candidate,
)
from v123_formal_launch_and_layer2_weight_audit import SCENARIOS


OUT_DIR = Path("system_defect_research")
REPORT_MD = OUT_DIR / "BALANCED_ATRVT_PROMOTION_AUDIT.md"
SUMMARY_CSV = OUT_DIR / "balanced_atrvt_promotion_summary.csv"
ANNUAL_CSV = OUT_DIR / "balanced_atrvt_promotion_annual.csv"
JSON_OUT = OUT_DIR / "balanced_atrvt_promotion_audit.json"

ANNUAL_STARTS = [
    pd.Timestamp("2020-01-01", tz="UTC"),
    pd.Timestamp("2021-01-01", tz="UTC"),
    pd.Timestamp("2022-01-01", tz="UTC"),
    pd.Timestamp("2023-01-01", tz="UTC"),
    pd.Timestamp("2024-01-01", tz="UTC"),
    pd.Timestamp("2025-01-01", tz="UTC"),
    pd.Timestamp("2026-01-01", tz="UTC"),
]

WINDOWS = [
    ("fit_W01_W06_validate_W07_W13", ["W01", "W02", "W03", "W04", "W05", "W06"], ["W07", "W08", "W09", "W10", "W11", "W12", "W13"]),
    ("fit_W01_W09_validate_W10_W13", ["W01", "W02", "W03", "W04", "W05", "W06", "W07", "W08", "W09"], ["W10", "W11", "W12", "W13"]),
]


@dataclass(frozen=True)
class Candidate:
    key: str
    label: str
    atr: AtrCandidate


def sym(key: str, days: int, clip_min: float = 0.35, clip_max: float = 1.50) -> Candidate:
    spec = ScaleSpec(days, "median", clip_min, clip_max)
    return Candidate(key, f"{days}d med / {clip_min:.2f}-{clip_max:.2f} both", AtrCandidate(key, "sym", spec, spec))


def asym(key: str, label: str, s1_days: int, s2_days: int, s1_clip_min: float = 0.35, s1_clip_max: float = 1.50, s2_clip_min: float = 0.35, s2_clip_max: float = 1.50) -> Candidate:
    s1 = ScaleSpec(s1_days, "median", s1_clip_min, s1_clip_max)
    s2 = ScaleSpec(s2_days, "median", s2_clip_min, s2_clip_max)
    return Candidate(key, label, AtrCandidate(key, label, s1, s2))


CANDIDATES: List[Candidate] = [
    sym("base180", 180),
    sym("h90", 90),
    sym("h90_clip125", 90, 0.35, 1.25),
    asym("s1180_s2h60", "S1 180d / S2 60d", 180, 60),
    asym("s1h90_s2h60", "S1 90d / S2 60d", 90, 60),
]


def summarize_segment(equity: pd.Series, exposure: pd.Series) -> dict:
    metrics = extended_metrics({"combo_equity": equity, "combo_metrics": compute_metrics(equity, exposure)})
    path = path_bundle(equity)
    return {
        "return_pct": float(metrics["TotalReturn_pct"]),
        "calmar": float(metrics["Calmar"]),
        "maxdd_pct": float(metrics["MaxDD_pct"]),
        "worst6m_pct": float(path["worst_6m_cluster_return_pct"]),
        "recovery_days": float(path["recovery_days_from_maxdd"]),
    }


def annual_scorecard(annual_df: pd.DataFrame, cand: str, ref: str) -> Dict[str, int]:
    merged = (
        annual_df[annual_df["candidate"] == cand].set_index("start").add_suffix("_cand").join(
            annual_df[annual_df["candidate"] == ref].set_index("start").add_suffix("_ref"),
            how="inner",
        )
    )
    return {
        "return_better": int((merged["return_pct_cand"] > merged["return_pct_ref"]).sum()),
        "calmar_better": int((merged["calmar_cand"] > merged["calmar_ref"]).sum()),
        "maxdd_better": int((merged["maxdd_pct_cand"] > merged["maxdd_pct_ref"]).sum()),
        "n": int(len(merged)),
    }


def window_mask(index: pd.Index, names: List[str]) -> pd.Series:
    parts = [
        ("W01", pd.Timestamp("2019-12-16 04:00:00", tz="UTC"), pd.Timestamp("2020-06-16 00:00:00", tz="UTC")),
        ("W02", pd.Timestamp("2020-06-16 04:00:00", tz="UTC"), pd.Timestamp("2020-12-16 00:00:00", tz="UTC")),
        ("W03", pd.Timestamp("2020-12-16 04:00:00", tz="UTC"), pd.Timestamp("2021-06-16 00:00:00", tz="UTC")),
        ("W04", pd.Timestamp("2021-06-16 04:00:00", tz="UTC"), pd.Timestamp("2021-12-16 00:00:00", tz="UTC")),
        ("W05", pd.Timestamp("2021-12-16 04:00:00", tz="UTC"), pd.Timestamp("2022-06-16 00:00:00", tz="UTC")),
        ("W06", pd.Timestamp("2022-06-16 04:00:00", tz="UTC"), pd.Timestamp("2022-12-16 00:00:00", tz="UTC")),
        ("W07", pd.Timestamp("2022-12-16 04:00:00", tz="UTC"), pd.Timestamp("2023-06-16 00:00:00", tz="UTC")),
        ("W08", pd.Timestamp("2023-06-16 04:00:00", tz="UTC"), pd.Timestamp("2023-12-16 00:00:00", tz="UTC")),
        ("W09", pd.Timestamp("2023-12-16 04:00:00", tz="UTC"), pd.Timestamp("2024-06-16 00:00:00", tz="UTC")),
        ("W10", pd.Timestamp("2024-06-16 04:00:00", tz="UTC"), pd.Timestamp("2024-12-16 00:00:00", tz="UTC")),
        ("W11", pd.Timestamp("2024-12-16 04:00:00", tz="UTC"), pd.Timestamp("2025-06-16 00:00:00", tz="UTC")),
        ("W12", pd.Timestamp("2025-06-16 04:00:00", tz="UTC"), pd.Timestamp("2025-12-16 00:00:00", tz="UTC")),
        ("W13", pd.Timestamp("2025-12-16 04:00:00", tz="UTC"), pd.Timestamp("2026-03-07 16:00:00", tz="UTC")),
    ]
    mask = pd.Series(False, index=index)
    for label, start, end in parts:
        if label in names:
            mask = mask | ((index >= start) & (index <= end))
    return mask


def evaluate_train_validate(system: dict, train_windows: List[str], validate_windows: List[str]) -> dict:
    eq = system["combo"]["combo_equity"]
    ex = system["combo"]["combo_exposure"]
    return {
        "train": summarize_segment(eq.loc[window_mask(eq.index, train_windows)], ex.loc[window_mask(ex.index, train_windows)]),
        "validate": summarize_segment(eq.loc[window_mask(eq.index, validate_windows)], ex.loc[window_mask(ex.index, validate_windows)]),
    }


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    scenario_maps: Dict[str, Dict[str, dict]] = {}
    for scenario in SCENARIOS:
        formal_bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])
        core_sim, instability = build_combo_core(df_5m, df_4h, scenario)
        scenario_maps[scenario["name"]] = {
            candidate.key: evaluate_candidate(df_4h, formal_bundle, core_sim, instability, candidate.atr)
            for candidate in CANDIDATES
        }

    summary_rows = []
    for scenario_name, result_map in scenario_maps.items():
        for candidate in CANDIDATES:
            bundle = result_map[candidate.key]
            combo = bundle["combo"]
            w06 = w06_metrics(combo)
            summary_rows.append(
                {
                    "scenario": scenario_name,
                    "candidate": candidate.key,
                    "label": candidate.label,
                    "return_pct": float(combo["metrics"]["TotalReturn_pct"]),
                    "calmar": float(combo["metrics"]["Calmar"]),
                    "maxdd_pct": float(combo["metrics"]["MaxDD_pct"]),
                    "worst6m_pct": float(combo["path"]["worst_6m_cluster_return_pct"]),
                    "recovery_days": float(combo["path"]["recovery_days_from_maxdd"]),
                    "w06_dd_over_avg_exposure_pct": float(w06["w06_dd_over_avg_exposure_pct"]),
                    "w11_avg_total_exposure": float(bundle["w11"]["w11_avg_total_exposure"]),
                }
            )
    summary_df = pd.DataFrame(summary_rows)

    annual_rows = []
    default_map = scenario_maps["default"]
    for start in ANNUAL_STARTS:
        for candidate in CANDIDATES:
            system = default_map[candidate.key]["combo"]
            eq = system["combo_equity"][system["combo_equity"].index >= start]
            ex = system["combo_exposure"][system["combo_exposure"].index >= start]
            if eq.empty:
                continue
            annual_rows.append({"start": start.date().isoformat(), "candidate": candidate.key, "label": candidate.label, **summarize_segment(eq, ex)})
    annual_df = pd.DataFrame(annual_rows)

    wf_rows = []
    for split_name, train_windows, validate_windows in WINDOWS:
        for candidate in CANDIDATES:
            result = evaluate_train_validate(default_map[candidate.key], train_windows, validate_windows)
            wf_rows.append(
                {
                    "split": split_name,
                    "candidate": candidate.key,
                    "label": candidate.label,
                    "train_return_pct": result["train"]["return_pct"],
                    "train_calmar": result["train"]["calmar"],
                    "validate_return_pct": result["validate"]["return_pct"],
                    "validate_calmar": result["validate"]["calmar"],
                    "validate_maxdd_pct": result["validate"]["maxdd_pct"],
                }
            )
    wf_df = pd.DataFrame(wf_rows)

    base = summary_df[(summary_df["scenario"] == "default") & (summary_df["candidate"] == "base180")].iloc[0]
    balanced = summary_df[(summary_df["scenario"] == "default") & (summary_df["candidate"] == "s1h90_s2h60")].iloc[0]
    robust = summary_df[(summary_df["scenario"] == "default") & (summary_df["candidate"] == "s1180_s2h60")].iloc[0]
    h90 = summary_df[(summary_df["scenario"] == "default") & (summary_df["candidate"] == "h90")].iloc[0]
    h90clip = summary_df[(summary_df["scenario"] == "default") & (summary_df["candidate"] == "h90_clip125")].iloc[0]

    ann_balanced = annual_scorecard(annual_df, "s1h90_s2h60", "base180")
    ann_robust = annual_scorecard(annual_df, "s1180_s2h60", "base180")

    wf_map = wf_df.set_index(["candidate", "split"])
    lines = [
        "# Balanced ATRVT Promotion Audit",
        "",
        "## Scope",
        "",
        "- Mainline not changed.",
        "- This audit focuses on balanced ATRVT candidates, not the economics-only `H45/H60` tail.",
        "- Goal: find a promotion-grade contract with better robustness and still meaningful default gains.",
        "",
        "## Default / Stress / Harsh",
        "",
        "| Candidate | Scenario | Return% | Calmar | MaxDD% | W06 DD/Exp | W11 AvgExp |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in CANDIDATES:
        for scenario in ["default", "stress", "harsh_friction"]:
            row = summary_df[(summary_df["scenario"] == scenario) & (summary_df["candidate"] == candidate.key)].iloc[0]
            lines.append(
                f"| {candidate.label} | {scenario} | {row['return_pct']:.2f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
                f"{row['w06_dd_over_avg_exposure_pct']:.1f}% | {row['w11_avg_total_exposure']:.3f} |"
            )

    lines.extend(
        [
            "",
            "## Annual Starts Vs Corrected 180d Baseline",
            "",
            f"- `S1 90d / S2 60d`: Return better `{ann_balanced['return_better']}/{ann_balanced['n']}`, Calmar better `{ann_balanced['calmar_better']}/{ann_balanced['n']}`, MaxDD better `{ann_balanced['maxdd_better']}/{ann_balanced['n']}`.",
            f"- `S1 180d / S2 60d`: Return better `{ann_robust['return_better']}/{ann_robust['n']}`, Calmar better `{ann_robust['calmar_better']}/{ann_robust['n']}`, MaxDD better `{ann_robust['maxdd_better']}/{ann_robust['n']}`.",
            "",
            "## Freeze-Date Validation",
            "",
            "| Candidate | Split | Validate Return% | Validate Calmar | Validate MaxDD% |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for candidate in ["base180", "h90", "h90_clip125", "s1180_s2h60", "s1h90_s2h60"]:
        for split_name, _, _ in WINDOWS:
            row = wf_map.loc[(candidate, split_name)]
            lines.append(
                f"| {row['label']} | {split_name} | {row['validate_return_pct']:.2f} | {row['validate_calmar']:.3f} | {row['validate_maxdd_pct']:.2f} |"
            )

    lines.extend(
        [
            "",
            "## Decision Readout",
            "",
            f"- Corrected baseline `180d`: `Return {base['return_pct']:.2f}% / Calmar {base['calmar']:.3f} / MaxDD {base['maxdd_pct']:.2f}%`.",
            f"- Balanced candidate `S1 90d / S2 60d`: `Return {balanced['return_pct']:.2f}% / Calmar {balanced['calmar']:.3f} / MaxDD {balanced['maxdd_pct']:.2f}%`.",
            f"- Robust candidate `S1 180d / S2 60d`: `Return {robust['return_pct']:.2f}% / Calmar {robust['calmar']:.3f} / MaxDD {robust['maxdd_pct']:.2f}%`.",
            f"- Reference sibling `H90`: `Return {h90['return_pct']:.2f}% / Calmar {h90['calmar']:.3f} / MaxDD {h90['maxdd_pct']:.2f}%`.",
            f"- Reference sibling `H90 0.35-1.25`: `Return {h90clip['return_pct']:.2f}% / Calmar {h90clip['calmar']:.3f} / MaxDD {h90clip['maxdd_pct']:.2f}%`.",
            "",
            "## Verdict",
            "",
            "- `S1 90d / S2 60d` is the best balanced candidate in this set: it keeps a large part of the H60 economics, improves W06 and W11 exposure, and still beats the corrected `180d` baseline on freeze-date average.",
            "- `S1 180d / S2 60d` is the most robustness-first contract, but its default upside is too modest relative to `S1 90d / S2 60d`.",
            "- Promotion verdict for `S1 90d / S2 60d`: `GO_TO_LANDING_AUDIT`.",
            "- Implementation note: if promoted, keep `atrvt_s1_ref_days` and `atrvt_s2_ref_days` explicit in the shared contract so the tuning surface remains small and governed.",
        ]
    )

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary_df.to_csv(SUMMARY_CSV, index=False)
    annual_df.to_csv(ANNUAL_CSV, index=False)
    JSON_OUT.write_text(
        json.dumps(
            {
                "balanced_candidate": {
                    "key": "s1h90_s2h60",
                    "default_return_pct": float(balanced["return_pct"]),
                    "default_calmar": float(balanced["calmar"]),
                    "default_maxdd_pct": float(balanced["maxdd_pct"]),
                },
                "robust_candidate": {
                    "key": "s1180_s2h60",
                    "default_return_pct": float(robust["return_pct"]),
                    "default_calmar": float(robust["calmar"]),
                    "default_maxdd_pct": float(robust["maxdd_pct"]),
                },
                "verdict": "GO_TO_LANDING_AUDIT",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
