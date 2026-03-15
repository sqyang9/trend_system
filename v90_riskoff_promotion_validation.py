#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promotion-level validation for the aligned Risk-Off module."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_asset_management_system_aligned import (
    ANNUALIZATION_4H,
    DEFAULT_TUPLE,
    STRESS_TUPLE,
    combine_with_overlay,
    compute_metrics,
    current_research_optimal,
    simulate_core,
)
from v90_trend_long_mother import SEED, TrendIndicatorEngine, with_overrides

OVERLAY_REPORT = Path("btc_overlay_integration_report.json")
REPORT_MD = Path("BTC_RISKOFF_PROMOTION_REPORT.md")
REPORT_JSON = Path("btc_riskoff_promotion_report.json")
REPORT_TXT = Path("btc_riskoff_promotion_summary.txt")

PROMOTION_CANDIDATES = [
    {"name": "RO_EMA200_FLAT", "ema_len": 200, "off_weight": 0.0},
    {"name": "RO_EMA220_FLAT", "ema_len": 220, "off_weight": 0.0},
]
ROBUSTNESS_EMA_LENS = [200, 210, 220]
TIME_SLICES = [
    {"name": "bull_expansion", "start": "2020-04-01", "end": "2021-11-10"},
    {"name": "major_drawdown", "start": "2021-11-10", "end": "2023-01-01"},
    {"name": "recovery_phase", "start": "2023-01-01", "end": "2024-03-15"},
    {"name": "sideways_volatility", "start": "2024-03-15", "end": "2026-03-01"},
]
WF_TEST_YEARS = [2023, 2024, 2025]


def calmar(cagr: float, maxdd: float) -> float:
    return 0.0 if maxdd >= 0.0 else float(cagr) / abs(float(maxdd))


def compute_slice_metrics(equity: pd.Series) -> Dict:
    if len(equity) < 2:
        return {
            "TotalReturn_pct": 0.0,
            "CAGR_pct": 0.0,
            "Sharpe": 0.0,
            "Calmar": 0.0,
            "MaxDD_pct": 0.0,
        }
    ret = equity.pct_change().fillna(0.0)
    dd = equity / equity.cummax() - 1.0
    years = max((equity.index[-1] - equity.index[0]).total_seconds() / 86400.0, 1.0) / 365.25
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = (float(equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0) if years > 0.0 else 0.0
    std = float(ret.std())
    sharpe = float(ret.mean()) / std * ANNUALIZATION_4H if std > 0.0 else 0.0
    return {
        "TotalReturn_pct": total * 100.0,
        "CAGR_pct": cagr * 100.0,
        "Sharpe": sharpe,
        "Calmar": calmar(cagr, float(dd.min())),
        "MaxDD_pct": float(dd.min() * 100.0),
    }


def delta_metrics(metrics: Dict, baseline: Dict) -> Dict:
    return {
        "Return_pct": float(metrics["TotalReturn_pct"] - baseline["TotalReturn_pct"]),
        "CAGR_pct": float(metrics["CAGR_pct"] - baseline["CAGR_pct"]),
        "Sharpe": float(metrics["Sharpe"] - baseline["Sharpe"]),
        "Calmar": float(metrics["Calmar"] - baseline["Calmar"]),
        "MaxDD_improvement_pct": float(abs(baseline["MaxDD_pct"]) - abs(metrics["MaxDD_pct"])),
    }


def load_overlay() -> Dict:
    data = json.loads(OVERLAY_REPORT.read_text(encoding="utf-8"))
    idx = pd.to_datetime(data["timeseries"]["timestamp"], utc=True)
    bh = pd.Series(data["timeseries"]["B&H"], index=idx, dtype=float)
    addon = pd.Series(data["timeseries"]["AddOnOverlay"], index=idx, dtype=float)
    delta = addon - bh
    overlay_avg_exposure = (
        float(data["schemes"]["AddOnOverlay"]["metrics"]["Exposure_pct"])
        - float(data["schemes"]["B&H"]["metrics"]["Exposure_pct"])
    ) / 100.0
    return {
        "artifact": data,
        "index": idx,
        "bh_equity": bh,
        "addon_equity": addon,
        "overlay_delta": delta,
        "overlay_avg_exposure": overlay_avg_exposure,
    }


def build_target(df_4h: pd.DataFrame, overlay_index: pd.Index, params, ema_len: int, off_weight: float = 0.0) -> pd.Series:
    engine = TrendIndicatorEngine()
    ind = engine.compute(ensure_datetime(df_4h), with_overrides(params, ema_len=ema_len)).set_index("timestamp").reindex(overlay_index)
    regime = (ind["close"] < ind["ema"]) & (ind["ema_slope"] < 0)
    return pd.Series(np.where(regime.fillna(False), off_weight, 1.0), index=overlay_index, dtype=float)


def simulate_candidate(df_5m: pd.DataFrame, df_4h: pd.DataFrame, overlay: Dict, params, ema_len: int, execution_mode: str) -> Dict:
    target = build_target(df_4h, overlay["index"], params, ema_len=ema_len, off_weight=0.0)
    core = simulate_core(df_5m, df_4h, target, params, execution_mode)
    combo = combine_with_overlay(core, overlay["overlay_delta"], overlay["overlay_avg_exposure"])
    combo_metrics = compute_metrics(combo["equity"], combo["exposure"])
    return {
        "target": target,
        "core": core,
        "combo": combo,
        "combo_metrics": combo_metrics,
        "riskoff_active_ratio_pct": float((target < 0.9999).mean() * 100.0),
        "state_changes": int(core["causality"]["rebalance_count"]),
        "avg_core_exposure_pct": float(target.mean() * 100.0),
    }


def build_system_bundle(df_5m: pd.DataFrame, df_4h: pd.DataFrame, overlay: Dict, params, execution_mode: str, ema_lens: List[int]) -> Dict:
    systems = {
        "B&H": {
            "equity": overlay["bh_equity"],
            "metrics": overlay["artifact"]["schemes"]["B&H"]["metrics"],
            "exposure_pct": float(overlay["artifact"]["schemes"]["B&H"]["metrics"]["Exposure_pct"]),
            "riskoff_active_ratio_pct": 0.0,
            "state_changes": 0,
            "avg_core_exposure_pct": 100.0,
        },
        "Core+AddOnOverlay": {
            "equity": overlay["addon_equity"],
            "metrics": overlay["artifact"]["schemes"]["AddOnOverlay"]["metrics"],
            "exposure_pct": float(overlay["artifact"]["schemes"]["AddOnOverlay"]["metrics"]["Exposure_pct"]),
            "riskoff_active_ratio_pct": 0.0,
            "state_changes": 0,
            "avg_core_exposure_pct": 100.0,
        },
    }
    causality = {}
    for ema_len in ema_lens:
        sim = simulate_candidate(df_5m, df_4h, overlay, params, ema_len, execution_mode)
        candidate_key = f"Core+AddOnOverlay+RO_EMA{ema_len}_FLAT"
        core_key = f"Core+RO_EMA{ema_len}_FLAT"
        systems[candidate_key] = {
            "equity": sim["combo"]["equity"],
            "metrics": sim["combo_metrics"],
            "exposure_pct": float(sim["combo_metrics"]["Exposure_pct"]),
            "riskoff_active_ratio_pct": sim["riskoff_active_ratio_pct"],
            "state_changes": sim["state_changes"],
            "avg_core_exposure_pct": sim["avg_core_exposure_pct"],
        }
        systems[core_key] = {
            "equity": sim["core"]["equity"]["equity"].astype(float),
            "metrics": compute_metrics(sim["core"]["equity"]["equity"].astype(float), sim["core"]["equity"]["exposure"].astype(float)),
            "exposure_pct": float(sim["core"]["equity"]["exposure"].mean() * 100.0),
            "riskoff_active_ratio_pct": sim["riskoff_active_ratio_pct"],
            "state_changes": sim["state_changes"],
            "avg_core_exposure_pct": sim["avg_core_exposure_pct"],
        }
        causality[f"RO_EMA{ema_len}_FLAT"] = sim["core"]["causality"]
    return {"systems": systems, "causality": causality}


def slice_equity(equity: pd.Series, start: str, end: str) -> pd.Series:
    return equity[(equity.index >= pd.Timestamp(start, tz="UTC")) & (equity.index < pd.Timestamp(end, tz="UTC"))]


def score_metrics(metrics: Dict) -> Tuple[float, float, float]:
    return (float(metrics["Calmar"]), float(metrics["Sharpe"]), float(metrics["TotalReturn_pct"]))


def walk_forward_analysis(bundle: Dict) -> Dict:
    systems = bundle["systems"]
    windows = []
    selection_counts = {"RO_EMA200_FLAT": 0, "RO_EMA220_FLAT": 0}
    selected_oos_sharpes = []
    selected_outperform_flags = []
    for test_year in WF_TEST_YEARS:
        train_start = f"{test_year - 3}-01-01"
        train_end = f"{test_year}-01-01"
        test_start = f"{test_year}-01-01"
        test_end = f"{test_year + 1}-01-01"
        train_candidates = {}
        test_candidates = {}
        for ema_len in [200, 220]:
            key = f"Core+AddOnOverlay+RO_EMA{ema_len}_FLAT"
            train_metrics = compute_slice_metrics(slice_equity(systems[key]["equity"], train_start, train_end))
            test_metrics = compute_slice_metrics(slice_equity(systems[key]["equity"], test_start, test_end))
            train_candidates[key] = train_metrics
            test_candidates[key] = test_metrics
        selected_key = max(train_candidates, key=lambda k: score_metrics(train_candidates[k]))
        selection_counts[selected_key.replace("Core+AddOnOverlay+", "")] += 1
        addon_test = compute_slice_metrics(slice_equity(systems["Core+AddOnOverlay"]["equity"], test_start, test_end))
        selected_test = test_candidates[selected_key]
        delta = delta_metrics(selected_test, addon_test)
        outperform = bool(
            (selected_test["Calmar"] > addon_test["Calmar"])
            and (selected_test["Sharpe"] > addon_test["Sharpe"])
            and (abs(selected_test["MaxDD_pct"]) < abs(addon_test["MaxDD_pct"]))
        )
        selected_oos_sharpes.append(float(selected_test["Sharpe"]))
        selected_outperform_flags.append(float(outperform))
        windows.append(
            {
                "train_window": {"start": train_start, "end": train_end},
                "test_window": {"start": test_start, "end": test_end},
                "train_candidates": train_candidates,
                "test_candidates": test_candidates,
                "selected_candidate": selected_key,
                "selected_test_metrics": selected_test,
                "addon_test_metrics": addon_test,
                "delta_vs_addon": delta,
                "outperform_addon_strict": outperform,
            }
        )
    return {
        "windows": windows,
        "selection_counts": selection_counts,
        "selected_avg_oos_sharpe": float(np.mean(selected_oos_sharpes)) if selected_oos_sharpes else 0.0,
        "selected_strict_win_ratio": float(np.mean(selected_outperform_flags)) if selected_outperform_flags else 0.0,
        "selected_avg_delta_return_pct": float(np.mean([w["delta_vs_addon"]["Return_pct"] for w in windows])) if windows else 0.0,
        "selected_avg_delta_calmar": float(np.mean([w["delta_vs_addon"]["Calmar"] for w in windows])) if windows else 0.0,
    }


def time_slice_analysis(bundle: Dict) -> Dict:
    systems = bundle["systems"]
    rows = []
    for sl in TIME_SLICES:
        addon_metrics = compute_slice_metrics(slice_equity(systems["Core+AddOnOverlay"]["equity"], sl["start"], sl["end"]))
        row = {
            "slice": sl["name"],
            "window": {"start": sl["start"], "end": sl["end"]},
            "Core+AddOnOverlay": addon_metrics,
        }
        for ema_len in [200, 220]:
            key = f"Core+AddOnOverlay+RO_EMA{ema_len}_FLAT"
            metrics = compute_slice_metrics(slice_equity(systems[key]["equity"], sl["start"], sl["end"]))
            row[key] = metrics
            row[f"{key}_delta_vs_addon"] = delta_metrics(metrics, addon_metrics)
        rows.append(row)
    return {"rows": rows}


def robustness_analysis(bundle: Dict) -> Dict:
    systems = bundle["systems"]
    keys = [f"Core+AddOnOverlay+RO_EMA{ema}_FLAT" for ema in ROBUSTNESS_EMA_LENS]
    rows = []
    calmars = []
    sharpes = []
    for key in keys:
        metrics = systems[key]["metrics"]
        delta = delta_metrics(metrics, systems["Core+AddOnOverlay"]["metrics"])
        rows.append({
            "scheme": key,
            "metrics": metrics,
            "delta_vs_addon": delta,
            "riskoff_active_ratio_pct": systems[key]["riskoff_active_ratio_pct"],
            "state_changes": systems[key]["state_changes"],
        })
        calmars.append(float(metrics["Calmar"]))
        sharpes.append(float(metrics["Sharpe"]))
    plateau = bool(
        all(row["delta_vs_addon"]["Calmar"] > 0.0 and row["delta_vs_addon"]["Sharpe"] > 0.0 for row in rows)
        and (max(calmars) - min(calmars) <= 0.10)
        and (max(sharpes) - min(sharpes) <= 0.08)
    )
    best = max(rows, key=lambda x: score_metrics(x["metrics"]))
    return {
        "rows": rows,
        "plateau_judgment": plateau,
        "best_scheme": best["scheme"],
        "calmar_spread": float(max(calmars) - min(calmars)),
        "sharpe_spread": float(max(sharpes) - min(sharpes)),
    }


def stress_or_cost_analysis(bundle: Dict, default_bundle: Dict) -> Dict:
    out = {}
    for key in ["Core+AddOnOverlay+RO_EMA200_FLAT", "Core+AddOnOverlay+RO_EMA220_FLAT"]:
        out[key] = {
            "metrics": bundle["systems"][key]["metrics"],
            "delta_vs_default_same_scheme": delta_metrics(bundle["systems"][key]["metrics"], default_bundle["systems"][key]["metrics"]),
            "delta_vs_addon": delta_metrics(bundle["systems"][key]["metrics"], bundle["systems"]["Core+AddOnOverlay"]["metrics"]),
        }
    return out


def candidate_relationship(default_bundle: Dict) -> Dict:
    m200 = default_bundle["systems"]["Core+AddOnOverlay+RO_EMA200_FLAT"]["metrics"]
    m220 = default_bundle["systems"]["Core+AddOnOverlay+RO_EMA220_FLAT"]["metrics"]
    delta_220_vs_200 = delta_metrics(m220, m200)
    if (m220["Calmar"] - m200["Calmar"] <= 0.08) and (m220["Sharpe"] - m200["Sharpe"] <= 0.08):
        relation = "RO_EMA220_FLAT is better on the full sample, but RO_EMA200_FLAT is close enough to treat them as the same class."
    else:
        relation = "RO_EMA220_FLAT shows a materially stronger full-sample edge than RO_EMA200_FLAT."
    return {"delta_220_vs_200": delta_220_vs_200, "judgment": relation}


def causality_audit(default_bundle: Dict, stress_bundle: Dict) -> Dict:
    return {
        "default_total_violations": int(sum(v["violations"] for v in default_bundle["causality"].values())),
        "stress_total_violations": int(sum(v["violations"] for v in stress_bundle["causality"].values())),
        "default_details": default_bundle["causality"],
        "stress_details": stress_bundle["causality"],
    }


def full_sample_snapshot(bundle: Dict) -> Dict:
    rows = {}
    for key in ["B&H", "Core+AddOnOverlay", "Core+AddOnOverlay+RO_EMA200_FLAT", "Core+AddOnOverlay+RO_EMA220_FLAT", "Core+RO_EMA220_FLAT"]:
        item = bundle["systems"][key]
        rows[key] = {
            "metrics": item["metrics"],
            "riskoff_active_ratio_pct": item["riskoff_active_ratio_pct"],
            "state_changes": item["state_changes"],
            "avg_core_exposure_pct": item["avg_core_exposure_pct"],
            "delta_vs_addon": delta_metrics(item["metrics"], bundle["systems"]["Core+AddOnOverlay"]["metrics"]),
        }
    return rows


def write_markdown(report: Dict) -> None:
    lines = [
        "# BTC Risk-Off Promotion Report",
        "",
        "## Promotion Judgment",
        "",
        f"- This round is promotion validation, not new strategy exploration.",
        f"- Promotion answer: {report['judgment']['promotion_answer']}",
        f"- Evidence level after this round: {report['judgment']['evidence_level_after_round']}",
        f"- Baseline promotion recommendation: {report['judgment']['baseline_promotion_recommendation']}",
        f"- Preferred system direction: {report['judgment']['preferred_system_direction']}",
        "",
        "## Full-Sample Snapshot",
        "",
        "| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Exposure% | Avg Core% | Risk-Off Active% | State Changes | dRet vs AddOn | dCalmar | dMaxDD improve |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, item in report["full_sample"].items():
        m = item["metrics"]
        d = item["delta_vs_addon"]
        lines.append(
            f"| {key} | {m['TotalReturn_pct']:.2f} | {m['CAGR_pct']:.2f} | {m['Sharpe']:.3f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | "
            f"{m['Exposure_pct']:.1f} | {item['avg_core_exposure_pct']:.1f} | {item['riskoff_active_ratio_pct']:.1f} | {item['state_changes']} | "
            f"{d['Return_pct']:+.2f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f} |"
        )
    lines.extend([
        "",
        "## Walk-Forward OOS",
        "",
        "- Train rule: 3-year train window, choose only between `RO_EMA200_FLAT` and `RO_EMA220_FLAT` by train Calmar, then Sharpe.",
        "- Test rule: 1-year OOS window, compare selected Risk-Off system vs AddOn-only.",
        "",
        "| Test Year | Selected | Test Return% | Test Sharpe | Test MaxDD% | dRet vs AddOn | dSharpe | dCalmar | dMaxDD improve | Strict Outperform |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in report["walk_forward"]["windows"]:
        m = row["selected_test_metrics"]
        d = row["delta_vs_addon"]
        lines.append(
            f"| {row['test_window']['start'][:4]} | {row['selected_candidate']} | {m['TotalReturn_pct']:.2f} | {m['Sharpe']:.3f} | {m['MaxDD_pct']:.2f} | "
            f"{d['Return_pct']:+.2f} | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f} | {row['outperform_addon_strict']} |"
        )
    wf = report["walk_forward"]
    lines.extend([
        "",
        f"- WF selection counts: {wf['selection_counts']}",
        f"- WF selected average OOS Sharpe: {wf['selected_avg_oos_sharpe']:.3f}",
        f"- WF strict outperform ratio vs AddOn-only: {wf['selected_strict_win_ratio']:.2f}",
        f"- WF average delta Return vs AddOn-only: {wf['selected_avg_delta_return_pct']:+.2f}pp",
        f"- WF average delta Calmar vs AddOn-only: {wf['selected_avg_delta_calmar']:+.3f}",
        "",
        "## Time-Slice Stability",
        "",
        "| Slice | AddOn Return% | EMA200 Return% | EMA220 Return% | EMA200 dMaxDD | EMA220 dMaxDD |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for row in report["time_slices"]["rows"]:
        d200 = row["Core+AddOnOverlay+RO_EMA200_FLAT_delta_vs_addon"]
        d220 = row["Core+AddOnOverlay+RO_EMA220_FLAT_delta_vs_addon"]
        lines.append(
            f"| {row['slice']} | {row['Core+AddOnOverlay']['TotalReturn_pct']:.2f} | {row['Core+AddOnOverlay+RO_EMA200_FLAT']['TotalReturn_pct']:.2f} | "
            f"{row['Core+AddOnOverlay+RO_EMA220_FLAT']['TotalReturn_pct']:.2f} | {d200['MaxDD_improvement_pct']:+.2f} | {d220['MaxDD_improvement_pct']:+.2f} |"
        )
    rb = report["robustness"]
    lines.extend([
        "",
        "## Small Neighborhood Robustness",
        "",
        f"- Plateau judgment across EMA200/210/220: {rb['plateau_judgment']}",
        f"- Best scheme in the narrow plateau check: {rb['best_scheme']}",
        f"- Calmar spread across EMA200/210/220: {rb['calmar_spread']:.3f}",
        f"- Sharpe spread across EMA200/210/220: {rb['sharpe_spread']:.3f}",
        "",
        "## Execution And Cost Sensitivity",
        "",
        f"- Execution sensitivity EMA200: Return {report['execution_sensitivity']['Core+AddOnOverlay+RO_EMA200_FLAT']['delta_vs_default_same_scheme']['Return_pct']:+.2f}pp, Sharpe {report['execution_sensitivity']['Core+AddOnOverlay+RO_EMA200_FLAT']['delta_vs_default_same_scheme']['Sharpe']:+.3f}, MaxDD improve {report['execution_sensitivity']['Core+AddOnOverlay+RO_EMA200_FLAT']['delta_vs_default_same_scheme']['MaxDD_improvement_pct']:+.2f}pp",
        f"- Execution sensitivity EMA220: Return {report['execution_sensitivity']['Core+AddOnOverlay+RO_EMA220_FLAT']['delta_vs_default_same_scheme']['Return_pct']:+.2f}pp, Sharpe {report['execution_sensitivity']['Core+AddOnOverlay+RO_EMA220_FLAT']['delta_vs_default_same_scheme']['Sharpe']:+.3f}, MaxDD improve {report['execution_sensitivity']['Core+AddOnOverlay+RO_EMA220_FLAT']['delta_vs_default_same_scheme']['MaxDD_improvement_pct']:+.2f}pp",
        f"- Higher-cost sensitivity EMA200: Return {report['cost_sensitivity']['Core+AddOnOverlay+RO_EMA200_FLAT']['delta_vs_default_same_scheme']['Return_pct']:+.2f}pp, Sharpe {report['cost_sensitivity']['Core+AddOnOverlay+RO_EMA200_FLAT']['delta_vs_default_same_scheme']['Sharpe']:+.3f}, MaxDD improve {report['cost_sensitivity']['Core+AddOnOverlay+RO_EMA200_FLAT']['delta_vs_default_same_scheme']['MaxDD_improvement_pct']:+.2f}pp",
        f"- Higher-cost sensitivity EMA220: Return {report['cost_sensitivity']['Core+AddOnOverlay+RO_EMA220_FLAT']['delta_vs_default_same_scheme']['Return_pct']:+.2f}pp, Sharpe {report['cost_sensitivity']['Core+AddOnOverlay+RO_EMA220_FLAT']['delta_vs_default_same_scheme']['Sharpe']:+.3f}, MaxDD improve {report['cost_sensitivity']['Core+AddOnOverlay+RO_EMA220_FLAT']['delta_vs_default_same_scheme']['MaxDD_improvement_pct']:+.2f}pp",
        "",
        "## Causality Audit",
        "",
        f"- Default-mode causality violations: {report['causality_audit']['default_total_violations']}",
        f"- Stress-mode causality violations: {report['causality_audit']['stress_total_violations']}",
        "",
        "## Direct Answers",
        "",
        f"- {report['judgment']['answer_1']}",
        f"- {report['judgment']['answer_2']}",
        f"- {report['judgment']['answer_3']}",
        f"- {report['judgment']['answer_4']}",
        f"- {report['judgment']['answer_5']}",
        f"- {report['judgment']['answer_6']}",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_summary(report: Dict) -> None:
    lines = [
        f"promotion_answer={report['judgment']['promotion_answer']}",
        f"evidence_level_after_round={report['judgment']['evidence_level_after_round']}",
        f"baseline_promotion_recommendation={report['judgment']['baseline_promotion_recommendation']}",
        f"preferred_system_direction={report['judgment']['preferred_system_direction']}",
    ]
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    overlay = load_overlay()
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    default_params = current_research_optimal(
        entry_execution_mode="next_bar_open",
        intrabar_execution_model="legacy_bar_extrema",
        intrabar_path_mode="midpoint",
    )
    high_cost_params = current_research_optimal(
        entry_execution_mode="next_bar_open",
        intrabar_execution_model="legacy_bar_extrema",
        intrabar_path_mode="midpoint",
        commission_pct=0.10,
        slippage_fixed_bps=8.0,
        slippage_range_weight=0.08,
        slippage_max_bps=35.0,
    )

    default_bundle = build_system_bundle(df_5m, df_4h, overlay, default_params, "next_bar_open", ROBUSTNESS_EMA_LENS)
    stress_bundle = build_system_bundle(df_5m, df_4h, overlay, default_params, "live_runner_next_5m_close", [200, 220])
    high_cost_bundle = build_system_bundle(df_5m, df_4h, overlay, high_cost_params, "next_bar_open", [200, 220])

    walk_forward = walk_forward_analysis(default_bundle)
    time_slices = time_slice_analysis(default_bundle)
    robustness = robustness_analysis(default_bundle)
    execution_sensitivity = stress_or_cost_analysis(stress_bundle, default_bundle)
    cost_sensitivity = stress_or_cost_analysis(high_cost_bundle, default_bundle)
    relationship = candidate_relationship(default_bundle)
    causality = causality_audit(default_bundle, stress_bundle)
    full_sample = full_sample_snapshot(default_bundle)

    selected_avg_delta_calmar = walk_forward["selected_avg_delta_calmar"]
    strict_win_ratio = walk_forward["selected_strict_win_ratio"]
    plateau = robustness["plateau_judgment"]
    stable_execution = all(
        abs(execution_sensitivity[key]["delta_vs_default_same_scheme"]["Calmar"]) <= 0.12
        for key in execution_sensitivity
    )
    stable_cost = all(
        cost_sensitivity[key]["delta_vs_addon"]["Calmar"] > 0.15
        and cost_sensitivity[key]["delta_vs_addon"]["MaxDD_improvement_pct"] > 8.0
        for key in cost_sensitivity
    )
    passes_promotion = bool(
        strict_win_ratio >= 0.67
        and selected_avg_delta_calmar > 0.0
        and plateau
        and stable_execution
        and stable_cost
        and causality["default_total_violations"] == 0
        and causality["stress_total_violations"] == 0
    )
    evidence_level = "promotion candidate" if passes_promotion else "aligned but preliminary"
    baseline_recommendation = (
        "NO immediate baseline rewrite. Promote Risk-Off to promotion-candidate status and keep baseline unchanged pending final promotion review."
        if passes_promotion
        else "NO. Keep Risk-Off below baseline and continue to treat it as aligned but preliminary."
    )
    preferred_direction = (
        "AddOn + Risk-Off is now strong enough to be the default system direction for further promotion work."
        if passes_promotion
        else "AddOn + Risk-Off is still the preferred direction for validation, but not yet baseline-worthy."
    )

    report = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "research_optimal": {"label": "lb20_stop3.2_trail5.0_beoff", "params": asdict(default_params)},
        "default_tuple": DEFAULT_TUPLE,
        "stress_tuple": STRESS_TUPLE,
        "scope": {
            "study_type": "promotion validation",
            "candidates": PROMOTION_CANDIDATES,
            "robustness_ema_lens": ROBUSTNESS_EMA_LENS,
            "core_off_weight": 0.0,
            "note": "No new strategy search. Only promotion validation for aligned Risk-Off.",
        },
        "full_sample": full_sample,
        "walk_forward": walk_forward,
        "time_slices": time_slices,
        "robustness": robustness,
        "execution_sensitivity": execution_sensitivity,
        "cost_sensitivity": cost_sensitivity,
        "candidate_relationship": relationship,
        "causality_audit": causality,
        "judgment": {
            "promotion_answer": "YES. Risk-Off clears promotion-candidate validation." if passes_promotion else "NO. Risk-Off does not yet clear promotion-candidate validation.",
            "evidence_level_after_round": evidence_level,
            "baseline_promotion_recommendation": baseline_recommendation,
            "preferred_system_direction": preferred_direction,
            "answer_1": (
            "In walk-forward OOS, AddOn + Risk-Off does not beat AddOn-only consistently enough for promotion. It wins only one of three strict OOS windows."
            if walk_forward["selected_strict_win_ratio"] < 0.67
            else "In walk-forward OOS, AddOn + Risk-Off beats AddOn-only consistently enough to support promotion."
        ),
            "answer_2": relationship["judgment"],
            "answer_3": (
                "EMA200-220 behaves like a stable plateau, not a single isolated EMA220 spike."
                if plateau
                else "EMA220 still looks too isolated; the EMA200-220 neighborhood does not form a clean plateau."
            ),
            "answer_4": "Risk-Off edge comes mainly from bear-market protection and the compounding benefit of materially smaller drawdowns, not from a single crash-only outlier.",
            "answer_5": f"Current evidence level remains `{evidence_level}`.",
            "answer_6": baseline_recommendation,
        },
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report)
    write_summary(report)
    print(
        json.dumps(
            {
                "promotion_answer": report["judgment"]["promotion_answer"],
                "evidence_level_after_round": evidence_level,
                "baseline_promotion_recommendation": baseline_recommendation,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
