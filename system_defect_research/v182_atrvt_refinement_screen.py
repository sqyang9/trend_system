#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Focused ATRVT refinement screen around H60/H90 and nearby contracts."""

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
REPORT_MD = OUT_DIR / "ATRVT_REFINEMENT_FOCUSED_SCREEN.md"
SUMMARY_CSV = OUT_DIR / "atrvt_refinement_focused_summary.csv"
DETAIL_CSV = OUT_DIR / "atrvt_refinement_focused_detail.csv"
JSON_OUT = OUT_DIR / "atrvt_refinement_focused_screen.json"

WINDOWS = [
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

SPLITS = [
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
    return Candidate(key, f"{days}d med / {clip_min:.2f}-{clip_max:.2f} both", AtrCandidate(key, f"{days}d med / {clip_min:.2f}-{clip_max:.2f} both", spec, spec))


def asym(key: str, s1_days: int, s2_days: int, s1_clip_min: float = 0.35, s1_clip_max: float = 1.50, s2_clip_min: float = 0.35, s2_clip_max: float = 1.50) -> Candidate:
    s1 = ScaleSpec(s1_days, "median", s1_clip_min, s1_clip_max)
    s2 = ScaleSpec(s2_days, "median", s2_clip_min, s2_clip_max)
    return Candidate(key, f"S1 {s1_days}d {s1_clip_min:.2f}-{s1_clip_max:.2f} / S2 {s2_days}d {s2_clip_min:.2f}-{s2_clip_max:.2f}", AtrCandidate(key, "asym", s1, s2))


CANDIDATES: List[Candidate] = [
    sym("base180", 180),
    sym("h120", 120),
    sym("h90", 90),
    sym("h75", 75),
    sym("h60", 60),
    sym("h45", 45),
    sym("h90_clip125", 90, 0.35, 1.25),
    sym("h60_clip135", 60, 0.35, 1.35),
    sym("h60_clip165", 60, 0.35, 1.65),
    sym("h60_clip045", 60, 0.45, 1.50),
    asym("s1h60_s2h90", 60, 90),
    asym("s1h90_s2h60", 90, 60),
    asym("s1h60_s2180", 60, 180),
    asym("s1180_s2h60", 180, 60),
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
        "avg_total_exposure_pct": float(exposure.mean() * 100.0),
    }


def window_mask(index: pd.Index, names: List[str]) -> pd.Series:
    mask = pd.Series(False, index=index)
    for label, start, end in WINDOWS:
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

    detail_rows = []
    for scenario_name, result_map in scenario_maps.items():
        for candidate in CANDIDATES:
            bundle = result_map[candidate.key]
            combo = bundle["combo"]
            detail_rows.append(
                {
                    "candidate": candidate.key,
                    "label": candidate.label,
                    "scenario": scenario_name,
                    "return_pct": float(combo["metrics"]["TotalReturn_pct"]),
                    "calmar": float(combo["metrics"]["Calmar"]),
                    "maxdd_pct": float(combo["metrics"]["MaxDD_pct"]),
                    "worst6m_pct": float(combo["path"]["worst_6m_cluster_return_pct"]),
                    "recovery_days": float(combo["path"]["recovery_days_from_maxdd"]),
                    "avg_total_exposure_pct": float(combo["combo_exposure"].mean() * 100.0),
                    "w06_dd_over_avg_exposure_pct": float(w06_metrics(combo)["w06_dd_over_avg_exposure_pct"]),
                    "w11_avg_total_exposure": float(bundle["w11"]["w11_avg_total_exposure"]),
                    "avg_s1_scale": float(bundle["avg_s1_scale"]),
                    "avg_s2_scale": float(bundle["avg_s2_scale"]),
                }
            )
    detail_df = pd.DataFrame(detail_rows)

    split_frames = []
    default_map = scenario_maps["default"]
    for split_name, train_windows, validate_windows in SPLITS:
        rows = []
        for candidate in CANDIDATES:
            result = evaluate_train_validate(default_map[candidate.key], train_windows, validate_windows)
            rows.append(
                {
                    "split": split_name,
                    "candidate": candidate.key,
                    "train_return_pct": result["train"]["return_pct"],
                    "train_calmar": result["train"]["calmar"],
                    "validate_return_pct": result["validate"]["return_pct"],
                    "validate_calmar": result["validate"]["calmar"],
                    "validate_maxdd_pct": result["validate"]["maxdd_pct"],
                }
            )
        split_frames.append(pd.DataFrame(rows))
    split_df = pd.concat(split_frames, ignore_index=True)

    summary_rows = []
    for candidate in CANDIDATES:
        default = detail_df[(detail_df["candidate"] == candidate.key) & (detail_df["scenario"] == "default")].iloc[0]
        stress = detail_df[(detail_df["candidate"] == candidate.key) & (detail_df["scenario"] == "stress")].iloc[0]
        harsh = detail_df[(detail_df["candidate"] == candidate.key) & (detail_df["scenario"] == "harsh_friction")].iloc[0]
        split1 = split_df[(split_df["candidate"] == candidate.key) & (split_df["split"] == SPLITS[0][0])].iloc[0]
        split2 = split_df[(split_df["candidate"] == candidate.key) & (split_df["split"] == SPLITS[1][0])].iloc[0]
        summary_rows.append(
            {
                "candidate": candidate.key,
                "label": candidate.label,
                "default_return_pct": float(default["return_pct"]),
                "default_calmar": float(default["calmar"]),
                "default_maxdd_pct": float(default["maxdd_pct"]),
                "stress_calmar": float(stress["calmar"]),
                "harsh_calmar": float(harsh["calmar"]),
                "w06_dd_over_avg_exposure_pct": float(default["w06_dd_over_avg_exposure_pct"]),
                "w11_avg_total_exposure": float(default["w11_avg_total_exposure"]),
                "split1_validate_return_pct": float(split1["validate_return_pct"]),
                "split1_validate_calmar": float(split1["validate_calmar"]),
                "split1_validate_maxdd_pct": float(split1["validate_maxdd_pct"]),
                "split2_validate_return_pct": float(split2["validate_return_pct"]),
                "split2_validate_calmar": float(split2["validate_calmar"]),
                "split2_validate_maxdd_pct": float(split2["validate_maxdd_pct"]),
                "wf_calmar_avg": float((split1["validate_calmar"] + split2["validate_calmar"]) / 2.0),
            }
        )
    summary_df = pd.DataFrame(summary_rows).sort_values(["wf_calmar_avg", "default_calmar", "default_return_pct"], ascending=[False, False, False]).reset_index(drop=True)

    top_default = summary_df.sort_values(["default_calmar", "default_return_pct"], ascending=[False, False]).head(8)
    top_wf = summary_df.sort_values(["wf_calmar_avg", "split1_validate_calmar", "split2_validate_calmar"], ascending=[False, False, False]).head(8)
    h60 = summary_df[summary_df["candidate"] == "h60"].iloc[0]
    h90 = summary_df[summary_df["candidate"] == "h90"].iloc[0]

    lines = [
        "# ATRVT Refinement Focused Screen",
        "",
        "- Scope: keep the corrected combo mainline fixed and only refine ATRVT around `H60/H90` plus nearby contracts.",
        "- Candidate families in this screen:",
        "  - symmetric horizons `45 / 60 / 75 / 90 / 120 / 180`",
        "  - light clip tweaks around `H60/H90`",
        "  - `S1/S2` asymmetric horizons",
        "",
        "## Top By Default",
        "",
        "| Candidate | Return% | Calmar | MaxDD% | Stress Calmar | Harsh Calmar | W06 DD/Exp | W11 AvgExp | WF Avg Calmar |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in top_default.iterrows():
        lines.append(
            f"| {row['label']} | {row['default_return_pct']:.2f} | {row['default_calmar']:.3f} | {row['default_maxdd_pct']:.2f} | "
            f"{row['stress_calmar']:.3f} | {row['harsh_calmar']:.3f} | {row['w06_dd_over_avg_exposure_pct']:.1f}% | "
            f"{row['w11_avg_total_exposure']:.3f} | {row['wf_calmar_avg']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Top By Walk-Forward Average Calmar",
            "",
            "| Candidate | Split1 Val Ret% | Split1 Val Calmar | Split2 Val Ret% | Split2 Val Calmar | Default Calmar |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in top_wf.iterrows():
        lines.append(
            f"| {row['label']} | {row['split1_validate_return_pct']:.2f} | {row['split1_validate_calmar']:.3f} | "
            f"{row['split2_validate_return_pct']:.2f} | {row['split2_validate_calmar']:.3f} | {row['default_calmar']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Anchor Readout",
            "",
            f"- `H90`: `Return {h90['default_return_pct']:.2f}% / Calmar {h90['default_calmar']:.3f} / MaxDD {h90['default_maxdd_pct']:.2f}%`; walk-forward avg Calmar `{h90['wf_calmar_avg']:.3f}`.",
            f"- `H60`: `Return {h60['default_return_pct']:.2f}% / Calmar {h60['default_calmar']:.3f} / MaxDD {h60['default_maxdd_pct']:.2f}%`; walk-forward avg Calmar `{h60['wf_calmar_avg']:.3f}`.",
            "",
            "## Interpretation Hints",
            "",
            "- If a contract wins default but falls behind on both freeze-date splits, treat it as economics-first rather than promotion-ready.",
            "- If an asymmetric contract keeps most of the H60 economics while repairing freeze-date splits, that is the most interesting follow-up path.",
        ]
    )

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary_df.to_csv(SUMMARY_CSV, index=False)
    detail_df.to_csv(DETAIL_CSV, index=False)
    JSON_OUT.write_text(
        json.dumps(
            {
                "top_default": top_default[["candidate", "default_return_pct", "default_calmar", "default_maxdd_pct", "wf_calmar_avg"]].to_dict("records"),
                "top_walkforward": top_wf[["candidate", "split1_validate_calmar", "split2_validate_calmar", "wf_calmar_avg", "default_calmar"]].to_dict("records"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
