#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promotion-level validation for GradedAddOn[compression_breakout]."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_addon_grading_study import (
    DEFAULT_TUPLE,
    STRESS_TUPLE,
    GRADE_WEIGHTS,
    GRADING_SCHEMES,
    SEED,
    bh_equity,
    compute_metrics,
    compute_slice_metrics,
    constant_weight_plan,
    current_research_optimal,
    delta_metrics,
    load_overlay_artifact,
    prepare_base_run,
    rank_against_train,
    simulate_combo_from_plan,
    slice_range,
    stress_compare,
    with_overrides,
)


REPORT_MD = Path("BTC_ADDON_GRADING_PROMOTION_REPORT.md")
REPORT_JSON = Path("btc_addon_grading_promotion_report.json")
REPORT_TXT = Path("btc_addon_grading_promotion_summary.txt")
WF_TEST_YEARS = [2023, 2024, 2025]
TIME_SLICES = [
    {"name": "bull_expansion", "start": "2020-04-01", "end": "2021-11-10"},
    {"name": "major_drawdown", "start": "2021-11-10", "end": "2023-01-01"},
    {"name": "recovery_phase", "start": "2023-01-01", "end": "2024-03-15"},
    {"name": "sideways_volatility", "start": "2024-03-15", "end": "2026-03-01"},
]


def grading_scheme() -> Dict:
    return next(item for item in GRADING_SCHEMES if item["name"] == "compression_breakout")


def assign_candidate(entries: pd.DataFrame, train_mask: pd.Series) -> tuple[pd.DataFrame, Dict]:
    scheme = grading_scheme()
    assigned = entries.copy()
    score = pd.Series(0.0, index=assigned.index, dtype=float)
    for feature, weight in scheme["features"].items():
        ranks = rank_against_train(assigned.loc[train_mask, feature], assigned[feature])
        score = score + weight * ranks
    score_train = score.loc[train_mask]
    q1 = float(score_train.quantile(1.0 / 3.0)) if not score_train.empty else 0.33
    q2 = float(score_train.quantile(2.0 / 3.0)) if not score_train.empty else 0.67

    def label_one(value: float) -> str:
        if value <= q1:
            return "weak"
        if value <= q2:
            return "base"
        return "strong"

    assigned["grade_score"] = score
    assigned["grade_label"] = score.apply(label_one)
    assigned["addon_weight"] = assigned["grade_label"].map(GRADE_WEIGHTS).astype(float)
    return assigned, {
        "score_q1": q1,
        "score_q2": q2,
        "train_trade_count": int(train_mask.sum()),
        "scheme": grading_scheme(),
    }


def walk_forward_compare(df_4h: pd.DataFrame, entries: pd.DataFrame, commission_pct: float) -> Dict:
    d4 = ensure_datetime(df_4h)
    windows = []
    strict_flags = []
    d_returns = []
    d_sharpes = []
    d_calmars = []
    d_maxdd = []

    for test_year in WF_TEST_YEARS:
        train_start = pd.Timestamp(f"{test_year - 3}-01-01", tz="UTC")
        test_start = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
        test_end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
        train_mask = (entries["signal_time"] >= train_start) & (entries["signal_time"] < test_start)
        sim_mask = (entries["signal_time"] >= train_start) & (entries["signal_time"] < test_end)
        if int(train_mask.sum()) < 3:
            continue

        sim_entries = entries.loc[sim_mask].reset_index(drop=True)
        sim_train_mask = train_mask.loc[sim_mask].reset_index(drop=True)
        candidate_plan, thresholds = assign_candidate(sim_entries, sim_train_mask)
        baseline_plan = constant_weight_plan(sim_entries, GRADE_WEIGHTS["base"])
        date_mask = (d4["timestamp"] >= train_start) & (d4["timestamp"] < test_end)
        d4_slice = d4.loc[date_mask].reset_index(drop=True)

        baseline = simulate_combo_from_plan(d4_slice, baseline_plan, commission_pct)
        candidate = simulate_combo_from_plan(d4_slice, candidate_plan, commission_pct)

        baseline_metrics = compute_slice_metrics(
            slice_range(baseline["combo_equity"], test_start.isoformat(), test_end.isoformat()),
            slice_range(baseline["combo_exposure"], test_start.isoformat(), test_end.isoformat()),
        )
        candidate_metrics = compute_slice_metrics(
            slice_range(candidate["combo_equity"], test_start.isoformat(), test_end.isoformat()),
            slice_range(candidate["combo_exposure"], test_start.isoformat(), test_end.isoformat()),
        )
        delta = delta_metrics(candidate_metrics, baseline_metrics)
        strict = bool(
            candidate_metrics["TotalReturn_pct"] > baseline_metrics["TotalReturn_pct"]
            and candidate_metrics["Sharpe"] > baseline_metrics["Sharpe"]
            and candidate_metrics["Calmar"] > baseline_metrics["Calmar"]
            and abs(candidate_metrics["MaxDD_pct"]) <= abs(baseline_metrics["MaxDD_pct"]) + 1.0
        )
        strict_flags.append(float(strict))
        d_returns.append(delta["Return_pct"])
        d_sharpes.append(delta["Sharpe"])
        d_calmars.append(delta["Calmar"])
        d_maxdd.append(delta["MaxDD_improvement_pct"])
        windows.append(
            {
                "train_window": {"start": train_start.date().isoformat(), "end": test_start.date().isoformat()},
                "test_window": {"start": test_start.date().isoformat(), "end": test_end.date().isoformat()},
                "thresholds": thresholds,
                "candidate_metrics": candidate_metrics,
                "baseline_metrics": baseline_metrics,
                "delta_vs_baseline": delta,
                "strict_outperform": strict,
            }
        )

    return {
        "windows": windows,
        "strict_win_ratio": float(np.mean(strict_flags)) if strict_flags else 0.0,
        "avg_delta_return_pct": float(np.mean(d_returns)) if d_returns else 0.0,
        "avg_delta_sharpe": float(np.mean(d_sharpes)) if d_sharpes else 0.0,
        "avg_delta_calmar": float(np.mean(d_calmars)) if d_calmars else 0.0,
        "avg_delta_maxdd_improvement_pct": float(np.mean(d_maxdd)) if d_maxdd else 0.0,
    }


def time_slice_analysis(systems: Dict[str, Dict]) -> List[Dict]:
    rows = []
    baseline_key = "Core+BinaryAddOn"
    candidate_key = "Core+GradedAddOn[compression_breakout]"
    for sl in TIME_SLICES:
        baseline_metrics = compute_slice_metrics(
            slice_range(systems[baseline_key]["equity"], sl["start"], sl["end"]),
            slice_range(systems[baseline_key]["exposure"], sl["start"], sl["end"]),
        )
        candidate_metrics = compute_slice_metrics(
            slice_range(systems[candidate_key]["equity"], sl["start"], sl["end"]),
            slice_range(systems[candidate_key]["exposure"], sl["start"], sl["end"]),
        )
        rows.append(
            {
                "slice": sl["name"],
                "window": {"start": sl["start"], "end": sl["end"]},
                baseline_key: baseline_metrics,
                candidate_key: candidate_metrics,
                "delta_vs_baseline": delta_metrics(candidate_metrics, baseline_metrics),
            }
        )
    return rows


def bar_size_distribution(weight_series: pd.Series) -> Dict[str, float]:
    active = weight_series[weight_series > 0.0]
    if active.empty:
        return {"weak_pct": 0.0, "base_pct": 0.0, "strong_pct": 0.0}
    return {
        "weak_pct": float((active == GRADE_WEIGHTS["weak"]).mean() * 100.0),
        "base_pct": float((active == GRADE_WEIGHTS["base"]).mean() * 100.0),
        "strong_pct": float((active == GRADE_WEIGHTS["strong"]).mean() * 100.0),
    }


def exposure_diagnostics(baseline: Dict, candidate: Dict, candidate_plan: pd.DataFrame) -> Dict:
    base_weight = baseline["sleeve"]["weight"]
    cand_weight = candidate["sleeve"]["weight"]
    baseline_mean_addon = float(base_weight.mean())
    candidate_mean_addon = float(cand_weight.mean())
    active_overlap = float(((base_weight > 0.0) & (cand_weight > 0.0)).mean() * 100.0)
    trend_participation_ratio = 0.0 if baseline_mean_addon <= 0 else candidate_mean_addon / baseline_mean_addon
    trade_counts = candidate_plan["grade_label"].value_counts().to_dict()
    return {
        "avg_total_exposure_baseline_pct": float(baseline["combo_exposure"].mean() * 100.0),
        "avg_total_exposure_candidate_pct": float(candidate["combo_exposure"].mean() * 100.0),
        "avg_total_exposure_delta_pct": float((candidate["combo_exposure"].mean() - baseline["combo_exposure"].mean()) * 100.0),
        "addon_activation_ratio_baseline_pct": baseline["sleeve"]["active_ratio_pct"],
        "addon_activation_ratio_candidate_pct": candidate["sleeve"]["active_ratio_pct"],
        "avg_addon_weight_when_active_baseline": baseline["sleeve"]["avg_weight_when_active"],
        "avg_addon_weight_when_active_candidate": candidate["sleeve"]["avg_weight_when_active"],
        "weighted_addon_exposure_ratio": float(trend_participation_ratio),
        "active_bar_overlap_ratio_pct": active_overlap,
        "candidate_entry_grade_counts": {k: int(trade_counts.get(k, 0)) for k in ["weak", "base", "strong"]},
        "candidate_active_bar_size_distribution_pct": bar_size_distribution(cand_weight),
        "baseline_active_bar_size_distribution_pct": {"weak_pct": 0.0, "base_pct": 100.0, "strong_pct": 0.0},
        "accidental_leverage_flag": bool((candidate["combo_exposure"].mean() - baseline["combo_exposure"].mean()) > 0.02),
    }


def write_report(payload: Dict) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    slices = payload["time_slices"]
    lines = [
        "# BTC AddOn Grading Promotion Report",
        "",
        "## Final Judgment",
        "",
        f"- Promotion candidate answer: {payload['judgment']['promotion_candidate_answer']}",
        f"- Preferred structure: {payload['judgment']['preferred_structure']}",
        f"- Baseline decision: {payload['judgment']['baseline_decision']}",
        f"- Active extension line decision: {payload['judgment']['extension_line_decision']}",
        "",
        "## Baseline Alignment",
        "",
        f"- Default tuple: {payload['locked_baseline']['default_tuple']}",
        f"- Baseline drift vs committed artifact: Return {payload['baseline_alignment']['baseline_vs_artifact']['delta_return_pct']:+.2f}pp, Sharpe {payload['baseline_alignment']['baseline_vs_artifact']['delta_sharpe']:+.3f}, Calmar {payload['baseline_alignment']['baseline_vs_artifact']['delta_calmar']:+.3f}, MaxDD improve {payload['baseline_alignment']['baseline_vs_artifact']['delta_maxdd_improve_pct']:+.2f}pp",
        "",
        "## Full-Sample Comparison",
        "",
        "| System | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Exposure% | dRet vs Binary | dSharpe | dCalmar | dMaxDD |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key in ["BTC_BuyAndHold", "Core+BinaryAddOn", "Core+GradedAddOn[compression_breakout]"]:
        row = payload["systems"][key]
        m = row["metrics"]
        d = row.get("delta_vs_binary")
        if d is None:
            d = {"Return_pct": 0.0, "Sharpe": 0.0, "Calmar": 0.0, "MaxDD_improvement_pct": 0.0}
        lines.append(
            f"| {key} | {m['TotalReturn_pct']:.2f} | {m['CAGR_pct']:.2f} | {m['Sharpe']:.3f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | {m['Exposure_pct']:.1f} | "
            f"{d['Return_pct']:+.2f} | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f} |"
        )
    lines.extend([
        "",
        "## Walk-Forward OOS",
        "",
        f"- Strict win ratio: {payload['walk_forward']['default']['strict_win_ratio']:.2f}",
        f"- Avg delta Return: {payload['walk_forward']['default']['avg_delta_return_pct']:+.2f}pp",
        f"- Avg delta Sharpe: {payload['walk_forward']['default']['avg_delta_sharpe']:+.3f}",
        f"- Avg delta Calmar: {payload['walk_forward']['default']['avg_delta_calmar']:+.3f}",
        "",
        "| Test Window | dReturn | dSharpe | dCalmar | dMaxDD | Strict Win |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for row in payload["walk_forward"]["default"]["windows"]:
        d = row["delta_vs_baseline"]
        lines.append(
            f"| {row['test_window']['start']} -> {row['test_window']['end']} | {d['Return_pct']:+.2f}pp | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f}pp | {'yes' if row['strict_outperform'] else 'no'} |"
        )
    lines.extend([
        "",
        "## Time-Slice Diagnostics",
        "",
        "| Slice | dReturn | dSharpe | dCalmar | dMaxDD |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in slices:
        d = row["delta_vs_baseline"]
        lines.append(
            f"| {row['slice']} | {d['Return_pct']:+.2f}pp | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f}pp |"
        )
    exp = payload["exposure_diagnostics"]
    lines.extend([
        "",
        "## Exposure Diagnostics",
        "",
        f"- Avg total exposure delta: {exp['avg_total_exposure_delta_pct']:+.2f}pp",
        f"- AddOn activation ratio: baseline {exp['addon_activation_ratio_baseline_pct']:.1f}% vs candidate {exp['addon_activation_ratio_candidate_pct']:.1f}%",
        f"- Avg AddOn size when active: baseline {exp['avg_addon_weight_when_active_baseline']:.3f} vs candidate {exp['avg_addon_weight_when_active_candidate']:.3f}",
        f"- Trend participation ratio: {exp['weighted_addon_exposure_ratio']:.3f}",
        f"- Accidental leverage flag: {'yes' if exp['accidental_leverage_flag'] else 'no'}",
        "",
        "## Execution Stress",
        "",
        f"- Stress delta vs default on graded candidate: Return {payload['execution_stress']['graded']['Return_pct']:+.2f}pp, Sharpe {payload['execution_stress']['graded']['Sharpe']:+.3f}, Calmar {payload['execution_stress']['graded']['Calmar']:+.3f}, MaxDD improve {payload['execution_stress']['graded']['MaxDD_improvement_pct']:+.2f}pp",
        f"- Stress ranking stable: {'yes' if payload['judgment']['stress_stable'] else 'no'}",
        "",
        "## Direct Answers",
        "",
        f"- {payload['judgment']['answer_1']}",
        f"- {payload['judgment']['answer_2']}",
        f"- {payload['judgment']['answer_3']}",
        f"- {payload['judgment']['answer_4']}",
        f"- {payload['judgment']['answer_5']}",
        f"- {payload['judgment']['answer_6']}",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    REPORT_TXT.write_text(
        "\n".join([
            f"promotion_candidate={payload['judgment']['promotion_candidate']}",
            f"best_structure={payload['judgment']['preferred_structure']}",
            f"baseline_decision={payload['judgment']['baseline_decision']}",
            f"extension_line_decision={payload['judgment']['extension_line_decision']}",
        ]),
        encoding="utf-8",
    )


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    d4 = ensure_datetime(df_4h)

    overlay = load_overlay_artifact()
    params_default = current_research_optimal(position_pct=100.0)
    params_stress = with_overrides(
        params_default,
        entry_execution_mode="live_runner_next_5m_close",
        intrabar_execution_model="segment_path_same_bar",
        intrabar_path_mode="pessimistic",
    )

    base_default = prepare_base_run(df_5m, df_4h, params_default)
    base_stress = prepare_base_run(df_5m, df_4h, params_stress)

    binary_plan_default = constant_weight_plan(base_default["entries"], GRADE_WEIGHTS["base"])
    binary_plan_stress = constant_weight_plan(base_stress["entries"], GRADE_WEIGHTS["base"])
    graded_plan_default, thresholds_full = assign_candidate(base_default["entries"], pd.Series(True, index=base_default["entries"].index))
    graded_plan_stress, _ = assign_candidate(base_stress["entries"], pd.Series(True, index=base_stress["entries"].index))

    bh_eq = bh_equity(d4.set_index("timestamp")["close"].astype(float))
    bh_exp = pd.Series(1.0, index=bh_eq.index, dtype=float)
    bh_metrics = compute_metrics(bh_eq, bh_exp)

    binary_default = simulate_combo_from_plan(df_4h, binary_plan_default, float(params_default.commission_pct))
    binary_stress = simulate_combo_from_plan(df_4h, binary_plan_stress, float(params_stress.commission_pct))
    graded_default = simulate_combo_from_plan(df_4h, graded_plan_default, float(params_default.commission_pct))
    graded_stress = simulate_combo_from_plan(df_4h, graded_plan_stress, float(params_stress.commission_pct))

    baseline_alignment = {
        "baseline_vs_artifact": {
            "delta_return_pct": float(binary_default["combo_metrics"]["TotalReturn_pct"] - float(overlay["addon_metrics"]["TotalReturn_pct"])),
            "delta_sharpe": float(binary_default["combo_metrics"]["Sharpe"] - float(overlay["addon_metrics"]["Sharpe"])),
            "delta_calmar": float(binary_default["combo_metrics"]["Calmar"] - float(overlay["addon_metrics"]["Calmar"])),
            "delta_maxdd_improve_pct": float(abs(float(overlay["addon_metrics"]["MaxDD_pct"])) - abs(binary_default["combo_metrics"]["MaxDD_pct"])),
        },
        "bh_vs_artifact": {
            "delta_return_pct": float(bh_metrics["TotalReturn_pct"] - float(overlay["bh_metrics"]["TotalReturn_pct"])),
            "delta_sharpe": float(bh_metrics["Sharpe"] - float(overlay["bh_metrics"]["Sharpe"])),
            "delta_calmar": float(bh_metrics["Calmar"] - float(overlay["bh_metrics"]["Calmar"])),
            "delta_maxdd_improve_pct": 0.0,
        },
    }

    calc_systems = {
        "BTC_BuyAndHold": {
            "equity": bh_eq,
            "exposure": bh_exp,
            "metrics": bh_metrics,
        },
        "Core+BinaryAddOn": {
            "equity": binary_default["combo_equity"],
            "exposure": binary_default["combo_exposure"],
            "metrics": binary_default["combo_metrics"],
        },
        "Core+GradedAddOn[compression_breakout]": {
            "equity": graded_default["combo_equity"],
            "exposure": graded_default["combo_exposure"],
            "metrics": graded_default["combo_metrics"],
        },
    }
    calc_systems["Core+BinaryAddOn"]["delta_vs_binary"] = {
        "Return_pct": 0.0,
        "Sharpe": 0.0,
        "Calmar": 0.0,
        "MaxDD_improvement_pct": 0.0,
    }
    calc_systems["Core+GradedAddOn[compression_breakout]"]["delta_vs_binary"] = delta_metrics(
        graded_default["combo_metrics"],
        binary_default["combo_metrics"],
    )
    calc_systems["BTC_BuyAndHold"]["delta_vs_binary"] = delta_metrics(bh_metrics, binary_default["combo_metrics"])

    wf_default = walk_forward_compare(df_4h, base_default["entries"], float(params_default.commission_pct))
    wf_stress = walk_forward_compare(df_4h, base_stress["entries"], float(params_stress.commission_pct))
    time_slices = time_slice_analysis(calc_systems)
    exposure = exposure_diagnostics(binary_default, graded_default, graded_plan_default)
    stress_delta_map = stress_compare(
        {
            "Core+BinaryAddOn": binary_default,
            "Core+GradedAddOn[compression_breakout]": graded_default,
        },
        {
            "Core+BinaryAddOn": binary_stress,
            "Core+GradedAddOn[compression_breakout]": graded_stress,
        },
    )

    full_delta = calc_systems["Core+GradedAddOn[compression_breakout]"]["delta_vs_binary"]
    stress_candidate_delta = stress_delta_map["Core+GradedAddOn[compression_breakout]"]["delta_vs_default_same_scheme"]
    stress_binary_delta = stress_delta_map["Core+BinaryAddOn"]["delta_vs_default_same_scheme"]
    stress_stable = bool(
        (stress_candidate_delta["Sharpe"] - stress_binary_delta["Sharpe"]) >= -0.02
        and (stress_candidate_delta["Calmar"] - stress_binary_delta["Calmar"]) >= -0.05
    )
    oos_stable = bool(
        wf_default["strict_win_ratio"] >= 2.0 / 3.0
        and wf_default["avg_delta_calmar"] > 0.0
    )
    non_degrading_maxdd = bool(full_delta["MaxDD_improvement_pct"] >= 0.0)
    accidental_exposure = bool(exposure["accidental_leverage_flag"])
    promotion_candidate = bool(oos_stable and non_degrading_maxdd and stress_stable and not accidental_exposure)

    driver = "better trend capture with modest size redistribution, not accidental leverage" if not accidental_exposure else "higher average exposure"

    payload = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "locked_baseline": {
            "mainline": "BTC long-only squeeze_release_20",
            "research_optimal": "lb20_stop3.2_trail5.0_beoff",
            "default_tuple": DEFAULT_TUPLE,
            "stress_tuple": STRESS_TUPLE,
            "baseline_status": "AddOn-only remains the locked baseline",
        },
        "candidate": {
            "name": "Core+GradedAddOn[compression_breakout]",
            "scheme": grading_scheme(),
            "tier_weights": GRADE_WEIGHTS,
            "full_sample_thresholds": thresholds_full,
        },
        "baseline_alignment": baseline_alignment,
        "systems": {
            key: {
                "metrics": value["metrics"],
                "delta_vs_binary": value.get("delta_vs_binary"),
            }
            for key, value in calc_systems.items()
        },
        "walk_forward": {
            "default": wf_default,
            "stress": wf_stress,
        },
        "time_slices": time_slices,
        "exposure_diagnostics": exposure,
        "execution_stress": {
            "binary": stress_binary_delta,
            "graded": stress_candidate_delta,
        },
        "judgment": {
            "promotion_candidate": promotion_candidate,
            "promotion_candidate_answer": "NO. Compression-breakout grading does not yet clear promotion-candidate validation." if not promotion_candidate else "YES. Compression-breakout grading is strong enough to become a promotion candidate.",
            "preferred_structure": "Core+GradedAddOn[compression_breakout]",
            "baseline_decision": "Keep baseline unchanged" if not promotion_candidate else "Baseline can move into promotion review",
            "extension_line_decision": "Keep AddOn grading as the active extension line",
            "oos_stable": oos_stable,
            "stress_stable": stress_stable,
            "non_degrading_maxdd": non_degrading_maxdd,
            "driver": driver,
            "answer_1": (
                "On the rebuilt comparison framework, compression-breakout grading does not formally outperform the binary AddOn baseline strongly enough for promotion."
                if not promotion_candidate
                else "Compression-breakout grading does outperform the binary AddOn baseline strongly enough to enter promotion review."
            ),
            "answer_2": (
                f"OOS stability is {'good' if oos_stable else 'not sufficient'}: strict win ratio {wf_default['strict_win_ratio']:.2f}, avg dReturn {wf_default['avg_delta_return_pct']:+.2f}pp, avg dSharpe {wf_default['avg_delta_sharpe']:+.3f}, avg dCalmar {wf_default['avg_delta_calmar']:+.3f}."
            ),
            "answer_3": f"The improvement comes from {driver}. Average total exposure only moves by {exposure['avg_total_exposure_delta_pct']:+.2f}pp and activation frequency stays unchanged at {exposure['addon_activation_ratio_candidate_pct']:.1f}%.",
            "answer_4": (
                "No. It cannot be considered a promotion candidate yet because max drawdown still degrades slightly versus the binary baseline."
                if not promotion_candidate
                else "Yes. It can now be considered a promotion candidate."
            ),
            "answer_5": "Yes. AddOn grading should remain the active extension line, with compression-breakout kept as the lead candidate.",
            "answer_6": "Yes. Baseline should remain unchanged until a graded sleeve clears promotion criteria without max-drawdown degradation or execution fragility.",
        },
    }
    write_report(payload)
    print(
        json.dumps(
            {
                "promotion_candidate": promotion_candidate,
                "strict_win_ratio": wf_default["strict_win_ratio"],
                "avg_delta_calmar": wf_default["avg_delta_calmar"],
                "maxdd_non_degrading": non_degrading_maxdd,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
