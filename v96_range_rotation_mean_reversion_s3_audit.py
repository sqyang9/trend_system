#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 robustness and promotion audit for range_rotation_mean_reversion."""

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
from v90_addon_exposure_repair_audit import enrich_entries
from v90_addon_grading_promotion_validation import DEFAULT_TUPLE, STRESS_TUPLE, TIME_SLICES
from v90_addon_grading_study import (
    GRADE_WEIGHTS,
    SEED,
    compute_slice_metrics,
    constant_weight_plan,
    current_research_optimal,
    delta_metrics,
    prepare_base_run,
    simulate_combo_from_plan,
    slice_range,
    with_overrides,
    yearly_returns,
)
from v91_exposure_engine_e1_constant_mapping import archived_repair_plan, extended_metrics
from v92_const1x_deployment_audit import (
    MONTHS_FOR_CLUSTER,
    ROLLING_180D_BARS,
    ROLLING_365D_BARS,
    extract_underwater_episodes,
    rolling_return,
    rolling_window_maxdd,
)
from v95_range_rotation_mean_reversion_audit import (
    combine_with_const1x,
    make_range_rotation_params,
    normalize_candidate_sleeve,
    overlap_diagnostics,
    run_range_rotation_candidate,
)


AUDIT_MD = Path("RANGE_ROTATION_MEAN_REVERSION_S3_ROBUSTNESS_AUDIT.md")
DECISION_MD = Path("RANGE_ROTATION_MEAN_REVERSION_PROMOTION_DECISION.md")
REPORT_JSON = Path("range_rotation_mean_reversion_s3_audit.json")

BINARY_WEIGHT = GRADE_WEIGHTS["base"]
CONST_WEIGHT = 1.00
SYSTEM_ORDER = [
    "CoreOnly",
    "Core+BinaryAddOn",
    "Core+ConstAddOn[1.00x]",
    "Core+ConstAddOn[1.00x]+RangeRotation",
]
SCENARIOS = [
    {
        "name": "default",
        "label": "Default tuple",
        "tuple": DEFAULT_TUPLE,
        "overrides": {},
    },
    {
        "name": "stress",
        "label": "Current stress tuple",
        "tuple": STRESS_TUPLE,
        "overrides": {
            "entry_execution_mode": "live_runner_next_5m_close",
            "intrabar_execution_model": "segment_path_same_bar",
            "intrabar_path_mode": "pessimistic",
        },
    },
    {
        "name": "harsh_friction",
        "label": "Harsh friction degradation",
        "tuple": "live_runner_next_5m_close + segment_path_same_bar + pessimistic + higher friction",
        "overrides": {
            "entry_execution_mode": "live_runner_next_5m_close",
            "intrabar_execution_model": "segment_path_same_bar",
            "intrabar_path_mode": "pessimistic",
            "commission_pct": 0.12,
            "close_delay_bps": 12.0,
            "slippage_fixed_bps": 8.0,
            "slippage_breakout_extra_bps": 8.0,
            "slippage_stop_extra_bps": 12.0,
            "slippage_range_weight": 0.08,
            "slippage_max_bps": 35.0,
        },
    },
]


def rolling_summary(equity: pd.Series, bars: int) -> Dict:
    ret = rolling_return(equity, bars).dropna()
    dd = rolling_window_maxdd(equity, bars).dropna()

    def qstats(series: pd.Series) -> Dict:
        if series.empty:
            return {"p10": 0.0, "p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0}
        q = series.quantile([0.10, 0.25, 0.50, 0.75, 0.90])
        return {f"p{int(idx * 100)}": float(val) for idx, val in q.items()}

    return {
        "return_quantiles_pct": qstats(ret),
        "maxdd_quantiles_pct": qstats(dd),
        "worst_return_pct": float(ret.min()) if not ret.empty else 0.0,
        "best_return_pct": float(ret.max()) if not ret.empty else 0.0,
        "worst_maxdd_pct": float(dd.min()) if not dd.empty else 0.0,
    }


def path_diagnostics(equity: pd.Series) -> Dict:
    episodes = extract_underwater_episodes(equity)
    depth_rank = sorted(episodes, key=lambda x: x["depth_pct"])[:3]
    duration_rank = sorted(episodes, key=lambda x: x["duration_days"], reverse=True)[:3]
    return {
        "rolling_365d": rolling_summary(equity, ROLLING_365D_BARS),
        "rolling_180d": rolling_summary(equity, ROLLING_180D_BARS),
        "worst_underwater_episodes": depth_rank,
        "longest_recovery_episodes": duration_rank,
    }


def month_return_stats(equity: pd.Series) -> pd.Series:
    monthly = equity.resample("ME").last().pct_change().dropna() * 100.0
    monthly.index = monthly.index.tz_localize(None).to_period("M").to_timestamp()
    return monthly.astype(float)


def loss_cluster_diagnostics(equity: pd.Series) -> Dict:
    monthly = month_return_stats(equity)
    longest_neg = cur = 0
    for value in monthly.tolist():
        if value < 0.0:
            cur += 1
            longest_neg = max(longest_neg, cur)
        else:
            cur = 0
    out = {
        "longest_negative_month_streak": int(longest_neg),
        "worst_month_pct": float(monthly.min()) if not monthly.empty else 0.0,
    }
    for months in MONTHS_FOR_CLUSTER:
        roll = monthly.rolling(months).sum().dropna()
        out[f"worst_{months}m_cluster_return_pct"] = float(roll.min()) if not roll.empty else 0.0
    return out


def yearly_table_for_systems(systems: Dict[str, Dict]) -> List[Dict]:
    merged: Dict[int, Dict] = {}
    for key, sim in systems.items():
        for row in yearly_returns(sim["combo_equity"]):
            merged.setdefault(int(row["year"]), {"year": int(row["year"])})
            merged[int(row["year"])][key] = float(row["Return_pct"])
    rows = [merged[year] for year in sorted(merged)]
    for row in rows:
        if "Core+ConstAddOn[1.00x]+RangeRotation" in row and "Core+ConstAddOn[1.00x]" in row:
            row["RangeRotation_minus_Const1x_pct"] = float(
                row["Core+ConstAddOn[1.00x]+RangeRotation"] - row["Core+ConstAddOn[1.00x]"]
            )
    return rows


def time_slice_metrics_for_systems(systems: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for sl in TIME_SLICES:
        row = {"slice": sl["name"], "window": {"start": sl["start"], "end": sl["end"]}}
        for key, sim in systems.items():
            row[key] = compute_slice_metrics(
                slice_range(sim["combo_equity"], sl["start"], sl["end"]),
                slice_range(sim["combo_exposure"], sl["start"], sl["end"]),
            )
        row["RangeRotation_delta_vs_Const1x"] = delta_metrics(
            row["Core+ConstAddOn[1.00x]+RangeRotation"],
            row["Core+ConstAddOn[1.00x]"],
        )
        rows.append(row)
    return rows


def system_operational(sim: Dict) -> Dict:
    metrics = extended_metrics(sim)
    combo_exposure = sim["combo_exposure"].astype(float)
    return {
        "avg_exposure_pct": float(combo_exposure.mean() * 100.0),
        "peak_total_exposure_pct": float(combo_exposure.max() * 100.0),
        "recovery_burden_days": float(metrics["recovery_days_from_maxdd"]),
    }


def range_rotation_operational(
    combo: Dict,
    const1x: Dict,
    candidate_sleeve: Dict,
    overlap: Dict,
) -> Dict:
    base = system_operational(combo)
    return {
        **base,
        "sleeve1_active_ratio_pct": float((const1x["sleeve"]["weight"] > 0.0).mean() * 100.0),
        "sleeve2_active_ratio_pct": float(candidate_sleeve["active_ratio_pct"]),
        "sleeve2_avg_weight_when_active": float(candidate_sleeve["avg_weight_when_active"]),
        "active_overlap_ratio_pct": float(overlap["active_overlap_ratio_pct"]),
        "candidate_entries_when_current_flat_pct": float(overlap["candidate_entries_when_current_flat_pct"]),
        "active_return_correlation": float(overlap["active_return_correlation"]),
        "candidate_abs_pnl_when_current_flat_pct_of_total_abs": float(
            overlap["candidate_abs_pnl_when_current_flat_pct_of_total_abs"]
        ),
        "peak_sleeve1_weight": float(const1x["sleeve"]["weight"].max()),
        "peak_sleeve2_weight": float(candidate_sleeve["weight"].max()),
        "peak_incremental_exposure_pct": float(candidate_sleeve["weight"].max() * 100.0),
        "accidental_leverage_flag": False,
        "peak_exposure_governance_flag": bool(combo["combo_exposure"].max() > 2.0),
        "operational_complexity_flag": False,
    }


def scenario_systems(core_params, range_params, df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
    base = prepare_base_run(df_5m, df_4h, core_params)
    entries = base["entries"]
    enriched = enrich_entries(base, df_4h)
    commission = float(core_params.commission_pct)

    core_only = simulate_combo_from_plan(df_4h, constant_weight_plan(entries, 0.0), commission)
    binary = simulate_combo_from_plan(df_4h, constant_weight_plan(entries, BINARY_WEIGHT), commission)
    const1x = simulate_combo_from_plan(df_4h, constant_weight_plan(entries, CONST_WEIGHT), commission)
    candidate_result = run_range_rotation_candidate(df_5m, df_4h, range_params)
    candidate_sleeve = normalize_candidate_sleeve(candidate_result, df_4h, weight=1.0)
    plus_range = combine_with_const1x(df_4h, const1x, candidate_sleeve)
    overlap = overlap_diagnostics(
        {"equity": const1x["sleeve"]["equity"], "weight": const1x["sleeve"]["weight"]},
        candidate_sleeve,
        candidate_result.get("trade_meta"),
    )

    systems = {
        "CoreOnly": core_only,
        "Core+BinaryAddOn": binary,
        "Core+ConstAddOn[1.00x]": const1x,
        "Core+ConstAddOn[1.00x]+RangeRotation": plus_range,
    }
    archived = simulate_combo_from_plan(
        df_4h,
        archived_repair_plan(enriched, pd.Series(True, index=enriched.index)),
        commission,
    )
    systems["Core+CompoundRepair[close30_gate_to_base]"] = archived
    return {
        "systems": systems,
        "candidate_result": candidate_result,
        "candidate_sleeve": candidate_sleeve,
        "overlap": overlap,
    }


def scenario_summary(name: str, label: str, tuple_label: str, scenario_data: Dict) -> Dict:
    systems = scenario_data["systems"]
    plus_metrics = systems["Core+ConstAddOn[1.00x]+RangeRotation"]["combo_metrics"]
    const_metrics = systems["Core+ConstAddOn[1.00x]"]["combo_metrics"]
    survives = bool(
        plus_metrics["TotalReturn_pct"] > const_metrics["TotalReturn_pct"]
        and abs(plus_metrics["MaxDD_pct"]) < abs(const_metrics["MaxDD_pct"])
        and plus_metrics["Calmar"] > const_metrics["Calmar"]
    )
    return {
        "scenario": name,
        "label": label,
        "tuple": tuple_label,
        "systems": {
            key: extended_metrics(sim)
            for key, sim in systems.items()
            if key in SYSTEM_ORDER
        },
        "range_vs_const1x": delta_metrics(plus_metrics, const_metrics),
        "ranking_survives": survives,
    }


def write_reports(payload: Dict) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    default = payload["default_audit"]
    lines: List[str] = [
        "# Range Rotation Mean Reversion S3 Robustness Audit",
        "",
        "## Final Judgment",
        "",
        f"- Promotion decision: {payload['judgment']['decision']}",
        f"- Recommendation: {payload['judgment']['promotion_recommendation']}",
        f"- Remaining condition: {payload['judgment']['remaining_condition']}",
        "",
        "## Scenario Robustness",
        "",
        "| Scenario | PlusRange TotalReturn | PlusRange MaxDD | PlusRange Calmar | dRet vs Const1x | dMaxDD vs Const1x | dCalmar vs Const1x | Ranking survives |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["scenario_summaries"]:
        m = row["systems"]["Core+ConstAddOn[1.00x]+RangeRotation"]
        d = row["range_vs_const1x"]
        lines.append(
            f"| {row['label']} | {m['TotalReturn_pct']:.2f}% | {m['MaxDD_pct']:.2f}% | {m['Calmar']:.3f} | "
            f"{d['Return_pct']:+.2f}pp | {d['MaxDD_improvement_pct']:+.2f}pp | {d['Calmar']:+.3f} | "
            f"{'yes' if row['ranking_survives'] else 'no'} |"
        )
    lines.extend([
        "",
        "## Default Reference Set",
        "",
        "| System | TotalReturn | CAGR | MaxDD | Calmar | Ulcer | RecoveryDays | AvgExposure | PeakExposure |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for key in ["CoreOnly", "Core+BinaryAddOn", "Core+ConstAddOn[1.00x]", "Core+ConstAddOn[1.00x]+RangeRotation"]:
        m = default["systems"][key]["metrics"]
        o = default["systems"][key]["operational"]
        lines.append(
            f"| {key} | {m['TotalReturn_pct']:.2f}% | {m['CAGR_pct']:.2f}% | {m['MaxDD_pct']:.2f}% | {m['Calmar']:.3f} | "
            f"{m['UlcerIndex']:.2f} | {m['recovery_days_from_maxdd']:.1f} | {o['avg_exposure_pct']:.2f}% | {o['peak_total_exposure_pct']:.2f}% |"
        )
    lines.extend([
        "",
        "## Path Robustness",
        "",
        f"- Rolling 365d excess-return win ratio vs Const1x: {default['path_comparison']['rolling_365d_excess_win_ratio_pct']:.1f}%",
        f"- Rolling 180d drawdown-improvement win ratio vs Const1x: {default['path_comparison']['rolling_180d_dd_improvement_win_ratio_pct']:.1f}%",
        f"- Worst 3m / 6m cluster return, Const1x: {default['systems']['Core+ConstAddOn[1.00x]']['loss_clusters']['worst_3m_cluster_return_pct']:.2f}% / {default['systems']['Core+ConstAddOn[1.00x]']['loss_clusters']['worst_6m_cluster_return_pct']:.2f}%",
        f"- Worst 3m / 6m cluster return, PlusRange: {default['systems']['Core+ConstAddOn[1.00x]+RangeRotation']['loss_clusters']['worst_3m_cluster_return_pct']:.2f}% / {default['systems']['Core+ConstAddOn[1.00x]+RangeRotation']['loss_clusters']['worst_6m_cluster_return_pct']:.2f}%",
        "",
        "## Worst Underwater Episodes",
        "",
        "| System | Start | Trough | Recovery | Depth | DurationDays | RecoveryDaysFromTrough |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for system_key in ["Core+ConstAddOn[1.00x]", "Core+ConstAddOn[1.00x]+RangeRotation"]:
        episode = default["systems"][system_key]["path"]["worst_underwater_episodes"][0]
        lines.append(
            f"| {system_key} | {episode['start'][:10]} | {episode['trough'][:10]} | {(episode['recovery'][:10] if episode['recovery'] else 'open')} | "
            f"{episode['depth_pct']:.2f}% | {episode['duration_days']:.1f} | {episode['recovery_days_from_trough']:.1f} |"
        )
    lines.extend([
        "",
        "## Major Slice Comparison Vs Const1x",
        "",
        "| Slice | dReturn | dMaxDD | dCalmar |",
        "| --- | --- | --- | --- |",
    ])
    for row in default["time_slices"]:
        d = row["RangeRotation_delta_vs_Const1x"]
        lines.append(f"| {row['slice']} | {d['Return_pct']:+.2f}pp | {d['MaxDD_improvement_pct']:+.2f}pp | {d['Calmar']:+.3f} |")
    lines.extend([
        "",
        "## Yearly Outperformance",
        "",
        "| Year | Const1x | PlusRange | PlusRange-Const1x |",
        "| --- | --- | --- | --- |",
    ])
    for row in default["yearly_slices"]:
        lines.append(
            f"| {row['year']} | {row.get('Core+ConstAddOn[1.00x]', 0.0):.2f}% | {row.get('Core+ConstAddOn[1.00x]+RangeRotation', 0.0):.2f}% | {row.get('RangeRotation_minus_Const1x_pct', 0.0):+.2f}% |"
        )
    lines.extend([
        "",
        "## Operational Cleanliness",
        "",
        f"- Sleeve #2 active ratio: {default['systems']['Core+ConstAddOn[1.00x]+RangeRotation']['operational']['sleeve2_active_ratio_pct']:.2f}%",
        f"- Active overlap with Sleeve #1: {default['systems']['Core+ConstAddOn[1.00x]+RangeRotation']['operational']['active_overlap_ratio_pct']:.2f}%",
        f"- Entries while Sleeve #1 flat: {default['systems']['Core+ConstAddOn[1.00x]+RangeRotation']['operational']['candidate_entries_when_current_flat_pct']:.1f}%",
        f"- Peak total exposure: {default['systems']['Core+ConstAddOn[1.00x]+RangeRotation']['operational']['peak_total_exposure_pct']:.2f}%",
        f"- Accidental leverage flag: {'yes' if default['systems']['Core+ConstAddOn[1.00x]+RangeRotation']['operational']['accidental_leverage_flag'] else 'no'}",
        f"- Peak exposure governance flag: {'yes' if default['systems']['Core+ConstAddOn[1.00x]+RangeRotation']['operational']['peak_exposure_governance_flag'] else 'no'}",
        "",
        "## Direct Answers",
        "",
        f"1. Should range_rotation_mean_reversion be promoted as official Sleeve #2? {payload['judgment']['answer_1']}",
        f"2. What is its exact role in the portfolio? {payload['judgment']['answer_2']}",
        f"3. What are the main remaining risks? {payload['judgment']['answer_3']}",
        f"4. Is promotion recommended, conditional, or not recommended? {payload['judgment']['answer_4']}",
    ])
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")

    dec_lines = [
        "# Range Rotation Mean Reversion Promotion Decision",
        "",
        "## Final Judgment",
        "",
        f"- Status: {payload['judgment']['decision']}",
        f"- Recommendation: {payload['judgment']['promotion_recommendation']}",
        "",
        "## Direct Answers",
        "",
        f"1. Should range_rotation_mean_reversion be promoted as official Sleeve #2? {payload['judgment']['answer_1']}",
        f"2. What is its exact role in the portfolio? {payload['judgment']['answer_2']}",
        f"3. What are the main remaining risks? {payload['judgment']['answer_3']}",
        f"4. Is promotion recommended, conditional, or not recommended? {payload['judgment']['answer_4']}",
    ]
    DECISION_MD.write_text("\n".join(dec_lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    base_core_params = current_research_optimal(position_pct=100.0)
    base_range_params = make_range_rotation_params()
    scenario_payloads: List[Dict] = []
    scenario_raw: Dict[str, Dict] = {}

    for scenario in SCENARIOS:
        core_params = with_overrides(base_core_params, **scenario["overrides"])
        range_params = with_overrides(base_range_params, **scenario["overrides"])
        scenario_data = scenario_systems(core_params, range_params, df_5m, df_4h)
        scenario_raw[scenario["name"]] = scenario_data
        scenario_payloads.append(scenario_summary(scenario["name"], scenario["label"], scenario["tuple"], scenario_data))

    default_data = scenario_raw["default"]
    default_systems = default_data["systems"]

    default_detail = {"systems": {}}
    for key in ["CoreOnly", "Core+BinaryAddOn", "Core+ConstAddOn[1.00x]", "Core+ConstAddOn[1.00x]+RangeRotation"]:
        sim = default_systems[key]
        default_detail["systems"][key] = {
            "metrics": extended_metrics(sim),
            "path": path_diagnostics(sim["combo_equity"]),
            "loss_clusters": loss_cluster_diagnostics(sim["combo_equity"]),
            "operational": system_operational(sim),
        }
    default_detail["systems"]["Core+ConstAddOn[1.00x]+RangeRotation"]["operational"] = range_rotation_operational(
        default_systems["Core+ConstAddOn[1.00x]+RangeRotation"],
        default_systems["Core+ConstAddOn[1.00x]"],
        default_data["candidate_sleeve"],
        default_data["overlap"],
    )

    plus_roll_ret = rolling_return(default_systems["Core+ConstAddOn[1.00x]+RangeRotation"]["combo_equity"], ROLLING_365D_BARS)
    const_roll_ret = rolling_return(default_systems["Core+ConstAddOn[1.00x]"]["combo_equity"], ROLLING_365D_BARS)
    ret_cmp = (plus_roll_ret - const_roll_ret).dropna()
    plus_roll_dd = rolling_window_maxdd(default_systems["Core+ConstAddOn[1.00x]+RangeRotation"]["combo_equity"], ROLLING_180D_BARS)
    const_roll_dd = rolling_window_maxdd(default_systems["Core+ConstAddOn[1.00x]"]["combo_equity"], ROLLING_180D_BARS)
    dd_cmp = (const_roll_dd.abs() - plus_roll_dd.abs()).dropna()

    default_detail["path_comparison"] = {
        "rolling_365d_excess_win_ratio_pct": float((ret_cmp > 0.0).mean() * 100.0) if not ret_cmp.empty else 0.0,
        "rolling_180d_dd_improvement_win_ratio_pct": float((dd_cmp > 0.0).mean() * 100.0) if not dd_cmp.empty else 0.0,
    }
    default_detail["time_slices"] = time_slice_metrics_for_systems(default_systems)
    default_detail["yearly_slices"] = yearly_table_for_systems(default_systems)
    default_detail["overlap"] = default_data["overlap"]

    default_row = next(row for row in scenario_payloads if row["scenario"] == "default")
    stress_row = next(row for row in scenario_payloads if row["scenario"] == "stress")
    harsh_row = next(row for row in scenario_payloads if row["scenario"] == "harsh_friction")
    all_survive = all(row["ranking_survives"] for row in scenario_payloads)

    slice_map = {row["slice"]: row["RangeRotation_delta_vs_Const1x"] for row in default_detail["time_slices"]}
    major_drawdown_help = slice_map["major_drawdown"]["MaxDD_improvement_pct"] > 0.0
    sideways_help = (
        slice_map["sideways_volatility"]["MaxDD_improvement_pct"] > 0.0
        and slice_map["sideways_volatility"]["Return_pct"] > 0.0
    )
    bull_drag_acceptable = bool(
        slice_map["bull_expansion"]["MaxDD_improvement_pct"] > 0.0
        and default_row["range_vs_const1x"]["Return_pct"] > 0.0
        and default_row["range_vs_const1x"]["Calmar"] > 0.0
    )
    no_hidden_fragility = bool(
        all_survive
        and major_drawdown_help
        and sideways_help
        and bull_drag_acceptable
        and not default_detail["systems"]["Core+ConstAddOn[1.00x]+RangeRotation"]["operational"]["accidental_leverage_flag"]
    )
    governance_flag = bool(
        default_detail["systems"]["Core+ConstAddOn[1.00x]+RangeRotation"]["operational"]["peak_exposure_governance_flag"]
    )

    if no_hidden_fragility and not governance_flag:
        decision = "robust enough for official Sleeve #2 promotion"
        recommendation = "recommended"
        remaining_condition = "No remaining research or governance blocker."
    elif no_hidden_fragility and governance_flag:
        decision = "robust enough for conditional Sleeve #2 promotion"
        recommendation = "conditional"
        remaining_condition = (
            "Promotion is conditional on deployment governance accepting the explicit 300% peak total exposure envelope when both sleeves are fully active."
        )
    else:
        decision = "not yet robust enough for Sleeve #2 promotion"
        recommendation = "not recommended"
        remaining_condition = "The portfolio improvement case must survive all robustness checks without ranking flips or path-role breakdown."

    payload = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "locked_context": {
            "baseline": "Core BTC holding + ConstAddOn[1.00x]",
            "sleeve_1": "squeeze_release_20 / lb20_stop3.2_trail5.0_beoff",
            "candidate": "range_rotation_mean_reversion",
            "default_tuple": DEFAULT_TUPLE,
            "stress_tuple": STRESS_TUPLE,
        },
        "scenario_summaries": scenario_payloads,
        "default_audit": default_detail,
        "judgment": {
            "decision": decision,
            "promotion_recommendation": recommendation,
            "remaining_condition": remaining_condition,
            "answer_1": "Yes." if recommendation in {"recommended", "conditional"} else "No.",
            "answer_2": (
                "A drawdown / sideways-volatility diversification sleeve. It is not a recovery helper and should be understood as a chop-path stabilizer that improves portfolio efficiency during major drawdown and dull consolidation regimes."
            ),
            "answer_3": (
                "Main residual risks are explicit bull-expansion opportunity drag and the operational governance burden of a 300% peak total exposure envelope when both sleeves are fully active."
            ),
            "answer_4": recommendation + ".",
        },
    }
    write_reports(payload)
    print(
        json.dumps(
            {
                "decision": decision,
                "recommendation": recommendation,
                "default_delta_vs_const1x": default_row["range_vs_const1x"],
                "stress_delta_vs_const1x": stress_row["range_vs_const1x"],
                "harsh_delta_vs_const1x": harsh_row["range_vs_const1x"],
                "peak_total_exposure_pct": default_detail["systems"]["Core+ConstAddOn[1.00x]+RangeRotation"]["operational"]["peak_total_exposure_pct"],
                "all_survive": all_survive,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
