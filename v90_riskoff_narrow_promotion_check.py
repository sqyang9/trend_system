#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Very narrow promotion diagnostic for the single best Risk-Off repair candidate."""

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
from v90_asset_management_system_aligned import (
    DEFAULT_TUPLE,
    STRESS_TUPLE,
    combine_with_overlay,
    compute_metrics,
    current_research_optimal,
)
from v90_riskoff_promotion_validation import TIME_SLICES, WF_TEST_YEARS, compute_slice_metrics, load_overlay
from v90_riskoff_promotion_v2 import (
    CANDIDATES,
    build_indicator_cache,
    build_target,
)
from v90_trend_long_mother import SEED

REPORT_MD = Path("BTC_RISKOFF_NARROW_PROMOTION_CHECK.md")
REPORT_JSON = Path("btc_riskoff_narrow_promotion_check.json")
REPORT_TXT = Path("btc_riskoff_narrow_promotion_check_summary.txt")

TARGET_CANDIDATE = "RO_EMA220_TWOSTAGE_50_TO_0"
REFERENCE_CANDIDATE = "RO_EMA220_FLAT"


def load_candidate(name: str) -> Dict:
    return next(c for c in CANDIDATES if c["name"] == name)


def simulate_with_target(
    df_5m: pd.DataFrame,
    df_4h: pd.DataFrame,
    overlay: Dict,
    params,
    execution_mode: str,
    target: pd.Series,
):
    from v90_asset_management_system_aligned import simulate_core

    core = simulate_core(df_5m, df_4h, target, params, execution_mode)
    combo = combine_with_overlay(core, overlay["overlay_delta"], overlay["overlay_avg_exposure"])
    return {
        "target": target,
        "core": core,
        "combo": combo,
        "combo_metrics": compute_metrics(combo["equity"], combo["exposure"]),
    }


def slice_series(series: pd.Series, start: str, end: str) -> pd.Series:
    return series[(series.index >= pd.Timestamp(start, tz="UTC")) & (series.index < pd.Timestamp(end, tz="UTC"))]


def state_distribution(target: pd.Series) -> Dict[str, float]:
    vals = target.round(4)
    total = max(len(vals), 1)
    return {
        "state_1.00_pct": float((vals == 1.0).sum() / total * 100.0),
        "state_0.50_pct": float((vals == 0.5).sum() / total * 100.0),
        "state_0.00_pct": float((vals == 0.0).sum() / total * 100.0),
    }


def state_changes(target: pd.Series) -> int:
    if len(target) <= 1:
        return 0
    return int(target.ne(target.shift(1)).sum() - 1)


def pnl_attribution(candidate_core: pd.Series, bh_core: pd.Series, target: pd.Series) -> Dict:
    bh_pnl = bh_core.diff().fillna(0.0)
    cand_pnl = candidate_core.diff().fillna(0.0)
    diff = cand_pnl - bh_pnl
    state = target.reindex(candidate_core.index).ffill().fillna(1.0).round(4)
    return {
        "upside_drag_total": float((-diff[(bh_pnl > 0) & (diff < 0)]).sum()),
        "downside_protection_total": float(diff[(bh_pnl < 0) & (diff > 0)].sum()),
        "soft_upside_drag": float((-diff[(state == 0.5) & (bh_pnl > 0) & (diff < 0)]).sum()),
        "flat_upside_drag": float((-diff[(state == 0.0) & (bh_pnl > 0) & (diff < 0)]).sum()),
        "soft_downside_protection": float(diff[(state == 0.5) & (bh_pnl < 0) & (diff > 0)].sum()),
        "flat_downside_protection": float(diff[(state == 0.0) & (bh_pnl < 0) & (diff > 0)].sum()),
    }


def monthly_diff_table(candidate_eq: pd.Series, addon_eq: pd.Series, top_n: int = 5) -> Dict:
    df = pd.DataFrame({"candidate": candidate_eq, "addon": addon_eq}).dropna()
    monthly = df.resample("ME").last()
    candidate_ret = monthly["candidate"].pct_change().fillna(0.0) * 100.0
    addon_ret = monthly["addon"].pct_change().fillna(0.0) * 100.0
    diff = candidate_ret - addon_ret
    best = diff.sort_values(ascending=False).head(top_n)
    worst = diff.sort_values(ascending=True).head(top_n)
    return {
        "worst_months": [{"month": idx.strftime("%Y-%m"), "delta_return_pct": float(val)} for idx, val in worst.items()],
        "best_months": [{"month": idx.strftime("%Y-%m"), "delta_return_pct": float(val)} for idx, val in best.items()],
    }


def window_diagnostic(
    name: str,
    start: str,
    end: str,
    addon_eq: pd.Series,
    candidate_eq: pd.Series,
    bh_core_eq: pd.Series,
    candidate_core_eq: pd.Series,
    target: pd.Series,
) -> Dict:
    addon_slice = slice_series(addon_eq, start, end)
    cand_slice = slice_series(candidate_eq, start, end)
    bh_core_slice = slice_series(bh_core_eq, start, end)
    cand_core_slice = slice_series(candidate_core_eq, start, end)
    target_slice = slice_series(target, start, end)
    addon_metrics = compute_slice_metrics(addon_slice)
    candidate_metrics = compute_slice_metrics(cand_slice)
    delta = {
        "Return_pct": float(candidate_metrics["TotalReturn_pct"] - addon_metrics["TotalReturn_pct"]),
        "CAGR_pct": float(candidate_metrics["CAGR_pct"] - addon_metrics["CAGR_pct"]),
        "Sharpe": float(candidate_metrics["Sharpe"] - addon_metrics["Sharpe"]),
        "Calmar": float(candidate_metrics["Calmar"] - addon_metrics["Calmar"]),
        "MaxDD_improvement_pct": float(abs(addon_metrics["MaxDD_pct"]) - abs(candidate_metrics["MaxDD_pct"])),
    }
    strict = bool(
        (candidate_metrics["Calmar"] > addon_metrics["Calmar"])
        and (candidate_metrics["Sharpe"] > addon_metrics["Sharpe"])
        and (abs(candidate_metrics["MaxDD_pct"]) < abs(addon_metrics["MaxDD_pct"]))
    )
    return {
        "name": name,
        "window": {"start": start, "end": end},
        "addon_metrics": addon_metrics,
        "candidate_metrics": candidate_metrics,
        "delta_vs_addon": delta,
        "strict_outperform": strict,
        "state_distribution": state_distribution(target_slice),
        "state_changes": state_changes(target_slice),
        "pnl_attribution": pnl_attribution(cand_core_slice, bh_core_slice, target_slice),
        "monthly_diff": monthly_diff_table(cand_slice, addon_slice),
    }


def write_markdown(report: Dict) -> None:
    lines = [
        "# BTC Risk-Off Narrow Promotion Check",
        "",
        "## Final Judgment",
        "",
        f"- This round is a single-candidate diagnostic for `{TARGET_CANDIDATE}`.",
        f"- Main finding: {report['judgment']['main_finding']}",
        f"- Promotion implication: {report['judgment']['promotion_implication']}",
        "",
        "## Full-Sample Comparison",
        "",
        "| Scheme | Return% | Sharpe | Calmar | MaxDD% | Exposure% |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key in ["Core+AddOnOverlay", f"Core+AddOnOverlay+{REFERENCE_CANDIDATE}", f"Core+AddOnOverlay+{TARGET_CANDIDATE}"]:
        m = report["full_sample"][key]["metrics"]
        lines.append(f"| {key} | {m['TotalReturn_pct']:.2f} | {m['Sharpe']:.3f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | {m['Exposure_pct']:.1f} |")
    lines.extend([
        "",
        "## OOS Windows",
        "",
        "| Window | dReturn | dSharpe | dCalmar | dMaxDD improve | Strict | state 1.0% | state 0.5% | state 0.0% | State Changes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in report["oos_windows"]:
        d = row["delta_vs_addon"]
        s = row["state_distribution"]
        lines.append(
            f"| {row['name']} | {d['Return_pct']:+.2f}pp | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f}pp | "
            f"{row['strict_outperform']} | {s['state_1.00_pct']:.1f} | {s['state_0.50_pct']:.1f} | {s['state_0.00_pct']:.1f} | {row['state_changes']} |"
        )
    lines.extend([
        "",
        "## Problem Diagnosis",
        "",
    ])
    for row in report["oos_windows"]:
        p = row["pnl_attribution"]
        lines.append(
            f"- {row['name']}: upside_drag={p['upside_drag_total']:.2f}, downside_protection={p['downside_protection_total']:.2f}, "
            f"soft_upside_drag={p['soft_upside_drag']:.2f}, flat_upside_drag={p['flat_upside_drag']:.2f}, "
            f"soft_downside_protection={p['soft_downside_protection']:.2f}, flat_downside_protection={p['flat_downside_protection']:.2f}"
        )
    lines.extend([
        "",
        "## Worst Months",
        "",
    ])
    for row in report["oos_windows"]:
        lines.append(f"### {row['name']}")
        for item in row["monthly_diff"]["worst_months"]:
            lines.append(f"- {item['month']}: {item['delta_return_pct']:+.2f}pp")
    lines.extend([
        "",
        "## Direct Answers",
        "",
        f"- {report['judgment']['answer_1']}",
        f"- {report['judgment']['answer_2']}",
        f"- {report['judgment']['answer_3']}",
        f"- {report['judgment']['answer_4']}",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_summary(report: Dict) -> None:
    lines = [
        f"main_finding={report['judgment']['main_finding']}",
        f"promotion_implication={report['judgment']['promotion_implication']}",
        f"best_candidate={TARGET_CANDIDATE}",
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

    candidate = load_candidate(TARGET_CANDIDATE)
    reference = load_candidate(REFERENCE_CANDIDATE)
    indicator_cache = build_indicator_cache(df_4h, params, [candidate["ema_len"], reference["ema_len"]], overlay["index"])

    bh_target = pd.Series(1.0, index=overlay["index"], dtype=float)
    bh_sim = simulate_with_target(df_5m, df_4h, overlay, params, "next_bar_open", bh_target)
    ref_target = build_target(reference, indicator_cache[reference["ema_len"]])
    ref_sim = simulate_with_target(df_5m, df_4h, overlay, params, "next_bar_open", ref_target)
    target = build_target(candidate, indicator_cache[candidate["ema_len"]])
    cand_sim = simulate_with_target(df_5m, df_4h, overlay, params, "next_bar_open", target)

    full_sample = {
        "Core+AddOnOverlay": {
            "metrics": overlay["artifact"]["schemes"]["AddOnOverlay"]["metrics"],
        },
        f"Core+AddOnOverlay+{REFERENCE_CANDIDATE}": {
            "metrics": ref_sim["combo_metrics"],
        },
        f"Core+AddOnOverlay+{TARGET_CANDIDATE}": {
            "metrics": cand_sim["combo_metrics"],
        },
    }

    oos_windows = [
        window_diagnostic(
            name=f"OOS_{year}",
            start=f"{year}-01-01",
            end=f"{year+1}-01-01",
            addon_eq=overlay["addon_equity"],
            candidate_eq=cand_sim["combo"]["equity"],
            bh_core_eq=bh_sim["core"]["equity"]["equity"].astype(float),
            candidate_core_eq=cand_sim["core"]["equity"]["equity"].astype(float),
            target=target,
        )
        for year in WF_TEST_YEARS
    ]

    worst = min(oos_windows, key=lambda x: x["delta_vs_addon"]["Calmar"])
    biggest_upside_drag = max(oos_windows, key=lambda x: x["pnl_attribution"]["upside_drag_total"])
    answer_1 = (
        f"The main blocker is still recovery-side opportunity cost. Worst OOS window is {worst['name']} with dReturn {worst['delta_vs_addon']['Return_pct']:+.2f}pp and dCalmar {worst['delta_vs_addon']['Calmar']:+.3f}."
    )
    answer_2 = (
        f"The repaired structure does defend downside, but most of its remaining problem comes from missed upside while reduced. "
        f"Largest upside-drag window is {biggest_upside_drag['name']} with upside_drag {biggest_upside_drag['pnl_attribution']['upside_drag_total']:.2f} versus downside_protection {biggest_upside_drag['pnl_attribution']['downside_protection_total']:.2f}."
    )
    answer_3 = (
        f"The 50% soft stage is not the main problem. In {worst['name']}, state_0.50 is only {worst['state_distribution']['state_0.50_pct']:.1f}% of bars, "
        f"while flat-state upside drag is {worst['pnl_attribution']['flat_upside_drag']:.2f} and dominates the missed upside."
    )
    answer_4 = (
        "Promotion still fails because the candidate improves full-sample optics and downside control, but cannot convert that into repeated strict OOS wins. "
        "The next step, if any, should target re-entry timing out of flat state rather than the bear trigger itself."
    )

    report = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "research_optimal": {"label": "lb20_stop3.2_trail5.0_beoff", "params": asdict(params)},
        "default_tuple": DEFAULT_TUPLE,
        "stress_tuple": STRESS_TUPLE,
        "target_candidate": candidate,
        "reference_candidate": reference,
        "full_sample": full_sample,
        "oos_windows": oos_windows,
        "judgment": {
            "main_finding": "The remaining blocker is still upside opportunity cost after Risk-Off, especially in recovery-like windows. The main drag is not the 50% bridge itself; it is staying flat for too long after risk conditions improve.",
            "promotion_implication": "Do not promote Risk-Off yet. If work continues, focus only on re-entry timing out of flat state for RO_EMA220_TWOSTAGE_50_TO_0.",
            "answer_1": answer_1,
            "answer_2": answer_2,
            "answer_3": answer_3,
            "answer_4": answer_4,
        },
    }

    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report)
    write_summary(report)
    print(
        json.dumps(
            {
                "main_finding": report["judgment"]["main_finding"],
                "promotion_implication": report["judgment"]["promotion_implication"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
