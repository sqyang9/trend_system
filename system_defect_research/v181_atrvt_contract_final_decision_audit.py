#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final decision audit for ATRVT contracts 180d vs 90d vs 60d."""

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
REPORT_MD = OUT_DIR / "ATRVT_CONTRACT_FINAL_DECISION_AUDIT.md"
SUMMARY_CSV = OUT_DIR / "atrvt_contract_final_decision_summary.csv"
ANNUAL_CSV = OUT_DIR / "atrvt_contract_final_decision_annual.csv"
WF_CSV = OUT_DIR / "atrvt_contract_final_decision_walkforward.csv"
JSON_OUT = OUT_DIR / "atrvt_contract_final_decision_audit.json"

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


CANDIDATES: List[Candidate] = [
    Candidate(
        "combo_180d",
        "Current corrected baseline: 180d med / 0.35-1.50 both",
        AtrCandidate("combo_180d", "Current corrected baseline: 180d med / 0.35-1.50 both", ScaleSpec(180, "median", 0.35, 1.50), ScaleSpec(180, "median", 0.35, 1.50)),
    ),
    Candidate(
        "combo_90d",
        "Balanced challenger: 90d med / 0.35-1.50 both",
        AtrCandidate("combo_90d", "Balanced challenger: 90d med / 0.35-1.50 both", ScaleSpec(90, "median", 0.35, 1.50), ScaleSpec(90, "median", 0.35, 1.50)),
    ),
    Candidate(
        "combo_60d",
        "Economics-first challenger: 60d med / 0.35-1.50 both",
        AtrCandidate("combo_60d", "Economics-first challenger: 60d med / 0.35-1.50 both", ScaleSpec(60, "median", 0.35, 1.50), ScaleSpec(60, "median", 0.35, 1.50)),
    ),
]


def summarize_segment(equity: pd.Series, exposure: pd.Series) -> dict:
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


def annual_metrics(equity: pd.Series, exposure: pd.Series) -> dict:
    return summarize_segment(equity, exposure)


def window_mask(index: pd.Index, names: List[str]) -> pd.Series:
    mask = pd.Series(False, index=index)
    for label, start, end in WINDOWS:
        if label in names:
            mask = mask | ((index >= start) & (index <= end))
    return mask


def evaluate_train_validate(system: dict, train_windows: List[str], validate_windows: List[str]) -> dict:
    eq = system["combo"]["combo_equity"]
    ex = system["combo"]["combo_exposure"]
    train_mask = window_mask(eq.index, train_windows)
    val_mask = window_mask(eq.index, validate_windows)
    return {
        "train": summarize_segment(eq.loc[train_mask], ex.loc[train_mask]),
        "validate": summarize_segment(eq.loc[val_mask], ex.loc[val_mask]),
    }


def choose_train_winner(rows: List[dict]) -> dict:
    return sorted(rows, key=lambda r: (r["train_calmar"], r["train_return_pct"]), reverse=True)[0]


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


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    scenario_maps: Dict[str, Dict[str, dict]] = {}
    for scenario in SCENARIOS:
        formal_bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])
        core_sim, instability = build_combo_core(df_5m, df_4h, scenario)
        results: Dict[str, dict] = {}
        for candidate in CANDIDATES:
            results[candidate.key] = evaluate_candidate(df_4h, formal_bundle, core_sim, instability, candidate.atr)
        scenario_maps[scenario["name"]] = results

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
                    "worst3m_pct": float(combo["path"]["worst_3m_cluster_return_pct"]),
                    "worst6m_pct": float(combo["path"]["worst_6m_cluster_return_pct"]),
                    "recovery_days": float(combo["path"]["recovery_days_from_maxdd"]),
                    "avg_total_exposure_pct": float(combo["combo_exposure"].mean() * 100.0),
                    "w06_dd_over_avg_exposure_pct": float(w06["w06_dd_over_avg_exposure_pct"]),
                    "w11_avg_total_exposure": float(bundle["w11"]["w11_avg_total_exposure"]),
                    "avg_s1_scale": float(bundle["avg_s1_scale"]),
                    "avg_s2_scale": float(bundle["avg_s2_scale"]),
                }
            )
    summary_df = pd.DataFrame(summary_rows)

    default_map = scenario_maps["default"]
    annual_rows = []
    for start in ANNUAL_STARTS:
        for candidate in CANDIDATES:
            system = default_map[candidate.key]["combo"]
            eq = system["combo_equity"][system["combo_equity"].index >= start]
            ex = system["combo_exposure"][system["combo_exposure"].index >= start]
            if eq.empty:
                continue
            annual_rows.append({"start": start.date().isoformat(), "candidate": candidate.key, "label": candidate.label, **annual_metrics(eq, ex)})
    annual_df = pd.DataFrame(annual_rows)

    wf_rows = []
    for split_name, train_windows, validate_windows in SPLITS:
        split_candidates = []
        for candidate in CANDIDATES:
            result = evaluate_train_validate(default_map[candidate.key], train_windows, validate_windows)
            split_candidates.append(
                {
                    "split": split_name,
                    "candidate": candidate.key,
                    "label": candidate.label,
                    "train_return_pct": result["train"]["return_pct"],
                    "train_calmar": result["train"]["calmar"],
                    "train_maxdd_pct": result["train"]["maxdd_pct"],
                    "validate_return_pct": result["validate"]["return_pct"],
                    "validate_calmar": result["validate"]["calmar"],
                    "validate_maxdd_pct": result["validate"]["maxdd_pct"],
                }
            )
        winner = choose_train_winner(split_candidates)
        for row in split_candidates:
            row["selected_by_train"] = row["candidate"] == winner["candidate"]
            wf_rows.append(row)
    wf_df = pd.DataFrame(wf_rows)

    base = summary_df[(summary_df["scenario"] == "default") & (summary_df["candidate"] == "combo_180d")].iloc[0]
    h90 = summary_df[(summary_df["scenario"] == "default") & (summary_df["candidate"] == "combo_90d")].iloc[0]
    h60 = summary_df[(summary_df["scenario"] == "default") & (summary_df["candidate"] == "combo_60d")].iloc[0]
    h90_ann = annual_scorecard(annual_df, "combo_90d", "combo_180d")
    h60_ann = annual_scorecard(annual_df, "combo_60d", "combo_180d")

    split1 = wf_df[wf_df["split"] == "fit_W01_W06_validate_W07_W13"].set_index("candidate")
    split2 = wf_df[wf_df["split"] == "fit_W01_W09_validate_W10_W13"].set_index("candidate")

    lines = [
        "# ATRVT Contract Final Decision Audit",
        "",
        "## Scope",
        "",
        "- Mainline not changed.",
        "- This audit compares the three now-parameterized ATRVT contracts on the same shared implementation surface.",
        "- Core structure is held fixed:",
        "  - stable `close3`",
        "  - high-churn `strict EMA50 + breakout_4`",
        "  - `HV percentile >= 85` forces high-churn earlier",
        "",
        "## Default / Stress / Harsh",
        "",
        "| Candidate | Scenario | Return% | Calmar | MaxDD% | Worst6m | RecoveryDays | W06 DD/Exp | W11 AvgExp |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in CANDIDATES:
        for scenario in ["default", "stress", "harsh_friction"]:
            row = summary_df[(summary_df["scenario"] == scenario) & (summary_df["candidate"] == candidate.key)].iloc[0]
            lines.append(
                f"| {candidate.label} | {scenario} | {row['return_pct']:.2f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
                f"{row['worst6m_pct']:.2f} | {row['recovery_days']:.1f} | {row['w06_dd_over_avg_exposure_pct']:.1f}% | {row['w11_avg_total_exposure']:.3f} |"
            )

    lines.extend(
        [
            "",
            "## Annual Starts Vs Corrected 180d Baseline",
            "",
            f"- `90d` vs `180d`: Return better `{h90_ann['return_better']}/{h90_ann['n']}`, Calmar better `{h90_ann['calmar_better']}/{h90_ann['n']}`, MaxDD better `{h90_ann['maxdd_better']}/{h90_ann['n']}`.",
            f"- `60d` vs `180d`: Return better `{h60_ann['return_better']}/{h60_ann['n']}`, Calmar better `{h60_ann['calmar_better']}/{h60_ann['n']}`, MaxDD better `{h60_ann['maxdd_better']}/{h60_ann['n']}`.",
            "",
            "## Freeze-Date Walk-Forward",
            "",
            "| Split | Candidate | Train Calmar | Validate Return% | Validate Calmar | Validate MaxDD% | Selected By Train |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for _, row in wf_df.iterrows():
        lines.append(
            f"| {row['split']} | {row['label']} | {row['train_calmar']:.3f} | {row['validate_return_pct']:.2f} | "
            f"{row['validate_calmar']:.3f} | {row['validate_maxdd_pct']:.2f} | {'yes' if row['selected_by_train'] else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Corrected current baseline `180d`: `Return {base['return_pct']:.2f}% / Calmar {base['calmar']:.3f} / MaxDD {base['maxdd_pct']:.2f}%`.",
            f"- `90d` is the balanced challenger: `Return {h90['return_pct']:.2f}% / Calmar {h90['calmar']:.3f} / MaxDD {h90['maxdd_pct']:.2f}%`.",
            f"- `60d` is the economics-first challenger: `Return {h60['return_pct']:.2f}% / Calmar {h60['calmar']:.3f} / MaxDD {h60['maxdd_pct']:.2f}%`.",
            "",
            "## Verdict",
            "",
            "- `60d` is the strongest full-sample economics contract, and it also improves W06 burden materially.",
            "- But `60d` is not a clean freeze-date winner: in the early split `W01-W06 -> W07-W13`, both `180d` and `90d` validate better.",
            "- `90d` is a more balanced sibling, but it still does not dominate the corrected `180d` baseline on the earliest freeze-date split.",
            "- Promotion verdict: `HOLD_CURRENT_180D`.",
            "- Reserve ranking: `90d` first, `60d` second if the goal is freeze-date credibility; `60d` first if the goal is pure economics exploration.",
        ]
    )

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary_df.to_csv(SUMMARY_CSV, index=False)
    annual_df.to_csv(ANNUAL_CSV, index=False)
    wf_df.to_csv(WF_CSV, index=False)
    JSON_OUT.write_text(
        json.dumps(
            {
                "default": {
                    "180d": {"return_pct": float(base["return_pct"]), "calmar": float(base["calmar"]), "maxdd_pct": float(base["maxdd_pct"])},
                    "90d": {"return_pct": float(h90["return_pct"]), "calmar": float(h90["calmar"]), "maxdd_pct": float(h90["maxdd_pct"])},
                    "60d": {"return_pct": float(h60["return_pct"]), "calmar": float(h60["calmar"]), "maxdd_pct": float(h60["maxdd_pct"])},
                },
                "annual_vs_180d": {"90d": h90_ann, "60d": h60_ann},
                "verdict": "HOLD_CURRENT_180D",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
