#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regime-capped AddOn study for the locked compression-breakout grading line."""

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
    assign_candidate,
    exposure_diagnostics,
    grading_scheme,
    walk_forward_compare,
)
from v90_addon_grading_study import (
    GRADE_WEIGHTS,
    bh_equity,
    compute_metrics,
    compute_slice_metrics,
    constant_weight_plan,
    current_research_optimal,
    delta_metrics,
    load_overlay_artifact,
    prepare_base_run,
    simulate_combo_from_plan,
    slice_range,
    stress_compare,
    with_overrides,
    SEED,
)


REPORT_MD = Path("BTC_ADDON_REGIME_CAP_REPORT.md")
REPORT_JSON = Path("btc_addon_regime_cap_report.json")
REPORT_TXT = Path("btc_addon_regime_cap_summary.txt")

REGIME_CAP_CONFIGS = [
    {
        "name": "cap_soft",
        "description": "Mild size cap for neutral and weak regimes.",
        "multipliers": {"strong_trend": 1.00, "neutral": 0.90, "weak_trend": 0.80},
    },
    {
        "name": "cap_base",
        "description": "Balanced cap with clearer weak-regime size reduction.",
        "multipliers": {"strong_trend": 1.00, "neutral": 0.85, "weak_trend": 0.70},
    },
    {
        "name": "cap_defensive",
        "description": "More defensive cap that pushes weak regimes close to minimum size.",
        "multipliers": {"strong_trend": 1.00, "neutral": 0.80, "weak_trend": 0.60},
    },
]


def attach_regime_features(entries: pd.DataFrame) -> pd.DataFrame:
    out = entries.copy()
    out["atr_norm"] = out["bar_range_atr"] / out["close_location"].clip(lower=0.1)
    return out


def build_regime_labels(entries: pd.DataFrame, train_mask: pd.Series) -> tuple[pd.Series, Dict]:
    df = entries.copy()
    slope_rank = df["ema_slope_atr"].rank(pct=True)
    distance_rank = df["trend_distance_atr"].rank(pct=True)
    atr_rank = df["atr_norm"].rank(pct=True)

    score = 0.4 * slope_rank + 0.4 * distance_rank + 0.2 * (1.0 - atr_rank)
    train_score = score.loc[train_mask]
    weak_cut = float(train_score.quantile(1.0 / 3.0)) if not train_score.empty else 0.33
    strong_cut = float(train_score.quantile(2.0 / 3.0)) if not train_score.empty else 0.67

    labels = pd.Series("neutral", index=df.index, dtype=object)
    labels.loc[score <= weak_cut] = "weak_trend"
    labels.loc[score >= strong_cut] = "strong_trend"
    thresholds = {
        "weak_cut": weak_cut,
        "strong_cut": strong_cut,
        "score_components": {
            "ema_slope_atr_rank": 0.4,
            "trend_distance_atr_rank": 0.4,
            "inverse_atr_rank": 0.2,
        },
        "train_trade_count": int(train_mask.sum()),
    }
    return labels, thresholds


def apply_regime_cap(graded_plan: pd.DataFrame, regime_labels: pd.Series, multipliers: Dict[str, float]) -> pd.DataFrame:
    out = graded_plan.copy()
    out["regime_label"] = regime_labels.astype(str)
    out["regime_multiplier"] = out["regime_label"].map(multipliers).astype(float)
    out["addon_weight_uncapped"] = out["addon_weight"].astype(float)
    out["addon_weight"] = (out["addon_weight_uncapped"] * out["regime_multiplier"]).clip(lower=0.0, upper=out["addon_weight_uncapped"])
    return out


def time_slice_analysis(systems: Dict[str, Dict], candidate_key: str) -> List[Dict]:
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
                baseline_key: baseline_metrics,
                candidate_key: candidate_metrics,
                "delta_vs_baseline": delta_metrics(candidate_metrics, baseline_metrics),
            }
        )
    return rows


def walk_forward_regime_cap(df_4h: pd.DataFrame, entries: pd.DataFrame, commission_pct: float, config: Dict) -> Dict:
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
        graded_plan, grade_thresholds = assign_candidate(sim_entries, sim_train_mask)
        regime_labels, regime_thresholds = build_regime_labels(sim_entries, sim_train_mask)
        capped_plan = apply_regime_cap(graded_plan, regime_labels, config["multipliers"])
        baseline_plan = constant_weight_plan(sim_entries, GRADE_WEIGHTS["base"])
        date_mask = (d4["timestamp"] >= train_start) & (d4["timestamp"] < test_end)
        d4_slice = d4.loc[date_mask].reset_index(drop=True)

        baseline = simulate_combo_from_plan(d4_slice, baseline_plan, commission_pct)
        capped = simulate_combo_from_plan(d4_slice, capped_plan, commission_pct)

        baseline_metrics = compute_slice_metrics(
            slice_range(baseline["combo_equity"], test_start.isoformat(), test_end.isoformat()),
            slice_range(baseline["combo_exposure"], test_start.isoformat(), test_end.isoformat()),
        )
        capped_metrics = compute_slice_metrics(
            slice_range(capped["combo_equity"], test_start.isoformat(), test_end.isoformat()),
            slice_range(capped["combo_exposure"], test_start.isoformat(), test_end.isoformat()),
        )
        delta = delta_metrics(capped_metrics, baseline_metrics)
        strict = bool(
            capped_metrics["TotalReturn_pct"] > baseline_metrics["TotalReturn_pct"]
            and capped_metrics["Sharpe"] > baseline_metrics["Sharpe"]
            and capped_metrics["Calmar"] > baseline_metrics["Calmar"]
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
                "grade_thresholds": grade_thresholds,
                "regime_thresholds": regime_thresholds,
                "candidate_metrics": capped_metrics,
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


def regime_cap_exposure_diagnostics(binary: Dict, graded: Dict, capped: Dict, capped_plan: pd.DataFrame) -> Dict:
    regime_counts = capped_plan["regime_label"].value_counts().to_dict()
    multiplier_dist = capped_plan["regime_multiplier"].value_counts(normalize=True).sort_index().to_dict()
    trade_counts = capped_plan["grade_label"].value_counts().to_dict()
    return {
        "avg_total_exposure_binary_pct": float(binary["combo_exposure"].mean() * 100.0),
        "avg_total_exposure_graded_pct": float(graded["combo_exposure"].mean() * 100.0),
        "avg_total_exposure_capped_pct": float(capped["combo_exposure"].mean() * 100.0),
        "avg_total_exposure_delta_vs_binary_pct": float((capped["combo_exposure"].mean() - binary["combo_exposure"].mean()) * 100.0),
        "addon_activation_ratio_binary_pct": binary["sleeve"]["active_ratio_pct"],
        "addon_activation_ratio_graded_pct": graded["sleeve"]["active_ratio_pct"],
        "addon_activation_ratio_capped_pct": capped["sleeve"]["active_ratio_pct"],
        "avg_addon_weight_when_active_graded": graded["sleeve"]["avg_weight_when_active"],
        "avg_addon_weight_when_active_capped": capped["sleeve"]["avg_weight_when_active"],
        "trend_participation_ratio_vs_binary": 0.0 if binary["sleeve"]["weight"].mean() <= 0 else float(capped["sleeve"]["weight"].mean() / binary["sleeve"]["weight"].mean()),
        "trend_participation_ratio_vs_graded": 0.0 if graded["sleeve"]["weight"].mean() <= 0 else float(capped["sleeve"]["weight"].mean() / graded["sleeve"]["weight"].mean()),
        "regime_label_counts": {k: int(regime_counts.get(k, 0)) for k in ["strong_trend", "neutral", "weak_trend"]},
        "regime_multiplier_distribution_pct": {str(k): float(v * 100.0) for k, v in multiplier_dist.items()},
        "grade_distribution": {k: int(trade_counts.get(k, 0)) for k in ["weak", "base", "strong"]},
        "accidental_leverage_flag": bool((capped["combo_exposure"].mean() - binary["combo_exposure"].mean()) > 0.02),
    }


def write_report(payload: Dict) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    best_key = payload["best_candidate"]
    best = payload["candidates"][best_key]
    lines = [
        "# BTC AddOn Regime Cap Report",
        "",
        "## Final Judgment",
        "",
        f"- Regime-cap answer: {payload['judgment']['promotion_candidate_answer']}",
        f"- Best regime-cap candidate: {best_key}",
        f"- Baseline decision: {payload['judgment']['baseline_decision']}",
        f"- Extension-line decision: {payload['judgment']['extension_line_decision']}",
        "",
        "## Baseline Alignment",
        "",
        f"- Binary AddOn drift vs committed artifact: Return {payload['baseline_alignment']['binary_vs_artifact']['delta_return_pct']:+.2f}pp, Sharpe {payload['baseline_alignment']['binary_vs_artifact']['delta_sharpe']:+.3f}, Calmar {payload['baseline_alignment']['binary_vs_artifact']['delta_calmar']:+.3f}, MaxDD improve {payload['baseline_alignment']['binary_vs_artifact']['delta_maxdd_improve_pct']:+.2f}pp",
        f"- Graded AddOn drift vs committed promotion result: Return {payload['baseline_alignment']['graded_vs_artifact']['delta_return_pct']:+.2f}pp, Sharpe {payload['baseline_alignment']['graded_vs_artifact']['delta_sharpe']:+.3f}, Calmar {payload['baseline_alignment']['graded_vs_artifact']['delta_calmar']:+.3f}, MaxDD improve {payload['baseline_alignment']['graded_vs_artifact']['delta_maxdd_improve_pct']:+.2f}pp",
        "",
        "## Full-Sample Comparison",
        "",
        "| Structure | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Exposure% | dRet vs Binary | dSharpe | dCalmar | dMaxDD |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key in ["Core+BinaryAddOn", "Core+GradedAddOn[compression_breakout]", best_key]:
        row = payload["systems"][key]
        m = row["metrics"]
        d = row["delta_vs_binary"]
        lines.append(
            f"| {key} | {m['TotalReturn_pct']:.2f} | {m['CAGR_pct']:.2f} | {m['Sharpe']:.3f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | {m['Exposure_pct']:.1f} | {d['Return_pct']:+.2f} | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f} |"
        )
    lines.extend([
        "",
        "## Candidate Table",
        "",
        "| Candidate | dRet vs Binary | dSharpe | dCalmar | dMaxDD | WF strict | WF dRet | WF dSharpe | WF dCalmar | WF dMaxDD |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for key, row in payload["candidates"].items():
        d = row["delta_vs_binary"]
        wf = row["walk_forward"]["default"]
        lines.append(
            f"| {key} | {d['Return_pct']:+.2f} | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f} | {wf['strict_win_ratio']:.2f} | {wf['avg_delta_return_pct']:+.2f} | {wf['avg_delta_sharpe']:+.3f} | {wf['avg_delta_calmar']:+.3f} | {wf['avg_delta_maxdd_improvement_pct']:+.2f} |"
        )
    lines.extend([
        "",
        "## Time-Slice Diagnostics",
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
        "## Exposure Diagnostics",
        "",
        f"- Avg total exposure vs binary: {exp['avg_total_exposure_delta_vs_binary_pct']:+.2f}pp",
        f"- AddOn activation ratio: binary {exp['addon_activation_ratio_binary_pct']:.1f}% / graded {exp['addon_activation_ratio_graded_pct']:.1f}% / capped {exp['addon_activation_ratio_capped_pct']:.1f}%",
        f"- Avg AddOn size when active: graded {exp['avg_addon_weight_when_active_graded']:.3f} / capped {exp['avg_addon_weight_when_active_capped']:.3f}",
        f"- Trend participation ratio vs binary: {exp['trend_participation_ratio_vs_binary']:.3f}",
        f"- Accidental leverage flag: {'yes' if exp['accidental_leverage_flag'] else 'no'}",
        "",
        "## Execution Stress",
        "",
        f"- Stress delta on best capped candidate: Return {best['execution_stress']['Return_pct']:+.2f}pp, Sharpe {best['execution_stress']['Sharpe']:+.3f}, Calmar {best['execution_stress']['Calmar']:+.3f}, MaxDD improve {best['execution_stress']['MaxDD_improvement_pct']:+.2f}pp",
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
    d4 = ensure_datetime(df_4h)

    overlay = load_overlay_artifact()
    grading_promo = json.loads(Path("btc_addon_grading_promotion_report.json").read_text(encoding="utf-8"))

    params_default = current_research_optimal(position_pct=100.0)
    params_stress = with_overrides(
        params_default,
        entry_execution_mode="live_runner_next_5m_close",
        intrabar_execution_model="segment_path_same_bar",
        intrabar_path_mode="pessimistic",
    )

    base_default = prepare_base_run(df_5m, df_4h, params_default)
    base_stress = prepare_base_run(df_5m, df_4h, params_stress)
    base_default["entries"] = attach_regime_features(base_default["entries"])
    base_stress["entries"] = attach_regime_features(base_stress["entries"])

    binary_plan_default = constant_weight_plan(base_default["entries"], GRADE_WEIGHTS["base"])
    binary_plan_stress = constant_weight_plan(base_stress["entries"], GRADE_WEIGHTS["base"])
    graded_plan_default, grade_thresholds_full = assign_candidate(base_default["entries"], pd.Series(True, index=base_default["entries"].index))
    graded_plan_stress, _ = assign_candidate(base_stress["entries"], pd.Series(True, index=base_stress["entries"].index))

    bh_eq = bh_equity(d4.set_index("timestamp")["close"].astype(float))
    bh_exp = pd.Series(1.0, index=bh_eq.index, dtype=float)
    bh_metrics = compute_metrics(bh_eq, bh_exp)

    binary_default = simulate_combo_from_plan(df_4h, binary_plan_default, float(params_default.commission_pct))
    binary_stress = simulate_combo_from_plan(df_4h, binary_plan_stress, float(params_stress.commission_pct))
    graded_default = simulate_combo_from_plan(df_4h, graded_plan_default, float(params_default.commission_pct))
    graded_stress = simulate_combo_from_plan(df_4h, graded_plan_stress, float(params_stress.commission_pct))

    baseline_alignment = {
        "binary_vs_artifact": {
            "delta_return_pct": float(binary_default["combo_metrics"]["TotalReturn_pct"] - float(overlay["addon_metrics"]["TotalReturn_pct"])),
            "delta_sharpe": float(binary_default["combo_metrics"]["Sharpe"] - float(overlay["addon_metrics"]["Sharpe"])),
            "delta_calmar": float(binary_default["combo_metrics"]["Calmar"] - float(overlay["addon_metrics"]["Calmar"])),
            "delta_maxdd_improve_pct": float(abs(float(overlay["addon_metrics"]["MaxDD_pct"])) - abs(binary_default["combo_metrics"]["MaxDD_pct"])),
        },
        "graded_vs_artifact": {
            "delta_return_pct": float(graded_default["combo_metrics"]["TotalReturn_pct"] - float(grading_promo["systems"]["Core+GradedAddOn[compression_breakout]"]["metrics"]["TotalReturn_pct"])),
            "delta_sharpe": float(graded_default["combo_metrics"]["Sharpe"] - float(grading_promo["systems"]["Core+GradedAddOn[compression_breakout]"]["metrics"]["Sharpe"])),
            "delta_calmar": float(graded_default["combo_metrics"]["Calmar"] - float(grading_promo["systems"]["Core+GradedAddOn[compression_breakout]"]["metrics"]["Calmar"])),
            "delta_maxdd_improve_pct": float(abs(float(grading_promo["systems"]["Core+GradedAddOn[compression_breakout]"]["metrics"]["MaxDD_pct"])) - abs(graded_default["combo_metrics"]["MaxDD_pct"])),
        },
    }

    systems = {
        "Core+BinaryAddOn": {
            "equity": binary_default["combo_equity"],
            "exposure": binary_default["combo_exposure"],
            "metrics": binary_default["combo_metrics"],
            "delta_vs_binary": {"Return_pct": 0.0, "Sharpe": 0.0, "Calmar": 0.0, "MaxDD_improvement_pct": 0.0},
        },
        "Core+GradedAddOn[compression_breakout]": {
            "equity": graded_default["combo_equity"],
            "exposure": graded_default["combo_exposure"],
            "metrics": graded_default["combo_metrics"],
            "delta_vs_binary": delta_metrics(graded_default["combo_metrics"], binary_default["combo_metrics"]),
        },
    }

    candidate_rows = {}
    for config in REGIME_CAP_CONFIGS:
        regime_labels_default, regime_thresholds_full = build_regime_labels(base_default["entries"], pd.Series(True, index=base_default["entries"].index))
        regime_labels_stress, _ = build_regime_labels(base_stress["entries"], pd.Series(True, index=base_stress["entries"].index))
        capped_plan_default = apply_regime_cap(graded_plan_default, regime_labels_default, config["multipliers"])
        capped_plan_stress = apply_regime_cap(graded_plan_stress, regime_labels_stress, config["multipliers"])
        capped_default = simulate_combo_from_plan(df_4h, capped_plan_default, float(params_default.commission_pct))
        capped_stress = simulate_combo_from_plan(df_4h, capped_plan_stress, float(params_stress.commission_pct))
        key = f"Core+RegimeCappedAddOn[{config['name']}]"
        systems[key] = {
            "equity": capped_default["combo_equity"],
            "exposure": capped_default["combo_exposure"],
            "metrics": capped_default["combo_metrics"],
            "delta_vs_binary": delta_metrics(capped_default["combo_metrics"], binary_default["combo_metrics"]),
        }
        wf_default = walk_forward_regime_cap(df_4h, base_default["entries"], float(params_default.commission_pct), config)
        wf_stress = walk_forward_regime_cap(df_4h, base_stress["entries"], float(params_stress.commission_pct), config)
        stress_delta = stress_compare({key: capped_default}, {key: capped_stress})[key]["delta_vs_default_same_scheme"]
        candidate_rows[key] = {
            "config": config,
            "grade_thresholds_full": grade_thresholds_full,
            "regime_thresholds_full": regime_thresholds_full,
            "metrics": capped_default["combo_metrics"],
            "delta_vs_binary": systems[key]["delta_vs_binary"],
            "delta_vs_graded": delta_metrics(capped_default["combo_metrics"], graded_default["combo_metrics"]),
            "walk_forward": {"default": wf_default, "stress": wf_stress},
            "time_slices": time_slice_analysis(systems, key),
            "execution_stress": stress_delta,
            "exposure_diagnostics": regime_cap_exposure_diagnostics(binary_default, graded_default, capped_default, capped_plan_default),
        }

    best_key = sorted(
        candidate_rows,
        key=lambda k: (
            candidate_rows[k]["walk_forward"]["default"]["strict_win_ratio"],
            candidate_rows[k]["walk_forward"]["default"]["avg_delta_calmar"],
            candidate_rows[k]["delta_vs_binary"]["MaxDD_improvement_pct"],
            candidate_rows[k]["delta_vs_binary"]["Sharpe"],
            candidate_rows[k]["delta_vs_binary"]["Return_pct"],
        ),
        reverse=True,
    )[0]
    best = candidate_rows[best_key]
    promotion_candidate = bool(
        best["walk_forward"]["default"]["strict_win_ratio"] >= 2.0 / 3.0
        and best["walk_forward"]["default"]["avg_delta_calmar"] > 0.0
        and best["delta_vs_binary"]["MaxDD_improvement_pct"] >= 0.0
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
            "type": "regime_cap_modulation_only",
            "base_grading_scheme": grading_scheme(),
            "tested_configs": REGIME_CAP_CONFIGS,
            "note": "No new signals, no mother-strategy change, no Risk-Off logic. Only graded AddOn size modulation.",
        },
        "baseline_alignment": baseline_alignment,
        "systems": {
            key: {
                "metrics": value["metrics"],
                "delta_vs_binary": value["delta_vs_binary"],
            }
            for key, value in systems.items()
        },
        "candidates": candidate_rows,
        "best_candidate": best_key,
        "judgment": {
            "promotion_candidate": promotion_candidate,
            "promotion_candidate_answer": "YES. Regime-capped graded AddOn is strong enough to become a promotion candidate." if promotion_candidate else "NO. Regime-capped graded AddOn does not yet clear promotion-candidate validation.",
            "baseline_decision": "Keep baseline unchanged" if not promotion_candidate else "Advance capped grading into promotion review",
            "extension_line_decision": "Yes. AddOn grading should keep moving toward an exposure-engine style extension line." if best["walk_forward"]["default"]["avg_delta_calmar"] > 0.0 else "Keep AddOn grading active, but do not yet broaden it into a larger exposure-engine program.",
            "answer_1": (
                f"{best_key} {'does' if promotion_candidate else 'does not'} outperform the binary AddOn baseline strongly enough on the full validation set."
            ),
            "answer_2": f"OOS stability is {'preserved' if best['walk_forward']['default']['strict_win_ratio'] >= 2.0 / 3.0 else 'not preserved'}: strict win ratio {best['walk_forward']['default']['strict_win_ratio']:.2f}, avg dReturn {best['walk_forward']['default']['avg_delta_return_pct']:+.2f}pp, avg dSharpe {best['walk_forward']['default']['avg_delta_sharpe']:+.3f}, avg dCalmar {best['walk_forward']['default']['avg_delta_calmar']:+.3f}.",
            "answer_3": (
                "The regime cap removes the prior MaxDD degradation."
                if best["delta_vs_binary"]["MaxDD_improvement_pct"] >= 0.0
                else f"The regime cap does not fully remove MaxDD degradation; best full-sample dMaxDD is {best['delta_vs_binary']['MaxDD_improvement_pct']:+.2f}pp."
            ),
            "answer_4": (
                "Yes. This structure can be considered a promotion candidate."
                if promotion_candidate
                else "No. This structure still cannot be considered a promotion candidate."
            ),
            "answer_5": "Yes. AddOn grading should move toward an exposure-engine design, but only through narrow modulation layers like this one, not by opening new strategy families.",
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
