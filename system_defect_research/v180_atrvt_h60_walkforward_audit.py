#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Walk-forward audit for ATRVT 180d vs 90d vs 60d."""

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

from system_defect_research.v171_volatility_proxy_system_upgrade import path_bundle, build_formal_bundle
from system_defect_research.v176_atrvt_refinement_screen import (
    Candidate as AtrCandidate,
    ScaleSpec,
    build_combo_core,
    evaluate_candidate,
)
from v123_formal_launch_and_layer2_weight_audit import SCENARIOS


OUT_DIR = Path("system_defect_research")
REPORT_MD = OUT_DIR / "ATRVT_H60_WALKFORWARD_AUDIT.md"
SUMMARY_CSV = OUT_DIR / "atrvt_h60_walkforward_split_summary.csv"
WINDOWS_CSV = OUT_DIR / "atrvt_h60_walkforward_window_selection.csv"
OOS_CSV = OUT_DIR / "atrvt_h60_walkforward_oos_path.csv"
SUMMARY_JSON = OUT_DIR / "atrvt_h60_walkforward_audit.json"


@dataclass(frozen=True)
class Candidate:
    key: str
    label: str
    atr: AtrCandidate


CANDIDATES: List[Candidate] = [
    Candidate(
        "combo_base180",
        "180d med / 0.35-1.50 both",
        AtrCandidate("combo_base180", "Reference: 180d med / 0.35-1.50 both", ScaleSpec(180, "median", 0.35, 1.50), ScaleSpec(180, "median", 0.35, 1.50)),
    ),
    Candidate(
        "combo_h90",
        "90d med / 0.35-1.50 both",
        AtrCandidate("combo_h90", "Reference: 90d med / 0.35-1.50 both", ScaleSpec(90, "median", 0.35, 1.50), ScaleSpec(90, "median", 0.35, 1.50)),
    ),
    Candidate(
        "combo_h60",
        "60d med / 0.35-1.50 both",
        AtrCandidate("combo_h60", "Challenger: 60d med / 0.35-1.50 both", ScaleSpec(60, "median", 0.35, 1.50), ScaleSpec(60, "median", 0.35, 1.50)),
    ),
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
    train_eq = eq.loc[train_mask]
    train_ex = ex.loc[train_mask]
    val_eq = eq.loc[val_mask]
    val_ex = ex.loc[val_mask]
    return {
        "train": summarize_segment(train_eq, train_ex),
        "validate": summarize_segment(val_eq, val_ex),
    }


def choose_train_winner(rows: List[dict]) -> dict:
    return sorted(rows, key=lambda r: (r["train_calmar"], r["train_return_pct"]), reverse=True)[0]


def stitch_oos(default_map: Dict[str, dict]) -> tuple[pd.Series, pd.Series, List[dict]]:
    selections = []
    stitched_eq = None
    stitched_ex = None
    for i in range(6, len(WINDOWS)):
        train_names = [w[0] for w in WINDOWS[:i]]
        val_name, val_start, val_end = WINDOWS[i]
        candidates = []
        for candidate in CANDIDATES:
            res = evaluate_train_validate(default_map[candidate.key], train_names, [val_name])
            candidates.append(
                {
                    "candidate": candidate.key,
                    "label": candidate.label,
                    "train_calmar": res["train"]["calmar"],
                    "train_return_pct": res["train"]["return_pct"],
                    "validate_calmar": res["validate"]["calmar"],
                    "validate_return_pct": res["validate"]["return_pct"],
                    "validate_maxdd_pct": res["validate"]["maxdd_pct"],
                    "window": val_name,
                    "start": val_start,
                    "end": val_end,
                }
            )
        winner = choose_train_winner(candidates)
        selections.append(winner)
        eq = default_map[winner["candidate"]]["combo"]["combo_equity"]
        ex = default_map[winner["candidate"]]["combo"]["combo_exposure"]
        sub_eq = eq[(eq.index >= val_start) & (eq.index <= val_end)]
        sub_ex = ex[(ex.index >= val_start) & (ex.index <= val_end)]
        if stitched_eq is None:
            stitched_eq = sub_eq.copy()
            stitched_ex = sub_ex.copy()
        else:
            prev = float(stitched_eq.iloc[-1])
            rebased = sub_eq / float(sub_eq.iloc[0]) * prev
            stitched_eq = pd.concat([stitched_eq.iloc[:-1], rebased])
            stitched_ex = pd.concat([stitched_ex.iloc[:-1], sub_ex])
    return stitched_eq, stitched_ex, selections


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    scenario = next(s for s in SCENARIOS if s["name"] == "default")
    formal_bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])
    core_sim, instability = build_combo_core(df_5m, df_4h, scenario)

    default_map: Dict[str, dict] = {}
    for candidate in CANDIDATES:
        default_map[candidate.key] = evaluate_candidate(df_4h, formal_bundle, core_sim, instability, candidate.atr)

    split_rows = []
    for split_name, train_windows, validate_windows in SPLITS:
        candidates = []
        for candidate in CANDIDATES:
            res = evaluate_train_validate(default_map[candidate.key], train_windows, validate_windows)
            candidates.append(
                {
                    "split": split_name,
                    "candidate": candidate.key,
                    "label": candidate.label,
                    "train_return_pct": res["train"]["return_pct"],
                    "train_calmar": res["train"]["calmar"],
                    "train_maxdd_pct": res["train"]["maxdd_pct"],
                    "validate_return_pct": res["validate"]["return_pct"],
                    "validate_calmar": res["validate"]["calmar"],
                    "validate_maxdd_pct": res["validate"]["maxdd_pct"],
                }
            )
        winner = choose_train_winner(candidates)
        winner_key = winner["candidate"]
        h60 = next(c for c in candidates if c["candidate"] == "combo_h60")
        h90 = next(c for c in candidates if c["candidate"] == "combo_h90")
        base = next(c for c in candidates if c["candidate"] == "combo_base180")
        split_rows.append(
            {
                "split": split_name,
                "selected_candidate": winner_key,
                "selected_label": winner["label"],
                "selected_train_return_pct": winner["train_return_pct"],
                "selected_train_calmar": winner["train_calmar"],
                "selected_validate_return_pct": winner["validate_return_pct"],
                "selected_validate_calmar": winner["validate_calmar"],
                "selected_validate_maxdd_pct": winner["validate_maxdd_pct"],
                "h60_validate_return_pct": h60["validate_return_pct"],
                "h60_validate_calmar": h60["validate_calmar"],
                "h60_validate_maxdd_pct": h60["validate_maxdd_pct"],
                "h90_validate_return_pct": h90["validate_return_pct"],
                "h90_validate_calmar": h90["validate_calmar"],
                "h90_validate_maxdd_pct": h90["validate_maxdd_pct"],
                "base180_validate_return_pct": base["validate_return_pct"],
                "base180_validate_calmar": base["validate_calmar"],
                "base180_validate_maxdd_pct": base["validate_maxdd_pct"],
            }
        )

    stitched_eq, stitched_ex, selections = stitch_oos(default_map)
    stitched_metrics = summarize_segment(stitched_eq, stitched_ex)

    selection_df = pd.DataFrame(selections)
    selection_df["selected_return_pct"] = selection_df["validate_return_pct"]
    selection_df["selected_calmar"] = selection_df["validate_calmar"]
    selection_df["selected_maxdd_pct"] = selection_df["validate_maxdd_pct"]
    selection_df = selection_df[
        [
            "window",
            "candidate",
            "label",
            "train_return_pct",
            "train_calmar",
            "validate_return_pct",
            "validate_calmar",
            "validate_maxdd_pct",
            "start",
            "end",
        ]
    ]

    base_oos = summarize_segment(
        default_map["combo_base180"]["combo"]["combo_equity"][window_mask(default_map["combo_base180"]["combo"]["combo_equity"].index, [w[0] for w in WINDOWS[6:]])],
        default_map["combo_base180"]["combo"]["combo_exposure"][window_mask(default_map["combo_base180"]["combo"]["combo_exposure"].index, [w[0] for w in WINDOWS[6:]])],
    )
    h90_oos = summarize_segment(
        default_map["combo_h90"]["combo"]["combo_equity"][window_mask(default_map["combo_h90"]["combo"]["combo_equity"].index, [w[0] for w in WINDOWS[6:]])],
        default_map["combo_h90"]["combo"]["combo_exposure"][window_mask(default_map["combo_h90"]["combo"]["combo_exposure"].index, [w[0] for w in WINDOWS[6:]])],
    )
    h60_oos = summarize_segment(
        default_map["combo_h60"]["combo"]["combo_equity"][window_mask(default_map["combo_h60"]["combo"]["combo_equity"].index, [w[0] for w in WINDOWS[6:]])],
        default_map["combo_h60"]["combo"]["combo_exposure"][window_mask(default_map["combo_h60"]["combo"]["combo_exposure"].index, [w[0] for w in WINDOWS[6:]])],
    )

    split_df = pd.DataFrame(split_rows)
    summary_payload = {
        "base180_oos": base_oos,
        "h90_oos": h90_oos,
        "h60_oos": h60_oos,
        "stitched_oos": stitched_metrics,
    }

    lines = [
        "# ATRVT H60 Walk-Forward Audit",
        "",
        "- Scope: corrected ATRVT lineage only.",
        "- Comparison set:",
        "  - `180d median / 0.35-1.50 both`",
        "  - `90d median / 0.35-1.50 both`",
        "  - `60d median / 0.35-1.50 both`",
        "",
        "## Split Summary",
        "",
        "| Split | Train Winner | Winner Val Return% | Winner Val Calmar | H60 Val Return% | H60 Val Calmar | H90 Val Return% | H90 Val Calmar | 180d Val Return% | 180d Val Calmar |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in split_df.iterrows():
        lines.append(
            f"| {row['split']} | {row['selected_label']} | {row['selected_validate_return_pct']:.2f} | {row['selected_validate_calmar']:.3f} | "
            f"{row['h60_validate_return_pct']:.2f} | {row['h60_validate_calmar']:.3f} | "
            f"{row['h90_validate_return_pct']:.2f} | {row['h90_validate_calmar']:.3f} | "
            f"{row['base180_validate_return_pct']:.2f} | {row['base180_validate_calmar']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## OOS Readout",
            "",
            f"- Fixed OOS `W07-W13`: 180d `{base_oos['return_pct']:.2f}% / {base_oos['calmar']:.3f} / {base_oos['maxdd_pct']:.2f}%`.",
            f"- Fixed OOS `W07-W13`: 90d `{h90_oos['return_pct']:.2f}% / {h90_oos['calmar']:.3f} / {h90_oos['maxdd_pct']:.2f}%`.",
            f"- Fixed OOS `W07-W13`: 60d `{h60_oos['return_pct']:.2f}% / {h60_oos['calmar']:.3f} / {h60_oos['maxdd_pct']:.2f}%`.",
            f"- Expanding stitched OOS: `{stitched_metrics['return_pct']:.2f}% / {stitched_metrics['calmar']:.3f} / {stitched_metrics['maxdd_pct']:.2f}%`.",
            "",
            "## Interpretation",
            "",
            "- This audit asks whether `H60` still survives freeze-date style evaluation, not whether it is the best in-sample default screen point.",
            "- If `H60` keeps winning or tying on the validation side, promotion credibility rises materially.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    SUMMARY_CSV.write_text(split_df.to_csv(index=False), encoding="utf-8")
    WINDOWS_CSV.write_text(selection_df.to_csv(index=False), encoding="utf-8")
    OOS_CSV.write_text(
        pd.DataFrame(
            [
                {"series": "base180_w07_w13", **base_oos},
                {"series": "h90_w07_w13", **h90_oos},
                {"series": "h60_w07_w13", **h60_oos},
                {"series": "stitched_selected", **stitched_metrics},
            ]
        ).to_csv(index=False),
        encoding="utf-8",
    )
    SUMMARY_JSON.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report_md": str(REPORT_MD), "summary_csv": str(SUMMARY_CSV), "selection_csv": str(WINDOWS_CSV), "oos_csv": str(OOS_CSV)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
