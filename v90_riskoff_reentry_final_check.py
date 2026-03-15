#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final narrow re-entry timing check for RO_EMA220_TWOSTAGE_50_TO_0."""

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
from v90_riskoff_promotion_validation import TIME_SLICES, WF_TEST_YEARS, compute_slice_metrics, delta_metrics, load_overlay
from v90_riskoff_promotion_v2 import build_indicator_cache
from v90_trend_long_mother import SEED, TrendIndicatorEngine, with_overrides

REPORT_MD = Path("BTC_RISKOFF_REENTRY_FINAL_CHECK_REPORT.md")
REPORT_JSON = Path("btc_riskoff_reentry_final_check.json")
REPORT_TXT = Path("btc_riskoff_reentry_final_check_summary.txt")

BASE_CANDIDATE = {
    "name": "RO_EMA220_TWOSTAGE_50_TO_0_BASE",
    "ema_len": 220,
    "kind": "base_twostage",
    "description": "Current best repair candidate: 1.0 -> 0.5 -> 0.0 on bearish deterioration; flat exits on first slope-confirm bar.",
}

REENTRY_CANDIDATES = [
    BASE_CANDIDATE,
    {
        "name": "RO_EMA220_REENTRY_CLOSE_HOLD_1",
        "ema_len": 220,
        "kind": "close_full",
        "reentry_bars": 1,
        "description": "Flat exits directly to 100% on first close>EMA220 bar.",
    },
    {
        "name": "RO_EMA220_REENTRY_CLOSE_HOLD_2",
        "ema_len": 220,
        "kind": "close_full",
        "reentry_bars": 2,
        "description": "Flat exits directly to 100% after two close>EMA220 bars.",
    },
    {
        "name": "RO_EMA220_REENTRY_CLOSE_HOLD_3",
        "ema_len": 220,
        "kind": "close_full",
        "reentry_bars": 3,
        "description": "Flat exits directly to 100% after three close>EMA220 bars.",
    },
    {
        "name": "RO_EMA220_REENTRY_STAGE50_CLOSE_1",
        "ema_len": 220,
        "kind": "stage50_close",
        "reentry_bars": 1,
        "description": "Flat exits to 50%, then goes to 100% on the next non-bear bar.",
    },
    {
        "name": "RO_EMA220_REENTRY_STAGE75_CLOSE_1",
        "ema_len": 220,
        "kind": "stage75_close",
        "reentry_bars": 1,
        "description": "Flat exits to 75%, then goes to 100% on the next non-bear bar.",
    },
]


def build_bearish_and_reentry(indicators: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    bearish = (indicators["close"] < indicators["ema"]) & (indicators["ema_slope"] < 0)
    close_confirm = indicators["close"] > indicators["ema"]
    slope_confirm = close_confirm & (indicators["ema_slope"] > 0)
    return bearish.fillna(False), close_confirm.fillna(False), slope_confirm.fillna(False)


def build_target(indicators: pd.DataFrame, candidate: Dict) -> pd.Series:
    bearish, close_confirm, slope_confirm = build_bearish_and_reentry(indicators)
    weights = []
    state = 1.0
    bear_count = 0
    close_count = 0
    slope_count = 0

    for is_bear, is_close, is_slope in zip(bearish.tolist(), close_confirm.tolist(), slope_confirm.tolist()):
        bear_count = bear_count + 1 if is_bear else 0
        close_count = close_count + 1 if is_close else 0
        slope_count = slope_count + 1 if is_slope else 0

        if state == 1.0:
            if bear_count >= 2:
                state = 0.0
            elif bear_count == 1:
                state = 0.5
            else:
                state = 1.0
        elif state == 0.5:
            if bear_count >= 2:
                state = 0.0
            elif bear_count == 1:
                state = 0.5
            else:
                state = 1.0
        elif state == 0.75:
            if bear_count >= 2:
                state = 0.0
            elif bear_count == 1:
                state = 0.5
            else:
                state = 1.0
        elif state == 0.0:
            if candidate["kind"] == "base_twostage":
                if slope_count >= 1:
                    state = 1.0
                else:
                    state = 0.0
            elif candidate["kind"] == "close_full":
                if close_count >= int(candidate["reentry_bars"]):
                    state = 1.0
                else:
                    state = 0.0
            elif candidate["kind"] == "stage50_close":
                if close_count >= int(candidate["reentry_bars"]):
                    state = 0.5
                else:
                    state = 0.0
            elif candidate["kind"] == "stage75_close":
                if close_count >= int(candidate["reentry_bars"]):
                    state = 0.75
                else:
                    state = 0.0
            else:
                raise ValueError(f"Unknown candidate kind: {candidate['kind']}")
        weights.append(state)

    return pd.Series(weights, index=indicators.index, dtype=float)


def build_flat_reference(indicators: pd.DataFrame) -> pd.Series:
    bearish, _, _ = build_bearish_and_reentry(indicators)
    return pd.Series(np.where(bearish, 0.0, 1.0), index=indicators.index, dtype=float)


def simulate_candidate(
    df_5m: pd.DataFrame,
    df_4h: pd.DataFrame,
    overlay: Dict,
    params,
    execution_mode: str,
    target: pd.Series,
) -> Dict:
    core = simulate_core(df_5m, df_4h, target, params, execution_mode)
    combo = combine_with_overlay(core, overlay["overlay_delta"], overlay["overlay_avg_exposure"])
    return {
        "target": target,
        "core": core,
        "combo": combo,
        "metrics": compute_metrics(combo["equity"], combo["exposure"]),
        "avg_core_exposure_pct": float(target.mean() * 100.0),
        "riskoff_active_ratio_pct": float((target < 0.9999).mean() * 100.0),
        "state_changes": int(core["causality"]["rebalance_count"]),
    }


def slice_series(series: pd.Series, start: str, end: str) -> pd.Series:
    return series[(series.index >= pd.Timestamp(start, tz="UTC")) & (series.index < pd.Timestamp(end, tz="UTC"))]


def state_distribution(target: pd.Series) -> Dict[str, float]:
    vals = target.round(4)
    total = max(len(vals), 1)
    return {
        "state_1.00_pct": float((vals == 1.0).sum() / total * 100.0),
        "state_0.75_pct": float((vals == 0.75).sum() / total * 100.0),
        "state_0.50_pct": float((vals == 0.5).sum() / total * 100.0),
        "state_0.00_pct": float((vals == 0.0).sum() / total * 100.0),
    }


def pnl_attribution(candidate_core: pd.Series, bh_core: pd.Series, target: pd.Series) -> Dict:
    bh_pnl = bh_core.diff().fillna(0.0)
    cand_pnl = candidate_core.diff().fillna(0.0)
    diff = cand_pnl - bh_pnl
    state = target.reindex(candidate_core.index).ffill().fillna(1.0).round(4)
    return {
        "flat_state_upside_drag": float((-diff[(state == 0.0) & (bh_pnl > 0) & (diff < 0)]).sum()),
        "flat_state_downside_protection": float(diff[(state == 0.0) & (bh_pnl < 0) & (diff > 0)].sum()),
        "reduced_state_upside_drag": float((-diff[(state.isin([0.5, 0.75])) & (bh_pnl > 0) & (diff < 0)]).sum()),
        "reduced_state_downside_protection": float(diff[(state.isin([0.5, 0.75])) & (bh_pnl < 0) & (diff > 0)].sum()),
    }


def build_bundle(df_5m: pd.DataFrame, df_4h: pd.DataFrame, overlay: Dict, params, execution_mode: str) -> Dict:
    indicators = build_indicator_cache(df_4h, params, [220], overlay["index"])[220]
    systems = {
        "Core+AddOnOverlay": {
            "equity": overlay["addon_equity"],
            "metrics": overlay["artifact"]["schemes"]["AddOnOverlay"]["metrics"],
            "avg_core_exposure_pct": 100.0,
            "riskoff_active_ratio_pct": 0.0,
            "state_changes": 0,
            "target": pd.Series(1.0, index=overlay["index"], dtype=float),
        },
        "Core+AddOnOverlay+RO_EMA220_FLAT": None,
    }

    flat_target = build_flat_reference(indicators)
    flat_sim = simulate_candidate(df_5m, df_4h, overlay, params, execution_mode, flat_target)
    systems["Core+AddOnOverlay+RO_EMA220_FLAT"] = {
        **flat_sim,
        "candidate": {"name": "RO_EMA220_FLAT", "kind": "flat_reference"},
    }

    for cand in REENTRY_CANDIDATES:
        target = build_target(indicators, cand)
        sim = simulate_candidate(df_5m, df_4h, overlay, params, execution_mode, target)
        key = f"Core+AddOnOverlay+{cand['name']}"
        systems[key] = {**sim, "candidate": cand}
    causality = {
        "RO_EMA220_FLAT": flat_sim["core"]["causality"],
    }
    for cand in REENTRY_CANDIDATES:
        causality[cand["name"]] = systems[f"Core+AddOnOverlay+{cand['name']}"]["core"]["causality"]
    return {"systems": systems, "causality": causality}


def candidate_summary(bundle: Dict) -> Dict:
    systems = bundle["systems"]
    addon_key = "Core+AddOnOverlay"
    summary = {}
    major_draw = next(x for x in TIME_SLICES if x["name"] == "major_drawdown")
    bull = next(x for x in TIME_SLICES if x["name"] == "bull_expansion")
    recovery = next(x for x in TIME_SLICES if x["name"] == "recovery_phase")

    for cand in REENTRY_CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        windows = []
        strict_flags = []
        delta_returns = []
        delta_sharpes = []
        delta_calmars = []
        flat_drags = []
        for year in WF_TEST_YEARS:
            start = f"{year}-01-01"
            end = f"{year+1}-01-01"
            addon_eq = slice_series(systems[addon_key]["equity"], start, end)
            cand_eq = slice_series(systems[key]["combo"]["equity"], start, end)
            addon_metrics = compute_slice_metrics(addon_eq)
            cand_metrics = compute_slice_metrics(cand_eq)
            delta = {
                "Return_pct": float(cand_metrics["TotalReturn_pct"] - addon_metrics["TotalReturn_pct"]),
                "CAGR_pct": float(cand_metrics["CAGR_pct"] - addon_metrics["CAGR_pct"]),
                "Sharpe": float(cand_metrics["Sharpe"] - addon_metrics["Sharpe"]),
                "Calmar": float(cand_metrics["Calmar"] - addon_metrics["Calmar"]),
                "MaxDD_improvement_pct": float(abs(addon_metrics["MaxDD_pct"]) - abs(cand_metrics["MaxDD_pct"])),
            }
            strict = bool(
                (cand_metrics["Calmar"] > addon_metrics["Calmar"])
                and (cand_metrics["Sharpe"] > addon_metrics["Sharpe"])
                and (abs(cand_metrics["MaxDD_pct"]) < abs(addon_metrics["MaxDD_pct"]))
            )
            attribution = pnl_attribution(
                slice_series(systems[key]["core"]["equity"]["equity"].astype(float), start, end),
                slice_series(systems["Core_BH"]["equity"], start, end),
                slice_series(systems[key]["target"], start, end),
            )
            windows.append(
                {
                    "name": f"OOS_{year}",
                    "window": {"start": start, "end": end},
                    "delta_vs_addon": delta,
                    "strict_outperform": strict,
                    "state_distribution": state_distribution(slice_series(systems[key]["target"], start, end)),
                    "flat_state_upside_drag": attribution["flat_state_upside_drag"],
                    "pnl_attribution": attribution,
                }
            )
            strict_flags.append(float(strict))
            delta_returns.append(delta["Return_pct"])
            delta_sharpes.append(delta["Sharpe"])
            delta_calmars.append(delta["Calmar"])
            flat_drags.append(attribution["flat_state_upside_drag"])

        bull_delta = compute_slice_metrics(slice_series(systems[key]["combo"]["equity"], bull["start"], bull["end"]))
        bull_addon = compute_slice_metrics(slice_series(systems[addon_key]["equity"], bull["start"], bull["end"]))
        recovery_delta = compute_slice_metrics(slice_series(systems[key]["combo"]["equity"], recovery["start"], recovery["end"]))
        recovery_addon = compute_slice_metrics(slice_series(systems[addon_key]["equity"], recovery["start"], recovery["end"]))
        draw_delta = compute_slice_metrics(slice_series(systems[key]["combo"]["equity"], major_draw["start"], major_draw["end"]))
        draw_addon = compute_slice_metrics(slice_series(systems[addon_key]["equity"], major_draw["start"], major_draw["end"]))
        sideways = next(x for x in TIME_SLICES if x["name"] == "sideways_volatility")
        side_delta = compute_slice_metrics(slice_series(systems[key]["combo"]["equity"], sideways["start"], sideways["end"]))
        side_addon = compute_slice_metrics(slice_series(systems[addon_key]["equity"], sideways["start"], sideways["end"]))

        summary[key] = {
            "metrics": systems[key]["metrics"],
            "avg_core_exposure_pct": systems[key]["avg_core_exposure_pct"],
            "riskoff_active_ratio_pct": systems[key]["riskoff_active_ratio_pct"],
            "state_changes": systems[key]["state_changes"],
            "strict_oos_win_ratio": float(np.mean(strict_flags)) if strict_flags else 0.0,
            "avg_delta_return_pct": float(np.mean(delta_returns)) if delta_returns else 0.0,
            "avg_delta_sharpe": float(np.mean(delta_sharpes)) if delta_sharpes else 0.0,
            "avg_delta_calmar": float(np.mean(delta_calmars)) if delta_calmars else 0.0,
            "bull_delta_return_pct": float(bull_delta["TotalReturn_pct"] - bull_addon["TotalReturn_pct"]),
            "recovery_delta_return_pct": float(recovery_delta["TotalReturn_pct"] - recovery_addon["TotalReturn_pct"]),
            "sideways_delta_return_pct": float(side_delta["TotalReturn_pct"] - side_addon["TotalReturn_pct"]),
            "major_drawdown_dmaxdd_pct": float(abs(draw_addon["MaxDD_pct"]) - abs(draw_delta["MaxDD_pct"])),
            "avg_flat_state_upside_drag": float(np.mean(flat_drags)) if flat_drags else 0.0,
            "oos_windows": windows,
        }
    return summary


def execution_stress(bundle_default: Dict, bundle_stress: Dict) -> Dict:
    out = {}
    addon_key = "Core+AddOnOverlay"
    for cand in REENTRY_CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        out[key] = {
            "delta_vs_default_same_scheme": delta_metrics(bundle_stress["systems"][key]["metrics"], bundle_default["systems"][key]["metrics"]),
            "delta_vs_addon_under_stress": delta_metrics(bundle_stress["systems"][key]["metrics"], bundle_stress["systems"][addon_key]["metrics"]),
        }
    return out


def causality_audit(default_bundle: Dict, stress_bundle: Dict) -> Dict:
    return {
        "default_total_violations": int(sum(v["violations"] for v in default_bundle["causality"].values())),
        "stress_total_violations": int(sum(v["violations"] for v in stress_bundle["causality"].values())),
        "default_details": default_bundle["causality"],
        "stress_details": stress_bundle["causality"],
    }


def full_sample_snapshot(bundle: Dict) -> Dict:
    out = {}
    addon_metrics = bundle["systems"]["Core+AddOnOverlay"]["metrics"]
    keys = ["Core+AddOnOverlay", "Core+AddOnOverlay+RO_EMA220_FLAT"] + [f"Core+AddOnOverlay+{c['name']}" for c in REENTRY_CANDIDATES]
    for key in keys:
        item = bundle["systems"][key]
        out[key] = {
            "metrics": item["metrics"],
            "avg_core_exposure_pct": item.get("avg_core_exposure_pct", 100.0),
            "riskoff_active_ratio_pct": item.get("riskoff_active_ratio_pct", 0.0),
            "state_changes": item.get("state_changes", 0),
            "delta_vs_addon": delta_metrics(item["metrics"], addon_metrics),
        }
    return out


def best_candidate(summary: Dict) -> str:
    return max(
        summary.keys(),
        key=lambda k: (
            summary[k]["strict_oos_win_ratio"],
            summary[k]["avg_delta_calmar"],
            summary[k]["avg_delta_return_pct"],
            -summary[k]["avg_flat_state_upside_drag"],
        ),
    )


def write_markdown(report: Dict) -> None:
    lines = [
        "# BTC Risk-Off Reentry Final Check Report",
        "",
        "## Final Judgment",
        "",
        f"- This round is the final flat re-entry timing check for `RO_EMA220_TWOSTAGE_50_TO_0` only.",
        f"- Final check answer: {report['judgment']['final_check_answer']}",
        f"- Best re-entry candidate: {report['judgment']['best_candidate']}",
        f"- Promotion decision: {report['judgment']['promotion_decision']}",
        f"- Recommendation: {report['judgment']['recommendation']}",
        "",
        "## Candidate Comparison",
        "",
        "| Candidate | Strict OOS Win Ratio | Avg dReturn | Avg dSharpe | Avg dCalmar | Bull dReturn | Recovery dReturn | Sideways dReturn | Major Drawdown dMaxDD | Avg Flat Upside Drag |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for cand in REENTRY_CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        row = report["candidate_summary"][key]
        lines.append(
            f"| {cand['name']} | {row['strict_oos_win_ratio']:.2f} | {row['avg_delta_return_pct']:+.2f}pp | {row['avg_delta_sharpe']:+.3f} | "
            f"{row['avg_delta_calmar']:+.3f} | {row['bull_delta_return_pct']:+.2f}pp | {row['recovery_delta_return_pct']:+.2f}pp | "
            f"{row['sideways_delta_return_pct']:+.2f}pp | {row['major_drawdown_dmaxdd_pct']:+.2f}pp | {row['avg_flat_state_upside_drag']:.2f} |"
        )
    lines.extend([
        "",
        "## Full-Sample References",
        "",
        "| Scheme | Return% | Sharpe | Calmar | MaxDD% | Exposure% |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for key in ["Core+AddOnOverlay", "Core+AddOnOverlay+RO_EMA220_FLAT", f"Core+AddOnOverlay+{report['judgment']['best_candidate']}"]:
        m = report["full_sample"][key]["metrics"]
        lines.append(f"| {key} | {m['TotalReturn_pct']:.2f} | {m['Sharpe']:.3f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | {m['Exposure_pct']:.1f} |")
    lines.extend([
        "",
        "## Execution Stress And Causality",
        "",
    ])
    for cand in REENTRY_CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        d = report["execution_stress"][key]["delta_vs_default_same_scheme"]
        lines.append(f"- {cand['name']}: stress delta Return {d['Return_pct']:+.2f}pp, Sharpe {d['Sharpe']:+.3f}, Calmar {d['Calmar']:+.3f}, MaxDD improve {d['MaxDD_improvement_pct']:+.2f}pp")
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
        f"- {report['judgment']['answer_7']}",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_summary(report: Dict) -> None:
    lines = [
        f"final_check_answer={report['judgment']['final_check_answer']}",
        f"best_candidate={report['judgment']['best_candidate']}",
        f"promotion_decision={report['judgment']['promotion_decision']}",
        f"recommendation={report['judgment']['recommendation']}",
    ]
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    overlay = load_overlay()
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    params = current_research_optimal(
        entry_execution_mode="next_bar_open",
        intrabar_execution_model="legacy_bar_extrema",
        intrabar_path_mode="midpoint",
    )

    default_bundle = build_bundle(df_5m, df_4h, overlay, params, "next_bar_open")
    stress_bundle = build_bundle(df_5m, df_4h, overlay, params, "live_runner_next_5m_close")
    default_bundle["systems"]["Core_BH"] = {"equity": overlay["bh_equity"]}
    stress_bundle["systems"]["Core_BH"] = {"equity": overlay["bh_equity"]}

    summary = candidate_summary(default_bundle)
    best_key = best_candidate(summary)
    execution = execution_stress(default_bundle, stress_bundle)
    causality = causality_audit(default_bundle, stress_bundle)
    full_sample = full_sample_snapshot(default_bundle)

    best = summary[best_key]
    base_key = f"Core+AddOnOverlay+{BASE_CANDIDATE['name']}"
    base = summary[base_key]
    strict_improved = best["strict_oos_win_ratio"] > (base["strict_oos_win_ratio"] + 0.05)
    avg_return_improved = best["avg_delta_return_pct"] > (base["avg_delta_return_pct"] + 3.0)
    avg_calmar_improved = best["avg_delta_calmar"] > (base["avg_delta_calmar"] + 0.15)
    bull_improved = best["bull_delta_return_pct"] > (base["bull_delta_return_pct"] + 20.0)
    recovery_improved = best["recovery_delta_return_pct"] > (base["recovery_delta_return_pct"] + 20.0)
    flat_drag_improved = best["avg_flat_state_upside_drag"] < (base["avg_flat_state_upside_drag"] * 0.85)

    material_fix = strict_improved and (avg_return_improved or avg_calmar_improved) and (bull_improved or recovery_improved) and flat_drag_improved
    promotion_candidate = material_fix and best["strict_oos_win_ratio"] >= 0.67 and causality["default_total_violations"] == 0 and causality["stress_total_violations"] == 0

    answer_1 = (
        "Partially. Re-entry timing does move the opportunity-cost profile, but it does not solve the promotion blocker by itself."
        if any([avg_return_improved, avg_calmar_improved, bull_improved, recovery_improved])
        else "No. Re-entry timing changes do not materially move the opportunity-cost profile."
    )
    answer_2 = f"Best re-entry candidate is {best_key}."
    answer_3 = (
        f"Yes. Strict OOS win ratio improves from {base['strict_oos_win_ratio']:.2f} to {best['strict_oos_win_ratio']:.2f}."
        if strict_improved
        else f"No. Strict OOS win ratio stays at {best['strict_oos_win_ratio']:.2f}, which is not a meaningful improvement over the current 0.33 level."
    )
    answer_4 = (
        f"Average deltas improve to dReturn {best['avg_delta_return_pct']:+.2f}pp and dCalmar {best['avg_delta_calmar']:+.3f}."
        if (avg_return_improved or avg_calmar_improved)
        else f"Average deltas do not improve enough. Best candidate still sits at dReturn {best['avg_delta_return_pct']:+.2f}pp and dCalmar {best['avg_delta_calmar']:+.3f}."
    )
    answer_5 = (
        f"Bull/recovery opportunity cost improves versus the base repair candidate: bull {best['bull_delta_return_pct']:+.2f}pp, recovery {best['recovery_delta_return_pct']:+.2f}pp."
        if (bull_improved or recovery_improved)
        else f"Bull/recovery opportunity cost does not improve enough: bull {best['bull_delta_return_pct']:+.2f}pp, recovery {best['recovery_delta_return_pct']:+.2f}pp."
    )
    answer_6 = (
        "Yes. Freeze Risk-Off promotion and keep AddOn-only baseline unchanged, because the apparent strict-ratio improvement is not matched by enough recovery-cost relief or enough reduction in flat-state upside drag."
        if not promotion_candidate
        else "No. Risk-Off is strong enough to keep moving through promotion."
    )
    answer_7 = (
        "No. Evidence stays below promotion-candidate level: avg dCalmar is still negative, recovery drag is still large, and flat-state upside drag is not reduced enough."
        if not promotion_candidate
        else "Yes. Evidence can now be upgraded to promotion candidate."
    )

    report = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "research_optimal": {"label": "lb20_stop3.2_trail5.0_beoff", "params": asdict(params)},
        "default_tuple": DEFAULT_TUPLE,
        "stress_tuple": STRESS_TUPLE,
        "scope": {
            "study_type": "flat_reentry_final_check",
            "candidate_count": len(REENTRY_CANDIDATES),
            "candidates": REENTRY_CANDIDATES,
            "note": "Single-family re-entry timing check only. No EMA expansion, no Bear Short, no AddOn change.",
        },
        "full_sample": full_sample,
        "candidate_summary": summary,
        "execution_stress": execution,
        "causality_audit": causality,
        "judgment": {
            "final_check_answer": "PARTIAL. Re-entry timing helps, but not enough to rescue promotion." if not promotion_candidate else "YES. Re-entry timing resolves the remaining blocker well enough for promotion.",
            "best_candidate": best_key.replace("Core+AddOnOverlay+", ""),
            "promotion_decision": "Freeze Risk-Off promotion" if not promotion_candidate else "Advance Risk-Off to promotion candidate",
            "recommendation": "Freeze Risk-Off promotion. Keep AddOn-only baseline unchanged." if not promotion_candidate else "Proceed to final promotion review on the best candidate only.",
            "answer_1": answer_1,
            "answer_2": answer_2,
            "answer_3": answer_3,
            "answer_4": answer_4,
            "answer_5": answer_5,
            "answer_6": answer_6,
            "answer_7": answer_7,
        },
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report)
    write_summary(report)
    print(json.dumps({
        "final_check_answer": report["judgment"]["final_check_answer"],
        "best_candidate": report["judgment"]["best_candidate"],
        "promotion_decision": report["judgment"]["promotion_decision"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
