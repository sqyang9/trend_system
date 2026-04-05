#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Walk-forward audit for the combo mainline promotion."""

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
from v90_asset_management_system_aligned import compute_metrics
from v91_exposure_engine_e1_constant_mapping import extended_metrics

from system_defect_research.v171_volatility_proxy_system_upgrade import GRID, build_background, path_bundle, scenario_results
from v123_formal_launch_and_layer2_weight_audit import SCENARIOS


OUT_DIR = Path("system_defect_research")
REPORT_MD = OUT_DIR / "COMBO_WALKFORWARD_AUDIT.md"
SUMMARY_CSV = OUT_DIR / "combo_walkforward_split_summary.csv"
WINDOW_SELECTION_CSV = OUT_DIR / "combo_walkforward_window_selection.csv"
OOS_PATH_CSV = OUT_DIR / "combo_walkforward_oos_path.csv"
REPORT_JSON = OUT_DIR / "combo_walkforward_audit.json"
PLOTS_HTML = OUT_DIR / "COMBO_WALKFORWARD_AUDIT.html"

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
    ("W13", pd.Timestamp("2025-12-16 04:00:00", tz="UTC"), pd.Timestamp("2026-03-30 20:00:00", tz="UTC")),
]

SPLITS = [
    ("fit_W01_W06_validate_W07_W13", "W01", "W06", "W07", "W13"),
    ("fit_W01_W09_validate_W10_W13", "W01", "W09", "W10", "W13"),
]


@dataclass(frozen=True)
class CandidateResult:
    key: str
    label: str
    equity: pd.Series
    exposure: pd.Series


def metrics_for_slice(equity: pd.Series, exposure: pd.Series) -> Dict[str, float]:
    if equity.empty or len(equity) < 2:
        return {
            "return_pct": 0.0,
            "calmar": 0.0,
            "maxdd_pct": 0.0,
            "worst3m_pct": 0.0,
            "worst6m_pct": 0.0,
            "recovery_days": 0.0,
            "avg_total_exposure_pct": 0.0,
        }
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


def slice_series(series: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    return series[(series.index >= start) & (series.index <= end)].astype(float)


def pick_candidate(rows: List[dict]) -> dict:
    ordered = sorted(
        rows,
        key=lambda r: (
            r["train_calmar"],
            r["train_maxdd_pct"],
            r["train_return_pct"],
        ),
        reverse=True,
    )
    return ordered[0]


def stitch_segments(segments: List[tuple[pd.Series, pd.Series, str]]) -> tuple[pd.Series, pd.Series, pd.Series]:
    stitched_eq_parts: list[pd.Series] = []
    stitched_ex_parts: list[pd.Series] = []
    stitched_pick_parts: list[pd.Series] = []
    level = 100.0
    for i, (eq, ex, pick) in enumerate(segments):
        if eq.empty:
            continue
        rebased = level * (eq / float(eq.iloc[0]))
        if i > 0:
            rebased = rebased.iloc[1:]
            ex = ex.iloc[1:]
        if rebased.empty:
            continue
        level = float(rebased.iloc[-1])
        stitched_eq_parts.append(rebased)
        stitched_ex_parts.append(ex.astype(float))
        stitched_pick_parts.append(pd.Series([pick] * len(rebased), index=rebased.index, dtype="object"))
    if not stitched_eq_parts:
        return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype="object")
    return (
        pd.concat(stitched_eq_parts).sort_index(),
        pd.concat(stitched_ex_parts).sort_index(),
        pd.concat(stitched_pick_parts).sort_index(),
    )


def window_index(label: str) -> int:
    for i, (name, _, _) in enumerate(WINDOWS):
        if name == label:
            return i
    raise KeyError(label)


def run_static_split(candidates: Dict[str, CandidateResult], split_name: str, train_start: str, train_end: str, val_start: str, val_end: str) -> tuple[dict, List[dict]]:
    ts = WINDOWS[window_index(train_start)][1]
    te = WINDOWS[window_index(train_end)][2]
    vs = WINDOWS[window_index(val_start)][1]
    ve = WINDOWS[window_index(val_end)][2]

    rows: List[dict] = []
    for cand in GRID:
        result = candidates[cand.key]
        train_eq = slice_series(result.equity, ts, te)
        train_ex = slice_series(result.exposure, ts, te)
        val_eq = slice_series(result.equity, vs, ve)
        val_ex = slice_series(result.exposure, vs, ve)
        train_m = metrics_for_slice(train_eq, train_ex)
        val_m = metrics_for_slice(val_eq, val_ex)
        rows.append(
            {
                "split": split_name,
                "candidate": cand.key,
                "label": cand.label,
                "selection_type": "static",
                "train_windows": f"{train_start}-{train_end}",
                "validation_windows": f"{val_start}-{val_end}",
                "train_return_pct": train_m["return_pct"],
                "train_calmar": train_m["calmar"],
                "train_maxdd_pct": train_m["maxdd_pct"],
                "validation_return_pct": val_m["return_pct"],
                "validation_calmar": val_m["calmar"],
                "validation_maxdd_pct": val_m["maxdd_pct"],
                "validation_avg_total_exposure_pct": val_m["avg_total_exposure_pct"],
            }
        )

    selected = pick_candidate(rows)
    baseline = next(r for r in rows if r["candidate"] == "baseline")
    combo = next(r for r in rows if r["candidate"] == "combo_all_hv85")
    summary = {
        "split": split_name,
        "mode": "static_freeze",
        "train_windows": f"{train_start}-{train_end}",
        "validation_windows": f"{val_start}-{val_end}",
        "selected_candidate": selected["candidate"],
        "selected_label": selected["label"],
        "train_return_pct": selected["train_return_pct"],
        "train_calmar": selected["train_calmar"],
        "train_maxdd_pct": selected["train_maxdd_pct"],
        "validation_return_pct": selected["validation_return_pct"],
        "validation_calmar": selected["validation_calmar"],
        "validation_maxdd_pct": selected["validation_maxdd_pct"],
        "d_validation_return_vs_baseline_pp": selected["validation_return_pct"] - baseline["validation_return_pct"],
        "d_validation_calmar_vs_baseline": selected["validation_calmar"] - baseline["validation_calmar"],
        "d_validation_maxdd_vs_baseline_pp": selected["validation_maxdd_pct"] - baseline["validation_maxdd_pct"],
        "combo_validation_return_pct": combo["validation_return_pct"],
        "combo_validation_calmar": combo["validation_calmar"],
        "combo_validation_maxdd_pct": combo["validation_maxdd_pct"],
        "combo_d_validation_return_vs_baseline_pp": combo["validation_return_pct"] - baseline["validation_return_pct"],
        "combo_d_validation_calmar_vs_baseline": combo["validation_calmar"] - baseline["validation_calmar"],
        "combo_d_validation_maxdd_vs_baseline_pp": combo["validation_maxdd_pct"] - baseline["validation_maxdd_pct"],
    }
    return summary, rows


def run_expanding_walkforward(candidates: Dict[str, CandidateResult]) -> tuple[dict, List[dict], pd.Series, pd.Series, pd.Series]:
    window_rows: List[dict] = []
    segments: List[tuple[pd.Series, pd.Series, str]] = []
    for val_idx in range(6, len(WINDOWS)):
        val_name, vs, ve = WINDOWS[val_idx]
        train_start = WINDOWS[0][0]
        train_end = WINDOWS[val_idx - 1][0]

        rows = []
        ts = WINDOWS[0][1]
        te = WINDOWS[val_idx - 1][2]
        for cand in GRID:
            result = candidates[cand.key]
            train_eq = slice_series(result.equity, ts, te)
            train_ex = slice_series(result.exposure, ts, te)
            val_eq = slice_series(result.equity, vs, ve)
            val_ex = slice_series(result.exposure, vs, ve)
            train_m = metrics_for_slice(train_eq, train_ex)
            val_m = metrics_for_slice(val_eq, val_ex)
            rows.append(
                {
                    "split": "expanding_walkforward",
                    "candidate": cand.key,
                    "label": cand.label,
                    "selection_type": "window",
                    "train_windows": f"{train_start}-{train_end}",
                    "validation_windows": val_name,
                    "train_return_pct": train_m["return_pct"],
                    "train_calmar": train_m["calmar"],
                    "train_maxdd_pct": train_m["maxdd_pct"],
                    "validation_return_pct": val_m["return_pct"],
                    "validation_calmar": val_m["calmar"],
                    "validation_maxdd_pct": val_m["maxdd_pct"],
                    "validation_avg_total_exposure_pct": val_m["avg_total_exposure_pct"],
                }
            )
        selected = pick_candidate(rows)
        picked_result = candidates[selected["candidate"]]
        val_eq = slice_series(picked_result.equity, vs, ve)
        val_ex = slice_series(picked_result.exposure, vs, ve)
        segments.append((val_eq, val_ex, selected["candidate"]))
        selected["selected_for_window"] = True
        window_rows.extend(rows)

    stitched_eq, stitched_ex, picked_series = stitch_segments(segments)
    stitched_metrics = metrics_for_slice(stitched_eq, stitched_ex)
    baseline_eq, baseline_ex, _ = stitch_segments(
        [
            (slice_series(candidates["baseline"].equity, start, end), slice_series(candidates["baseline"].exposure, start, end), "baseline")
            for _, start, end in WINDOWS[6:]
        ]
    )
    combo_eq, combo_ex, _ = stitch_segments(
        [
            (slice_series(candidates["combo_all_hv85"].equity, start, end), slice_series(candidates["combo_all_hv85"].exposure, start, end), "combo_all_hv85")
            for _, start, end in WINDOWS[6:]
        ]
    )
    baseline_metrics = metrics_for_slice(baseline_eq, baseline_ex)
    combo_metrics = metrics_for_slice(combo_eq, combo_ex)
    summary = {
        "split": "expanding_walkforward",
        "mode": "expanding_walkforward",
        "train_windows": "W01-expanding",
        "validation_windows": "W07-W13",
        "selected_candidate": "window_by_window_reselect",
        "selected_label": "Expanding walk-forward stitched OOS",
        "train_return_pct": float("nan"),
        "train_calmar": float("nan"),
        "train_maxdd_pct": float("nan"),
        "validation_return_pct": stitched_metrics["return_pct"],
        "validation_calmar": stitched_metrics["calmar"],
        "validation_maxdd_pct": stitched_metrics["maxdd_pct"],
        "d_validation_return_vs_baseline_pp": stitched_metrics["return_pct"] - baseline_metrics["return_pct"],
        "d_validation_calmar_vs_baseline": stitched_metrics["calmar"] - baseline_metrics["calmar"],
        "d_validation_maxdd_vs_baseline_pp": stitched_metrics["maxdd_pct"] - baseline_metrics["maxdd_pct"],
        "combo_validation_return_pct": combo_metrics["return_pct"],
        "combo_validation_calmar": combo_metrics["calmar"],
        "combo_validation_maxdd_pct": combo_metrics["maxdd_pct"],
        "combo_d_validation_return_vs_baseline_pp": combo_metrics["return_pct"] - baseline_metrics["return_pct"],
        "combo_d_validation_calmar_vs_baseline": combo_metrics["calmar"] - baseline_metrics["calmar"],
        "combo_d_validation_maxdd_vs_baseline_pp": combo_metrics["maxdd_pct"] - baseline_metrics["maxdd_pct"],
    }
    return summary, window_rows, stitched_eq, baseline_eq, combo_eq


def write_plot(oos_df: pd.DataFrame) -> None:
    fig = go.Figure()
    for key, label, color in [
        ("baseline_oos", "Baseline stitched OOS", "#0f172a"),
        ("combo_oos", "Current combo stitched OOS", "#16a34a"),
        ("wf_oos", "Expanding walk-forward stitched OOS", "#0ea5e9"),
    ]:
        sub = oos_df[oos_df["series"] == key]
        fig.add_trace(go.Scatter(x=sub["timestamp"], y=sub["equity"], mode="lines", name=label, line=dict(width=2.0, color=color)))
    fig.update_layout(template="plotly_white", hovermode="x unified", height=620, title="Combo Walk-Forward OOS Equity")
    fig.update_yaxes(title_text="Rebased OOS Equity")
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def write_report(summary_df: pd.DataFrame, selection_df: pd.DataFrame) -> None:
    split_a = summary_df[summary_df["split"] == "fit_W01_W06_validate_W07_W13"].iloc[0]
    split_b = summary_df[summary_df["split"] == "fit_W01_W09_validate_W10_W13"].iloc[0]
    wf = summary_df[summary_df["split"] == "expanding_walkforward"].iloc[0]

    wf_selected = selection_df[
        (selection_df["split"] == "expanding_walkforward")
        & (selection_df["selection_type"] == "window")
    ].sort_values("validation_windows")

    lines = [
        "# Combo Walk-Forward Audit",
        "",
        "## Scope",
        "",
        "- Mainline not changed.",
        "- This is a freeze-date / walk-forward credibility audit for the latest combo promotion.",
        "- It does not attempt to re-open the older mother-line parameter history (`EMA250`, `close3`, `ATR 3.2 / 2.2`).",
        "- It only tests whether the latest volatility-proxy promotion family looks materially weaker once candidate selection is forced to happen before later windows.",
        "",
        "## Candidate Family Under Test",
        "",
        "- `baseline` = pre-combo current mainline replay",
        "- `p0_atrvt_s2`",
        "- `p0_atrvt_all`",
        "- `p1_hv85_coregate`",
        "- `p1_hv90_coregate`",
        "- `combo_s2_hv85`",
        "- `combo_all_hv85`",
        "",
        "## Selection Rule",
        "",
        "- Training winner is selected by:",
        "  - higher `Calmar`",
        "  - then better `MaxDD`",
        "  - then higher `Return`",
        "- This is intentionally simple and stable; the goal is credibility, not re-optimization.",
        "",
        "## Static Freeze Splits",
        "",
        "| Split | Selected | Train Return% | Train Calmar | Train MaxDD% | Validate Return% | Validate Calmar | Validate MaxDD% | dCalmar vs Baseline |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in [split_a, split_b]:
        lines.append(
            f"| {row['split']} | {row['selected_label']} | {row['train_return_pct']:.2f} | {row['train_calmar']:.3f} | "
            f"{row['train_maxdd_pct']:.2f} | {row['validation_return_pct']:.2f} | {row['validation_calmar']:.3f} | "
            f"{row['validation_maxdd_pct']:.2f} | {row['d_validation_calmar_vs_baseline']:+.3f} |"
        )

    lines.extend(
        [
            "",
            "## Expanding Walk-Forward",
            "",
            f"- Stitched OOS windows: `W07-W13`.",
            f"- Expanding walk-forward stitched OOS: `Return {wf['validation_return_pct']:.2f}% / Calmar {wf['validation_calmar']:.3f} / MaxDD {wf['validation_maxdd_pct']:.2f}%`.",
            f"- Baseline stitched OOS delta: `dReturn {wf['d_validation_return_vs_baseline_pp']:+.2f}pp / dCalmar {wf['d_validation_calmar_vs_baseline']:+.3f} / dMaxDD {wf['d_validation_maxdd_vs_baseline_pp']:+.2f}pp`.",
            f"- Current combo stitched OOS on the same windows: `Return {wf['combo_validation_return_pct']:.2f}% / Calmar {wf['combo_validation_calmar']:.3f} / MaxDD {wf['combo_validation_maxdd_pct']:.2f}%`.",
            "",
            "Window-by-window picks:",
            "",
            "| Validation Window | Training Span | Selected Candidate | Validation Calmar | Validation Return% |",
            "| --- | --- | --- | --- | --- |",
        ]
    )

    for _, row in wf_selected.iterrows():
        is_sel = pick_candidate(
            selection_df[
                (selection_df["split"] == "expanding_walkforward")
                & (selection_df["validation_windows"] == row["validation_windows"])
            ].to_dict("records")
        )
        if row["candidate"] != is_sel["candidate"]:
            continue
        lines.append(
            f"| {row['validation_windows']} | {row['train_windows']} | {row['label']} | {row['validation_calmar']:.3f} | {row['validation_return_pct']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Readout",
            "",
            f"- `W01-W06 -> W07-W13` freeze selected `{split_a['selected_candidate']}` and validated at `Return {split_a['validation_return_pct']:.2f}% / Calmar {split_a['validation_calmar']:.3f} / MaxDD {split_a['validation_maxdd_pct']:.2f}%`.",
            f"- `W01-W09 -> W10-W13` freeze selected `{split_b['selected_candidate']}` and validated at `Return {split_b['validation_return_pct']:.2f}% / Calmar {split_b['validation_calmar']:.3f} / MaxDD {split_b['validation_maxdd_pct']:.2f}%`.",
            f"- Current promoted combo on those same validations delivered `W07-W13 Calmar {split_a['combo_validation_calmar']:.3f}` and `W10-W13 Calmar {split_b['combo_validation_calmar']:.3f}`.",
            "",
            "## Verdict",
            "",
            "- If the frozen-selection winner and the promoted combo remain close on later windows, the promotion looks less likely to be a pure in-sample artifact.",
            "- If the frozen-selection winner flips away from combo and later OOS also clearly rejects combo, then the promotion should be treated as more fragile.",
            "- This audit is about the latest combo package only; it is not a full mother-line parameter archaeology.",
        ]
    )

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    background = build_background(df_4h)
    scenario = next(s for s in SCENARIOS if s["name"] == "default")
    results = scenario_results(df_5m, df_4h, background, scenario)

    candidates = {
        cand.key: CandidateResult(
            key=cand.key,
            label=cand.label,
            equity=results[cand.key]["combo"]["combo_equity"].astype(float),
            exposure=results[cand.key]["combo"]["combo_exposure"].astype(float),
        )
        for cand in GRID
    }

    summary_rows: List[dict] = []
    selection_rows: List[dict] = []
    for split in SPLITS:
        summary, rows = run_static_split(candidates, *split)
        summary_rows.append(summary)
        selection_rows.extend(rows)

    wf_summary, wf_rows, wf_eq, baseline_eq, combo_eq = run_expanding_walkforward(candidates)
    summary_rows.append(wf_summary)
    selection_rows.extend(wf_rows)

    summary_df = pd.DataFrame(summary_rows)
    selection_df = pd.DataFrame(selection_rows)
    SUMMARY_CSV.write_text(summary_df.to_csv(index=False), encoding="utf-8")
    WINDOW_SELECTION_CSV.write_text(selection_df.to_csv(index=False), encoding="utf-8")

    oos_df = pd.concat(
        [
            pd.DataFrame({"timestamp": baseline_eq.index, "series": "baseline_oos", "equity": baseline_eq.values}),
            pd.DataFrame({"timestamp": combo_eq.index, "series": "combo_oos", "equity": combo_eq.values}),
            pd.DataFrame({"timestamp": wf_eq.index, "series": "wf_oos", "equity": wf_eq.values}),
        ],
        ignore_index=True,
    )
    OOS_PATH_CSV.write_text(oos_df.to_csv(index=False), encoding="utf-8")
    write_plot(oos_df)
    write_report(summary_df, selection_df)

    payload = {
        "summary_csv": str(SUMMARY_CSV),
        "selection_csv": str(WINDOW_SELECTION_CSV),
        "oos_path_csv": str(OOS_PATH_CSV),
        "report_md": str(REPORT_MD),
        "plot_html": str(PLOTS_HTML),
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
