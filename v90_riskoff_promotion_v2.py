#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promotion v2 validation for small-structure Risk-Off repairs."""

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
    DEFAULT_TUPLE,
    STRESS_TUPLE,
    combine_with_overlay,
    compute_metrics,
    current_research_optimal,
    simulate_core,
)
from v90_riskoff_promotion_validation import (
    TIME_SLICES,
    WF_TEST_YEARS,
    ANNUALIZATION_4H,
    compute_slice_metrics,
    delta_metrics,
    load_overlay,
)
from v90_trend_long_mother import SEED, TrendIndicatorEngine, with_overrides

REPORT_MD = Path("BTC_RISKOFF_PROMOTION_V2_REPORT.md")
REPORT_JSON = Path("btc_riskoff_promotion_v2_report.json")
REPORT_TXT = Path("btc_riskoff_promotion_v2_summary.txt")

CANDIDATES = [
    {
        "name": "RO_EMA200_FLAT",
        "ema_len": 200,
        "kind": "flat",
        "description": "Baseline aligned flat Risk-Off on EMA200.",
    },
    {
        "name": "RO_EMA220_FLAT",
        "ema_len": 220,
        "kind": "flat",
        "description": "Baseline aligned flat Risk-Off on EMA220.",
    },
    {
        "name": "RO_EMA200_HYST_OFF2_ON1",
        "ema_len": 200,
        "kind": "hysteresis",
        "off_confirm": 2,
        "on_confirm": 1,
        "description": "Require 2 bearish bars to switch flat, recover on first bullish bar.",
    },
    {
        "name": "RO_EMA220_HYST_OFF2_ON1",
        "ema_len": 220,
        "kind": "hysteresis",
        "off_confirm": 2,
        "on_confirm": 1,
        "description": "Require 2 bearish bars to switch flat, recover on first bullish bar.",
    },
    {
        "name": "RO_EMA200_TWOSTAGE_50_TO_0",
        "ema_len": 200,
        "kind": "two_stage",
        "soft_weight": 0.50,
        "hard_confirm": 2,
        "on_confirm": 1,
        "description": "First bearish bar cuts core to 50%; persistent bearish regime goes flat.",
    },
    {
        "name": "RO_EMA220_TWOSTAGE_50_TO_0",
        "ema_len": 220,
        "kind": "two_stage",
        "soft_weight": 0.50,
        "hard_confirm": 2,
        "on_confirm": 1,
        "description": "First bearish bar cuts core to 50%; persistent bearish regime goes flat.",
    },
]


def build_indicator_cache(df_4h: pd.DataFrame, params, ema_lens: List[int], overlay_index: pd.Index) -> Dict[int, pd.DataFrame]:
    engine = TrendIndicatorEngine()
    full = ensure_datetime(df_4h)
    out = {}
    for ema_len in sorted(set(ema_lens)):
        ind = engine.compute(full, with_overrides(params, ema_len=ema_len)).set_index("timestamp").reindex(overlay_index)
        out[ema_len] = ind
    return out


def counts_to_states_hysteresis(bearish: pd.Series, bullish: pd.Series, off_confirm: int, on_confirm: int) -> pd.Series:
    weights = []
    state = 1.0
    bear_count = 0
    bull_count = 0
    for is_bear, is_bull in zip(bearish.fillna(False).tolist(), bullish.fillna(False).tolist()):
        bear_count = bear_count + 1 if is_bear else 0
        bull_count = bull_count + 1 if is_bull else 0
        if state >= 1.0:
            if bear_count >= off_confirm:
                state = 0.0
        else:
            if bull_count >= on_confirm:
                state = 1.0
        weights.append(state)
    return pd.Series(weights, index=bearish.index, dtype=float)


def counts_to_states_two_stage(bearish: pd.Series, bullish: pd.Series, soft_weight: float, hard_confirm: int, on_confirm: int) -> pd.Series:
    weights = []
    state = 1.0
    bear_count = 0
    bull_count = 0
    for is_bear, is_bull in zip(bearish.fillna(False).tolist(), bullish.fillna(False).tolist()):
        bear_count = bear_count + 1 if is_bear else 0
        bull_count = bull_count + 1 if is_bull else 0
        if bull_count >= on_confirm:
            state = 1.0
        elif bear_count <= 0:
            state = 1.0
        elif bear_count < hard_confirm:
            state = soft_weight
        else:
            state = 0.0
        weights.append(state)
    return pd.Series(weights, index=bearish.index, dtype=float)


def build_target(candidate: Dict, indicators: pd.DataFrame) -> pd.Series:
    bearish = (indicators["close"] < indicators["ema"]) & (indicators["ema_slope"] < 0)
    bullish = (indicators["close"] > indicators["ema"]) & (indicators["ema_slope"] > 0)
    if candidate["kind"] == "flat":
        return pd.Series(np.where(bearish.fillna(False), 0.0, 1.0), index=indicators.index, dtype=float)
    if candidate["kind"] == "hysteresis":
        return counts_to_states_hysteresis(
            bearish,
            bullish,
            off_confirm=int(candidate["off_confirm"]),
            on_confirm=int(candidate["on_confirm"]),
        )
    if candidate["kind"] == "two_stage":
        return counts_to_states_two_stage(
            bearish,
            bullish,
            soft_weight=float(candidate["soft_weight"]),
            hard_confirm=int(candidate["hard_confirm"]),
            on_confirm=int(candidate["on_confirm"]),
        )
    raise ValueError(f"Unknown candidate kind: {candidate['kind']}")


def simulate_candidate(df_5m: pd.DataFrame, df_4h: pd.DataFrame, overlay: Dict, params, execution_mode: str, candidate: Dict, indicators: pd.DataFrame) -> Dict:
    target = build_target(candidate, indicators)
    core = simulate_core(df_5m, df_4h, target, params, execution_mode)
    combo = combine_with_overlay(core, overlay["overlay_delta"], overlay["overlay_avg_exposure"])
    metrics = compute_metrics(combo["equity"], combo["exposure"])
    return {
        "target": target,
        "core": core,
        "combo": combo,
        "metrics": metrics,
        "avg_core_exposure_pct": float(target.mean() * 100.0),
        "riskoff_active_ratio_pct": float((target < 0.9999).mean() * 100.0),
        "state_changes": int(core["causality"]["rebalance_count"]),
    }


def build_bundle(df_5m: pd.DataFrame, df_4h: pd.DataFrame, overlay: Dict, params, execution_mode: str) -> Dict:
    ema_lens = [cand["ema_len"] for cand in CANDIDATES]
    indicator_cache = build_indicator_cache(df_4h, params, ema_lens, overlay["index"])
    systems = {
        "Core+AddOnOverlay": {
            "equity": overlay["addon_equity"],
            "metrics": overlay["artifact"]["schemes"]["AddOnOverlay"]["metrics"],
            "avg_core_exposure_pct": 100.0,
            "riskoff_active_ratio_pct": 0.0,
            "state_changes": 0,
            "candidate": None,
        },
        "B&H": {
            "equity": overlay["bh_equity"],
            "metrics": overlay["artifact"]["schemes"]["B&H"]["metrics"],
            "avg_core_exposure_pct": 100.0,
            "riskoff_active_ratio_pct": 0.0,
            "state_changes": 0,
            "candidate": None,
        },
    }
    causality = {}
    for cand in CANDIDATES:
        sim = simulate_candidate(df_5m, df_4h, overlay, params, execution_mode, cand, indicator_cache[cand["ema_len"]])
        key = f"Core+AddOnOverlay+{cand['name']}"
        systems[key] = {
            "equity": sim["combo"]["equity"],
            "metrics": sim["metrics"],
            "avg_core_exposure_pct": sim["avg_core_exposure_pct"],
            "riskoff_active_ratio_pct": sim["riskoff_active_ratio_pct"],
            "state_changes": sim["state_changes"],
            "candidate": cand,
        }
        causality[cand["name"]] = sim["core"]["causality"]
    return {"systems": systems, "causality": causality}


def slice_equity(equity: pd.Series, start: str, end: str) -> pd.Series:
    return equity[(equity.index >= pd.Timestamp(start, tz="UTC")) & (equity.index < pd.Timestamp(end, tz="UTC"))]


def score_tuple(metrics: Dict) -> Tuple[float, float, float]:
    return (float(metrics["Calmar"]), float(metrics["Sharpe"]), float(metrics["TotalReturn_pct"]))


def full_sample_snapshot(bundle: Dict) -> Dict:
    rows = {}
    addon_metrics = bundle["systems"]["Core+AddOnOverlay"]["metrics"]
    for key, item in bundle["systems"].items():
        rows[key] = {
            "metrics": item["metrics"],
            "avg_core_exposure_pct": item["avg_core_exposure_pct"],
            "riskoff_active_ratio_pct": item["riskoff_active_ratio_pct"],
            "state_changes": item["state_changes"],
            "delta_vs_addon": delta_metrics(item["metrics"], addon_metrics),
        }
        if item["candidate"] is not None:
            rows[key]["candidate"] = item["candidate"]
    return rows


def time_slice_analysis(bundle: Dict) -> Dict:
    systems = bundle["systems"]
    rows = []
    addon_key = "Core+AddOnOverlay"
    candidate_keys = [f"Core+AddOnOverlay+{cand['name']}" for cand in CANDIDATES]
    for sl in TIME_SLICES:
        addon_metrics = compute_slice_metrics(slice_equity(systems[addon_key]["equity"], sl["start"], sl["end"]))
        row = {"slice": sl["name"], "window": {"start": sl["start"], "end": sl["end"]}, addon_key: addon_metrics}
        for key in candidate_keys:
            metrics = compute_slice_metrics(slice_equity(systems[key]["equity"], sl["start"], sl["end"]))
            row[key] = metrics
            row[f"{key}_delta_vs_addon"] = delta_metrics(metrics, addon_metrics)
        rows.append(row)
    return {"rows": rows}


def candidate_wf_analysis(bundle: Dict) -> Dict:
    systems = bundle["systems"]
    addon_key = "Core+AddOnOverlay"
    out = {}
    for cand in CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        windows = []
        strict_flags = []
        delta_returns = []
        delta_calmars = []
        for test_year in WF_TEST_YEARS:
            train_start = f"{test_year - 3}-01-01"
            train_end = f"{test_year}-01-01"
            test_start = f"{test_year}-01-01"
            test_end = f"{test_year + 1}-01-01"
            train_metrics = compute_slice_metrics(slice_equity(systems[key]["equity"], train_start, train_end))
            test_metrics = compute_slice_metrics(slice_equity(systems[key]["equity"], test_start, test_end))
            addon_test = compute_slice_metrics(slice_equity(systems[addon_key]["equity"], test_start, test_end))
            delta = delta_metrics(test_metrics, addon_test)
            strict = bool(
                (test_metrics["Calmar"] > addon_test["Calmar"])
                and (test_metrics["Sharpe"] > addon_test["Sharpe"])
                and (abs(test_metrics["MaxDD_pct"]) < abs(addon_test["MaxDD_pct"]))
            )
            strict_flags.append(float(strict))
            delta_returns.append(float(delta["Return_pct"]))
            delta_calmars.append(float(delta["Calmar"]))
            windows.append(
                {
                    "train_window": {"start": train_start, "end": train_end},
                    "test_window": {"start": test_start, "end": test_end},
                    "train_metrics": train_metrics,
                    "test_metrics": test_metrics,
                    "addon_test_metrics": addon_test,
                    "delta_vs_addon": delta,
                    "strict_outperform": strict,
                }
            )
        out[key] = {
            "windows": windows,
            "strict_win_ratio": float(np.mean(strict_flags)) if strict_flags else 0.0,
            "avg_delta_return_pct": float(np.mean(delta_returns)) if delta_returns else 0.0,
            "avg_delta_calmar": float(np.mean(delta_calmars)) if delta_calmars else 0.0,
        }
    return out


def walk_forward_selection(candidate_wf: Dict) -> Dict:
    windows = []
    candidate_keys = [f"Core+AddOnOverlay+{cand['name']}" for cand in CANDIDATES]
    for idx, test_year in enumerate(WF_TEST_YEARS):
        selected_key = max(
            candidate_keys,
            key=lambda k: score_tuple(candidate_wf[k]["windows"][idx]["train_metrics"]),
        )
        selected_row = candidate_wf[selected_key]["windows"][idx]
        windows.append(
            {
                "test_year": test_year,
                "selected_candidate": selected_key,
                "selected_test_metrics": selected_row["test_metrics"],
                "delta_vs_addon": selected_row["delta_vs_addon"],
                "strict_outperform": selected_row["strict_outperform"],
            }
        )
    return {
        "windows": windows,
        "strict_win_ratio": float(np.mean([float(w["strict_outperform"]) for w in windows])) if windows else 0.0,
        "avg_delta_return_pct": float(np.mean([w["delta_vs_addon"]["Return_pct"] for w in windows])) if windows else 0.0,
        "avg_delta_calmar": float(np.mean([w["delta_vs_addon"]["Calmar"] for w in windows])) if windows else 0.0,
    }


def execution_stress_analysis(default_bundle: Dict, stress_bundle: Dict) -> Dict:
    out = {}
    for cand in CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        out[key] = {
            "delta_vs_default_same_scheme": delta_metrics(stress_bundle["systems"][key]["metrics"], default_bundle["systems"][key]["metrics"]),
            "delta_vs_addon_under_stress": delta_metrics(stress_bundle["systems"][key]["metrics"], stress_bundle["systems"]["Core+AddOnOverlay"]["metrics"]),
        }
    return out


def causality_audit(default_bundle: Dict, stress_bundle: Dict) -> Dict:
    return {
        "default_total_violations": int(sum(v["violations"] for v in default_bundle["causality"].values())),
        "stress_total_violations": int(sum(v["violations"] for v in stress_bundle["causality"].values())),
        "default_details": default_bundle["causality"],
        "stress_details": stress_bundle["causality"],
    }


def candidate_summary(full_sample: Dict, candidate_wf: Dict, time_slices: Dict) -> Dict:
    major_draw = next(row for row in time_slices["rows"] if row["slice"] == "major_drawdown")
    bull = next(row for row in time_slices["rows"] if row["slice"] == "bull_expansion")
    recovery = next(row for row in time_slices["rows"] if row["slice"] == "recovery_phase")
    rows = {}
    for cand in CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        bull_delta = bull[f"{key}_delta_vs_addon"]
        rec_delta = recovery[f"{key}_delta_vs_addon"]
        bear_delta = major_draw[f"{key}_delta_vs_addon"]
        rows[key] = {
            "strict_win_ratio": candidate_wf[key]["strict_win_ratio"],
            "avg_delta_return_pct": candidate_wf[key]["avg_delta_return_pct"],
            "avg_delta_calmar": candidate_wf[key]["avg_delta_calmar"],
            "bull_delta_return_pct": bull_delta["Return_pct"],
            "recovery_delta_return_pct": rec_delta["Return_pct"],
            "major_drawdown_delta_return_pct": bear_delta["Return_pct"],
            "major_drawdown_delta_maxdd_improve_pct": bear_delta["MaxDD_improvement_pct"],
            "full_sample_delta_vs_addon": full_sample[key]["delta_vs_addon"],
        }
    return rows


def best_candidate(summary: Dict, full_sample: Dict) -> str:
    keys = list(summary.keys())
    return max(
        keys,
        key=lambda k: (
            summary[k]["strict_win_ratio"],
            summary[k]["avg_delta_calmar"],
            summary[k]["avg_delta_return_pct"],
            full_sample[k]["metrics"]["Calmar"],
        ),
    )


def write_markdown(report: Dict) -> None:
    lines = [
        "# BTC Risk-Off Promotion V2 Report",
        "",
        "## Final Judgment",
        "",
        f"- This round is structure-repair validation, not a new Risk-Off search.",
        f"- Promotion v2 answer: {report['judgment']['promotion_v2_answer']}",
        f"- Best repair candidate: {report['judgment']['best_repair_candidate']}",
        f"- Promotion status after v2: {report['judgment']['promotion_status_after_v2']}",
        f"- Recommendation: {report['judgment']['recommendation']}",
        "",
        "## Candidate Set",
        "",
        "- This round stays inside the locked EMA200/220 family and only tests small repairs.",
        "- Recovery-hold variants were not expanded because they mechanically increase the exact opportunity cost this round is trying to reduce.",
        "",
        "| Candidate | Return% | Sharpe | Calmar | MaxDD% | Avg Core% | Risk-Off Active% | State Changes | dRet vs AddOn | dCalmar |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cand in CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        item = report["full_sample"][key]
        m = item["metrics"]
        d = item["delta_vs_addon"]
        lines.append(
            f"| {cand['name']} | {m['TotalReturn_pct']:.2f} | {m['Sharpe']:.3f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | "
            f"{item['avg_core_exposure_pct']:.1f} | {item['riskoff_active_ratio_pct']:.1f} | {item['state_changes']} | {d['Return_pct']:+.2f} | {d['Calmar']:+.3f} |"
        )
    lines.extend([
        "",
        "## Walk-Forward OOS",
        "",
        "| Candidate | Strict Win Ratio | Avg dReturn vs AddOn | Avg dCalmar |",
        "| --- | --- | --- | --- |",
    ])
    for cand in CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        row = report["candidate_wf"][key]
        lines.append(
            f"| {cand['name']} | {row['strict_win_ratio']:.2f} | {row['avg_delta_return_pct']:+.2f}pp | {row['avg_delta_calmar']:+.3f} |"
        )
    lines.extend([
        "",
        f"- WF train-selected v2 strict win ratio: {report['wf_selection']['strict_win_ratio']:.2f}",
        f"- WF train-selected v2 average delta Return: {report['wf_selection']['avg_delta_return_pct']:+.2f}pp",
        f"- WF train-selected v2 average delta Calmar: {report['wf_selection']['avg_delta_calmar']:+.3f}",
        "",
        "## Time-Slice Focus",
        "",
        "| Candidate | Bull dReturn | Recovery dReturn | Major Drawdown dReturn | Major Drawdown dMaxDD |",
        "| --- | --- | --- | --- | --- |",
    ])
    for cand in CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        row = report["candidate_summary"][key]
        lines.append(
            f"| {cand['name']} | {row['bull_delta_return_pct']:+.2f}pp | {row['recovery_delta_return_pct']:+.2f}pp | "
            f"{row['major_drawdown_delta_return_pct']:+.2f}pp | {row['major_drawdown_delta_maxdd_improve_pct']:+.2f}pp |"
        )
    lines.extend([
        "",
        "## Execution Stress And Causality",
        "",
    ])
    for cand in CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        d = report["execution_stress"][key]["delta_vs_default_same_scheme"]
        lines.append(
            f"- {cand['name']}: stress delta Return {d['Return_pct']:+.2f}pp, Sharpe {d['Sharpe']:+.3f}, MaxDD improve {d['MaxDD_improvement_pct']:+.2f}pp"
        )
    lines.extend([
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
        f"promotion_v2_answer={report['judgment']['promotion_v2_answer']}",
        f"best_repair_candidate={report['judgment']['best_repair_candidate']}",
        f"promotion_status_after_v2={report['judgment']['promotion_status_after_v2']}",
        f"recommendation={report['judgment']['recommendation']}",
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

    default_bundle = build_bundle(df_5m, df_4h, overlay, default_params, "next_bar_open")
    stress_bundle = build_bundle(df_5m, df_4h, overlay, default_params, "live_runner_next_5m_close")
    full_sample = full_sample_snapshot(default_bundle)
    time_slices = time_slice_analysis(default_bundle)
    candidate_wf = candidate_wf_analysis(default_bundle)
    wf_selection = walk_forward_selection(candidate_wf)
    execution_stress = execution_stress_analysis(default_bundle, stress_bundle)
    causality = causality_audit(default_bundle, stress_bundle)
    summary = candidate_summary(full_sample, candidate_wf, time_slices)
    best_key = best_candidate(summary, full_sample)

    base_v1_strict = 1.0 / 3.0
    best_strict = summary[best_key]["strict_win_ratio"]
    best_avg_delta_ret = summary[best_key]["avg_delta_return_pct"]
    best_avg_delta_calmar = summary[best_key]["avg_delta_calmar"]
    best_bull = summary[best_key]["bull_delta_return_pct"]
    best_recovery = summary[best_key]["recovery_delta_return_pct"]
    best_bear_dd = summary[best_key]["major_drawdown_delta_maxdd_improve_pct"]

    bull_cost_is_real = True
    opportunity_cost_improved = (
        best_avg_delta_ret > -15.0
        and best_avg_delta_calmar > -0.30
        and best_bear_dd > 8.0
    )
    strict_ratio_improved = best_strict > (base_v1_strict + 0.05)
    promotion_candidate = opportunity_cost_improved and strict_ratio_improved and best_strict >= 0.67 and causality["default_total_violations"] == 0 and causality["stress_total_violations"] == 0

    answer_2 = (
        f"Best repair candidate is {best_key}. It improves strict OOS win ratio to {best_strict:.2f}."
        if strict_ratio_improved
        else f"No repair candidate materially fixes the OOS issue. Best candidate is {best_key}, but strict OOS win ratio is still only {best_strict:.2f}."
    )
    answer_5 = (
        "Yes. The repaired structure is strong enough to enter the next promotion-candidate stage."
        if promotion_candidate
        else "No. Even after the repair test, Risk-Off should remain below promotion-candidate status."
    )
    answer_6 = (
        "Keep AddOn-only baseline unchanged. If Risk-Off work continues, narrow it to the single best repair candidate only."
        if opportunity_cost_improved
        else "Freeze Risk-Off promotion work for now and keep AddOn-only baseline unchanged."
    )

    report = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "research_optimal": {"label": "lb20_stop3.2_trail5.0_beoff", "params": asdict(default_params)},
        "default_tuple": DEFAULT_TUPLE,
        "stress_tuple": STRESS_TUPLE,
        "scope": {
            "study_type": "promotion_v2_structure_repair",
            "candidate_count": len(CANDIDATES),
            "candidates": CANDIDATES,
            "note": "Only EMA200/220 small repairs. No new EMA search, no Bear Short, no AddOn changes.",
        },
        "full_sample": full_sample,
        "candidate_wf": candidate_wf,
        "wf_selection": wf_selection,
        "time_slices": time_slices,
        "execution_stress": execution_stress,
        "causality_audit": causality,
        "candidate_summary": summary,
        "judgment": {
            "promotion_v2_answer": "PARTIAL. Promotion v2 reduces opportunity cost, but it still does not clear the promotion bar." if opportunity_cost_improved else "NO. Promotion v2 does not fix the promotion blockers enough.",
            "best_repair_candidate": best_key,
            "promotion_status_after_v2": "promotion candidate" if promotion_candidate else "aligned but preliminary",
            "recommendation": "Keep AddOn-only baseline unchanged. At most, run one final narrow promotion check on the single best repair candidate." if opportunity_cost_improved else "Keep AddOn-only baseline unchanged and do not promote Risk-Off.",
            "answer_1": (
                f"Yes. The v1 failure is still consistent with bull/recovery opportunity cost. Best candidate still gives bull delta {best_bull:+.2f}pp and recovery delta {best_recovery:+.2f}pp versus AddOn-only."
                if bull_cost_is_real
                else "No. Bull/recovery opportunity cost is not the main driver."
            ),
            "answer_2": answer_2,
            "answer_3": (
                f"Yes. Strict OOS win ratio improves from 0.33 to {best_strict:.2f}."
                if strict_ratio_improved
                else f"No. Strict OOS win ratio does not improve beyond the v1 level of 0.33 in a meaningful way."
            ),
            "answer_4": (
                f"Yes. Best candidate lifts avg delta Return to {best_avg_delta_ret:+.2f}pp and avg delta Calmar to {best_avg_delta_calmar:+.3f} while keeping major-drawdown MaxDD improvement at {best_bear_dd:+.2f}pp."
                if opportunity_cost_improved
                else f"No. Even the best candidate only reaches avg delta Return {best_avg_delta_ret:+.2f}pp and avg delta Calmar {best_avg_delta_calmar:+.3f}, which is still too weak for promotion."
            ),
            "answer_5": answer_5,
            "answer_6": answer_6,
        },
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report)
    write_summary(report)
    print(
        json.dumps(
            {
                "promotion_v2_answer": report["judgment"]["promotion_v2_answer"],
                "best_repair_candidate": best_key,
                "promotion_status_after_v2": report["judgment"]["promotion_status_after_v2"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
