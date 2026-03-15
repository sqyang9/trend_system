#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Narrow MaxDD repair study for GradedAddOn[compression_breakout]."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_addon_grading_promotion_validation import (
    DEFAULT_TUPLE,
    STRESS_TUPLE,
    TIME_SLICES,
    WF_TEST_YEARS,
)
from v90_addon_grading_study import (
    GRADE_WEIGHTS,
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


REPORT_MD = Path("BTC_ADDON_GRADING_MAXDD_REPAIR_REPORT.md")
REPORT_JSON = Path("btc_addon_grading_maxdd_repair_report.json")
REPORT_TXT = Path("btc_addon_grading_maxdd_repair_summary.txt")
PROMOTION_REPORT = Path("btc_addon_grading_promotion_report.json")

BASE_SCHEME = {
    "name": "compression_breakout",
    "title": "Compression + Breakout Release",
    "description": "Grade entries by squeeze quality, squeeze persistence, and breakout distance.",
    "features": {
        "compression_quality": 0.35,
        "squeeze_count": 0.25,
        "breakout_distance_atr": 0.40,
    },
}

REPAIR_CANDIDATES = [
    {
        "name": "repair_strong045",
        "description": "Reduce strong tier from 0.50 to 0.45.",
        "strong_weight": 0.45,
        "strong_quantile": 2.0 / 3.0,
        "breakout_multiplier": None,
    },
    {
        "name": "repair_strong048",
        "description": "Reduce strong tier from 0.50 to 0.48.",
        "strong_weight": 0.48,
        "strong_quantile": 2.0 / 3.0,
        "breakout_multiplier": None,
    },
    {
        "name": "repair_top30",
        "description": "Tighten strong grade to top 30% only.",
        "strong_weight": 0.50,
        "strong_quantile": 0.70,
        "breakout_multiplier": None,
    },
    {
        "name": "repair_top30_strong045",
        "description": "Top 30% strong grade with strong weight cut to 0.45.",
        "strong_weight": 0.45,
        "strong_quantile": 0.70,
        "breakout_multiplier": None,
    },
    {
        "name": "repair_breakout110",
        "description": "Strong grade also requires breakout distance >= 110% of train strong median.",
        "strong_weight": 0.50,
        "strong_quantile": 2.0 / 3.0,
        "breakout_multiplier": 1.10,
    },
    {
        "name": "repair_breakout110_strong048",
        "description": "Strong grade uses 0.48 weight and 110% breakout requirement.",
        "strong_weight": 0.48,
        "strong_quantile": 2.0 / 3.0,
        "breakout_multiplier": 1.10,
    },
]


def assign_original(entries: pd.DataFrame, train_mask: pd.Series) -> tuple[pd.DataFrame, Dict]:
    return assign_variant(entries, train_mask, {
        "name": "original",
        "description": "Original compression_breakout grading.",
        "strong_weight": 0.50,
        "strong_quantile": 2.0 / 3.0,
        "breakout_multiplier": None,
    })


def assign_variant(entries: pd.DataFrame, train_mask: pd.Series, config: Dict) -> tuple[pd.DataFrame, Dict]:
    assigned = entries.copy()
    score = pd.Series(0.0, index=assigned.index, dtype=float)
    for feature, weight in BASE_SCHEME["features"].items():
        ranks = rank_against_train(assigned.loc[train_mask, feature], assigned[feature])
        score = score + weight * ranks
    score_train = score.loc[train_mask]
    weak_cut = float(score_train.quantile(1.0 / 3.0)) if not score_train.empty else 0.33
    strong_cut = float(score_train.quantile(config["strong_quantile"])) if not score_train.empty else 0.67

    assigned["grade_score"] = score
    assigned["grade_label"] = "base"
    assigned.loc[score <= weak_cut, "grade_label"] = "weak"
    assigned.loc[score >= strong_cut, "grade_label"] = "strong"

    breakout_cut = None
    if config["breakout_multiplier"] is not None:
        train_strong = assigned.loc[train_mask & (assigned["grade_label"] == "strong"), "breakout_distance_atr"]
        base_cut = float(train_strong.median()) if not train_strong.empty else float(assigned.loc[train_mask, "breakout_distance_atr"].median())
        breakout_cut = base_cut * float(config["breakout_multiplier"])
        assigned.loc[(assigned["grade_label"] == "strong") & (assigned["breakout_distance_atr"] < breakout_cut), "grade_label"] = "base"

    weight_map = {"weak": GRADE_WEIGHTS["weak"], "base": GRADE_WEIGHTS["base"], "strong": float(config["strong_weight"])}
    assigned["addon_weight"] = assigned["grade_label"].map(weight_map).astype(float)
    thresholds = {
        "weak_cut": weak_cut,
        "strong_cut": strong_cut,
        "strong_quantile": float(config["strong_quantile"]),
        "strong_weight": float(config["strong_weight"]),
        "breakout_cut": breakout_cut,
        "breakout_multiplier": config["breakout_multiplier"],
        "train_trade_count": int(train_mask.sum()),
    }
    return assigned, thresholds


def walk_forward_variant(df_4h: pd.DataFrame, entries: pd.DataFrame, commission_pct: float, config: Dict) -> Dict:
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
        baseline_plan = constant_weight_plan(sim_entries, GRADE_WEIGHTS["base"])
        candidate_plan, thresholds = assign_variant(sim_entries, sim_train_mask, config)
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
            and delta["MaxDD_improvement_pct"] >= 0.0
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
                "delta_vs_baseline": delta,
                "candidate_metrics": candidate_metrics,
                "baseline_metrics": baseline_metrics,
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


def time_slice_variant(systems: Dict[str, Dict], candidate_key: str) -> List[Dict]:
    rows = []
    baseline_key = "Core+BinaryAddOn"
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
                "delta_vs_baseline": delta_metrics(candidate_metrics, baseline_metrics),
                "candidate_metrics": candidate_metrics,
                "baseline_metrics": baseline_metrics,
            }
        )
    return rows


def exposure_diag(binary: Dict, candidate: Dict, plan: pd.DataFrame) -> Dict:
    counts = plan["grade_label"].value_counts().to_dict()
    active = candidate["sleeve"]["weight"] > 0.0
    return {
        "avg_total_exposure_binary_pct": float(binary["combo_exposure"].mean() * 100.0),
        "avg_total_exposure_candidate_pct": float(candidate["combo_exposure"].mean() * 100.0),
        "avg_total_exposure_delta_vs_binary_pct": float((candidate["combo_exposure"].mean() - binary["combo_exposure"].mean()) * 100.0),
        "addon_activation_ratio_binary_pct": binary["sleeve"]["active_ratio_pct"],
        "addon_activation_ratio_candidate_pct": candidate["sleeve"]["active_ratio_pct"],
        "avg_addon_weight_when_active_binary": binary["sleeve"]["avg_weight_when_active"],
        "avg_addon_weight_when_active_candidate": candidate["sleeve"]["avg_weight_when_active"],
        "grade_counts": {k: int(counts.get(k, 0)) for k in ["weak", "base", "strong"]},
        "active_bar_size_distribution_pct": {
            "weak_pct": float((candidate["sleeve"]["weight"][active] == GRADE_WEIGHTS["weak"]).mean() * 100.0) if active.any() else 0.0,
            "base_pct": float((candidate["sleeve"]["weight"][active] == GRADE_WEIGHTS["base"]).mean() * 100.0) if active.any() else 0.0,
            "strong_pct": float((candidate["sleeve"]["weight"][active] > GRADE_WEIGHTS["base"]).mean() * 100.0) if active.any() else 0.0,
        },
        "accidental_leverage_flag": bool((candidate["combo_exposure"].mean() - binary["combo_exposure"].mean()) > 0.02),
    }


def write_report(payload: Dict) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    best_key = payload["best_candidate"]
    best = payload["candidates"][best_key]
    lines = [
        "# BTC AddOn Grading MaxDD Repair Report",
        "",
        "## Final Judgment",
        "",
        f"- Repair answer: {payload['judgment']['repair_answer']}",
        f"- Best repair candidate: {best_key}",
        f"- Baseline decision: {payload['judgment']['baseline_decision']}",
        f"- Extension-line decision: {payload['judgment']['extension_line_decision']}",
        "",
        "## Baseline Alignment",
        "",
        f"- Binary AddOn drift vs committed artifact: Return {payload['baseline_alignment']['binary_vs_artifact']['delta_return_pct']:+.2f}pp, Sharpe {payload['baseline_alignment']['binary_vs_artifact']['delta_sharpe']:+.3f}, Calmar {payload['baseline_alignment']['binary_vs_artifact']['delta_calmar']:+.3f}, MaxDD improve {payload['baseline_alignment']['binary_vs_artifact']['delta_maxdd_improve_pct']:+.2f}pp",
        f"- Original graded drift vs committed promotion result: Return {payload['baseline_alignment']['graded_vs_artifact']['delta_return_pct']:+.2f}pp, Sharpe {payload['baseline_alignment']['graded_vs_artifact']['delta_sharpe']:+.3f}, Calmar {payload['baseline_alignment']['graded_vs_artifact']['delta_calmar']:+.3f}, MaxDD improve {payload['baseline_alignment']['graded_vs_artifact']['delta_maxdd_improve_pct']:+.2f}pp",
        "",
        "## Candidate Table",
        "",
        "| Candidate | dRet vs Binary | dSharpe | dCalmar | dMaxDD | WF strict | WF dRet | WF dSharpe | WF dCalmar | WF dMaxDD |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, row in payload["candidates"].items():
        d = row["delta_vs_binary"]
        wf = row["walk_forward"]["default"]
        lines.append(
            f"| {key} | {d['Return_pct']:+.2f} | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f} | {wf['strict_win_ratio']:.2f} | {wf['avg_delta_return_pct']:+.2f} | {wf['avg_delta_sharpe']:+.3f} | {wf['avg_delta_calmar']:+.3f} | {wf['avg_delta_maxdd_improvement_pct']:+.2f} |"
        )
    lines.extend([
        "",
        "## Best Candidate Time-Slice Diagnostics",
        "",
        "| Slice | dReturn | dSharpe | dCalmar | dMaxDD |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in best["time_slices"]:
        d = row["delta_vs_baseline"]
        lines.append(
            f"| {row['slice']} | {d['Return_pct']:+.2f}pp | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f}pp |"
        )
    exp = best["exposure_diagnostics"]
    lines.extend([
        "",
        "## Best Candidate Exposure Diagnostics",
        "",
        f"- Avg total exposure delta vs binary: {exp['avg_total_exposure_delta_vs_binary_pct']:+.2f}pp",
        f"- AddOn activation ratio: binary {exp['addon_activation_ratio_binary_pct']:.1f}% vs candidate {exp['addon_activation_ratio_candidate_pct']:.1f}%",
        f"- Avg AddOn size when active: binary {exp['avg_addon_weight_when_active_binary']:.3f} vs candidate {exp['avg_addon_weight_when_active_candidate']:.3f}",
        f"- Accidental leverage flag: {'yes' if exp['accidental_leverage_flag'] else 'no'}",
        "",
        "## Execution Stress",
        "",
        f"- Stress delta on best repair candidate: Return {best['execution_stress']['Return_pct']:+.2f}pp, Sharpe {best['execution_stress']['Sharpe']:+.3f}, Calmar {best['execution_stress']['Calmar']:+.3f}, MaxDD improve {best['execution_stress']['MaxDD_improvement_pct']:+.2f}pp",
        "",
        "## Direct Answers",
        "",
        f"- {payload['judgment']['answer_1']}",
        f"- {payload['judgment']['answer_2']}",
        f"- {payload['judgment']['answer_3']}",
        f"- {payload['judgment']['answer_4']}",
        f"- {payload['judgment']['answer_5']}",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    REPORT_TXT.write_text(
        "\n".join([
            f"promotion_candidate={payload['judgment']['promotion_candidate']}",
            f"best_candidate={best_key}",
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
    overlay = load_overlay_artifact()
    promotion = json.loads(PROMOTION_REPORT.read_text(encoding="utf-8"))

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
    graded_plan_default, _ = assign_original(base_default["entries"], pd.Series(True, index=base_default["entries"].index))
    graded_plan_stress, _ = assign_original(base_stress["entries"], pd.Series(True, index=base_stress["entries"].index))

    binary_default = simulate_combo_from_plan(df_4h, binary_plan_default, float(params_default.commission_pct))
    binary_stress = simulate_combo_from_plan(df_4h, binary_plan_stress, float(params_stress.commission_pct))
    graded_default = simulate_combo_from_plan(df_4h, graded_plan_default, float(params_default.commission_pct))
    graded_stress = simulate_combo_from_plan(df_4h, graded_plan_stress, float(params_stress.commission_pct))

    systems = {
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

    baseline_alignment = {
        "binary_vs_artifact": {
            "delta_return_pct": float(binary_default["combo_metrics"]["TotalReturn_pct"] - float(overlay["addon_metrics"]["TotalReturn_pct"])),
            "delta_sharpe": float(binary_default["combo_metrics"]["Sharpe"] - float(overlay["addon_metrics"]["Sharpe"])),
            "delta_calmar": float(binary_default["combo_metrics"]["Calmar"] - float(overlay["addon_metrics"]["Calmar"])),
            "delta_maxdd_improve_pct": float(abs(float(overlay["addon_metrics"]["MaxDD_pct"])) - abs(binary_default["combo_metrics"]["MaxDD_pct"])),
        },
        "graded_vs_artifact": {
            "delta_return_pct": float(graded_default["combo_metrics"]["TotalReturn_pct"] - float(promotion["systems"]["Core+GradedAddOn[compression_breakout]"]["metrics"]["TotalReturn_pct"])),
            "delta_sharpe": float(graded_default["combo_metrics"]["Sharpe"] - float(promotion["systems"]["Core+GradedAddOn[compression_breakout]"]["metrics"]["Sharpe"])),
            "delta_calmar": float(graded_default["combo_metrics"]["Calmar"] - float(promotion["systems"]["Core+GradedAddOn[compression_breakout]"]["metrics"]["Calmar"])),
            "delta_maxdd_improve_pct": float(abs(float(promotion["systems"]["Core+GradedAddOn[compression_breakout]"]["metrics"]["MaxDD_pct"])) - abs(graded_default["combo_metrics"]["MaxDD_pct"])),
        },
    }

    candidate_rows = {}
    for config in REPAIR_CANDIDATES:
        plan_default, thresholds_full = assign_variant(base_default["entries"], pd.Series(True, index=base_default["entries"].index), config)
        plan_stress, _ = assign_variant(base_stress["entries"], pd.Series(True, index=base_stress["entries"].index), config)
        default_sim = simulate_combo_from_plan(df_4h, plan_default, float(params_default.commission_pct))
        stress_sim = simulate_combo_from_plan(df_4h, plan_stress, float(params_stress.commission_pct))
        key = f"Core+AdjustedGradedAddOn[{config['name']}]"
        systems[key] = {
            "equity": default_sim["combo_equity"],
            "exposure": default_sim["combo_exposure"],
            "metrics": default_sim["combo_metrics"],
        }
        candidate_rows[key] = {
            "config": config,
            "thresholds_full_sample": thresholds_full,
            "metrics": default_sim["combo_metrics"],
            "delta_vs_binary": delta_metrics(default_sim["combo_metrics"], binary_default["combo_metrics"]),
            "delta_vs_original_graded": delta_metrics(default_sim["combo_metrics"], graded_default["combo_metrics"]),
            "walk_forward": {
                "default": walk_forward_variant(df_4h, base_default["entries"], float(params_default.commission_pct), config),
                "stress": walk_forward_variant(df_4h, base_stress["entries"], float(params_stress.commission_pct), config),
            },
            "time_slices": time_slice_variant(systems, key),
            "exposure_diagnostics": exposure_diag(binary_default, default_sim, plan_default),
            "execution_stress": stress_compare({key: default_sim}, {key: stress_sim})[key]["delta_vs_default_same_scheme"],
        }

    best_key = sorted(
        candidate_rows,
        key=lambda k: (
            candidate_rows[k]["delta_vs_binary"]["MaxDD_improvement_pct"] >= 0.0,
            candidate_rows[k]["walk_forward"]["default"]["strict_win_ratio"],
            candidate_rows[k]["walk_forward"]["default"]["avg_delta_calmar"],
            candidate_rows[k]["delta_vs_binary"]["Calmar"],
            candidate_rows[k]["delta_vs_binary"]["Return_pct"],
        ),
        reverse=True,
    )[0]
    best = candidate_rows[best_key]
    promotion_candidate = bool(
        best["walk_forward"]["default"]["strict_win_ratio"] >= 2.0 / 3.0
        and best["walk_forward"]["default"]["avg_delta_calmar"] > 0.0
        and best["delta_vs_binary"]["MaxDD_improvement_pct"] >= 0.0
        and best["delta_vs_binary"]["Calmar"] >= 0.0
        and best["execution_stress"]["Calmar"] >= -0.05
        and not best["exposure_diagnostics"]["accidental_leverage_flag"]
    )

    payload = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "locked_baseline": {
            "mainline": "BTC long-only squeeze_release_20",
            "research_optimal": "lb20_stop3.2_trail5.0_beoff",
            "default_tuple": DEFAULT_TUPLE,
            "stress_tuple": STRESS_TUPLE,
            "baseline_status": "Core BTC holding + Binary AddOn remains the locked baseline",
        },
        "study_scope": {
            "type": "very_narrow_maxdd_repair",
            "base_scheme": BASE_SCHEME,
            "tested_candidates": REPAIR_CANDIDATES,
            "note": "Only strong-tier weight, strong threshold, and strong-tier breakout tightening are tested.",
        },
        "baseline_alignment": baseline_alignment,
        "reference_systems": {
            "Core+BinaryAddOn": binary_default["combo_metrics"],
            "Core+GradedAddOn[compression_breakout]": graded_default["combo_metrics"],
        },
        "candidates": candidate_rows,
        "best_candidate": best_key,
        "judgment": {
            "promotion_candidate": promotion_candidate,
            "repair_answer": "YES. A repaired candidate clears promotion-candidate validation." if promotion_candidate else "NO. No repaired grading candidate clears promotion-candidate validation.",
            "baseline_decision": "Move to promotion review" if promotion_candidate else "Keep baseline unchanged",
            "extension_line_decision": "Keep AddOn grading as active extension line",
            "answer_1": (
                f"{best_key} {'does' if promotion_candidate else 'does not'} outperform the binary AddOn baseline strongly enough after the narrow MaxDD repair pass."
            ),
            "answer_2": f"OOS stability remains {'strong' if best['walk_forward']['default']['strict_win_ratio'] >= 2.0 / 3.0 else 'too weak'}: strict win ratio {best['walk_forward']['default']['strict_win_ratio']:.2f}, avg dReturn {best['walk_forward']['default']['avg_delta_return_pct']:+.2f}pp, avg dSharpe {best['walk_forward']['default']['avg_delta_sharpe']:+.3f}, avg dCalmar {best['walk_forward']['default']['avg_delta_calmar']:+.3f}.",
            "answer_3": (
                "Yes. MaxDD degradation is removed."
                if best["delta_vs_binary"]["MaxDD_improvement_pct"] >= 0.0
                else f"No. MaxDD degradation remains; best full-sample dMaxDD is {best['delta_vs_binary']['MaxDD_improvement_pct']:+.2f}pp."
            ),
            "answer_4": (
                "Yes. The repaired candidate can become a promotion candidate."
                if promotion_candidate
                else "No. The repaired candidate still cannot become a promotion candidate."
            ),
            "answer_5": (
                "Yes. Baseline can move to promotion review."
                if promotion_candidate
                else "No. Baseline should stay unchanged while AddOn grading remains the active extension line."
            ),
        },
    }
    write_report(payload)
    print(
        json.dumps(
            {
                "best_candidate": best_key,
                "promotion_candidate": promotion_candidate,
                "strict_win_ratio": best["walk_forward"]["default"]["strict_win_ratio"],
                "avg_delta_calmar": best["walk_forward"]["default"]["avg_delta_calmar"],
                "full_sample_dmaxdd": best["delta_vs_binary"]["MaxDD_improvement_pct"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
