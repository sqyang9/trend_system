#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Positioning validation for the squeeze_release_20 long-only mother."""

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
from v90_trend_long_mother import SEED, TrendLongParams, compare_to_buy_hold, gatekeeper_v2_for_long_trend, run_candidate, with_overrides


DEFAULT_TUPLE = "next_bar_open + legacy_bar_extrema + midpoint + full_model"
STRESS_TUPLE = "live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model"
NON_BASELINE_GATES = [
    "yearly",
    "rolling_oos",
    "regime",
    "cost_stress",
    "slippage_stress",
    "execution_mode_stress",
    "intrabar_path_stress",
    "live_safety_check",
]


def current_research_optimal() -> TrendLongParams:
    return TrendLongParams(
        candidate_name="squeeze_release_20",
        description="Squeeze release plus 20-bar breakout inside a bullish EMA200 regime, designed to enter expansion after compression.",
        breakout_mode="squeeze_release",
        donchian_entry_len=20,
        squeeze_threshold=0.90,
        squeeze_bars=6,
        adx_min=10.0,
        close_location_min=0.60,
        range_atr_min=0.55,
        initial_stop_atr=3.2,
        trail_atr_mult=5.0,
        trail_activate_atr=2.5,
        use_swing_trail=False,
        break_even_after_atr=1e9,
    )


def calmar(cagr_pct: float, maxdd_pct: float) -> float:
    return 0.0 if maxdd_pct >= 0 else (cagr_pct / 100.0) / abs(maxdd_pct / 100.0)


def label_for(params: TrendLongParams) -> str:
    be = "off" if params.break_even_after_atr >= 1e8 else f"{params.break_even_after_atr:.1f}"
    return f"lb{params.donchian_entry_len}_stop{params.initial_stop_atr:.1f}_trail{params.trail_atr_mult:.1f}_be{be}"


def behavior_light(result: Dict) -> Dict:
    trades = result.get("trades")
    if trades is None or trades.empty:
        return {
            "avg_hold_4h_bars": 0.0,
            "median_hold_4h_bars": 0.0,
            "top10_winner_contrib_pct": 0.0,
            "exit_mix": {},
        }
    df = trades.copy()
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)
    df["exit_time"] = pd.to_datetime(df["exit_time"], utc=True)
    hold_4h = (df["exit_time"] - df["entry_time"]).dt.total_seconds() / (240.0 * 60.0)
    winners = df[df["pnl"] > 0].sort_values("pnl", ascending=False)
    total_profit = float(winners["pnl"].sum()) if not winners.empty else 0.0
    top10 = float(winners.head(10)["pnl"].sum()) if not winners.empty else 0.0
    return {
        "avg_hold_4h_bars": float(hold_4h.mean()),
        "median_hold_4h_bars": float(hold_4h.median()),
        "top10_winner_contrib_pct": float(top10 / total_profit * 100.0) if total_profit > 0 else 0.0,
        "exit_mix": df["exit_reason"].value_counts(normalize=True).to_dict(),
    }


def evaluate_raw(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    print(f"raw {label_for(params)}", flush=True)
    result = run_candidate(df_5m, df_4h, params)
    stats = result["stats"]
    bh = compare_to_buy_hold(result, df_4h)
    return {
        "label": label_for(params),
        "params": asdict(params),
        "stats": {
            "Return_pct": float(stats["TotalReturn_pct"]),
            "CAGR_pct": float(stats["CAGR"] * 100.0),
            "Sharpe": float(stats["Sharpe"]),
            "Calmar": float(calmar(float(stats["CAGR"] * 100.0), float(stats["MaxDD_pct"] * 100.0))),
            "MaxDD_pct": float(stats["MaxDD_pct"] * 100.0),
            "PF": float(stats["ProfitFactor"]),
            "Trades": int(stats["Trades"]),
        },
        "behavior": behavior_light(result),
        "buy_hold_delta": {
            "return_vs_bh_pct": float(bh["delta"]["return_vs_bh_pct"]),
            "cagr_vs_bh_pct": float(bh["delta"]["cagr_vs_bh_pct"]),
            "sharpe_vs_bh": float(bh["delta"]["sharpe_vs_bh"]),
            "calmar_vs_bh": float(bh["delta"]["calmar_vs_bh"]),
        },
    }


def add_deltas(row: Dict, base: Dict) -> Dict:
    out = dict(row)
    out["delta_vs_base"] = {
        "Return_pct": float(row["stats"]["Return_pct"] - base["stats"]["Return_pct"]),
        "CAGR_pct": float(row["stats"]["CAGR_pct"] - base["stats"]["CAGR_pct"]),
        "Sharpe": float(row["stats"]["Sharpe"] - base["stats"]["Sharpe"]),
        "Calmar": float(row["stats"]["Calmar"] - base["stats"]["Calmar"]),
        "MaxDD_pct": float(row["stats"]["MaxDD_pct"] - base["stats"]["MaxDD_pct"]),
    }
    out["vs_buy_hold_change"] = {
        "return_gap_change_pct": float(row["buy_hold_delta"]["return_vs_bh_pct"] - base["buy_hold_delta"]["return_vs_bh_pct"]),
        "cagr_gap_change_pct": float(row["buy_hold_delta"]["cagr_vs_bh_pct"] - base["buy_hold_delta"]["cagr_vs_bh_pct"]),
        "sharpe_edge_change": float(row["buy_hold_delta"]["sharpe_vs_bh"] - base["buy_hold_delta"]["sharpe_vs_bh"]),
        "calmar_edge_change": float(row["buy_hold_delta"]["calmar_vs_bh"] - base["buy_hold_delta"]["calmar_vs_bh"]),
        "return_gap_shrinks": bool(row["buy_hold_delta"]["return_vs_bh_pct"] > base["buy_hold_delta"]["return_vs_bh_pct"]),
        "cagr_gap_shrinks": bool(row["buy_hold_delta"]["cagr_vs_bh_pct"] > base["buy_hold_delta"]["cagr_vs_bh_pct"]),
        "risk_adjusted_edge_kept": bool(
            row["buy_hold_delta"]["sharpe_vs_bh"] >= 0.0 and row["buy_hold_delta"]["calmar_vs_bh"] >= 0.0
        ),
    }
    return out


def sort_key(row: Dict, base: Dict) -> Tuple[float, float, float, float, float]:
    delta = row["delta_vs_base"]
    bh = row["vs_buy_hold_change"]
    return (
        bh["cagr_gap_change_pct"],
        bh["return_gap_change_pct"],
        delta["CAGR_pct"],
        delta["Sharpe"] + delta["Calmar"],
        delta["MaxDD_pct"],
    )


def should_test_break_even(row: Dict, base: Dict) -> bool:
    delta = row["delta_vs_base"]
    return (
        delta["Return_pct"] >= 15.0
        and delta["CAGR_pct"] >= 1.0
        and delta["Sharpe"] >= 0.0
        and delta["Calmar"] >= 0.0
        and delta["MaxDD_pct"] >= -0.5
    )


def compact_gate(gate: Dict) -> Dict:
    return {
        "gate_summary": gate["gate_summary"],
        "final_pass": bool(gate["final_pass"]),
        "baseline_gate": gate["baseline_gate"],
        "trend_gate_mismatch": gate["trend_gate_mismatch"],
        "key_rows": {
            "yearly": gate["yearly"],
            "rolling_oos": gate["rolling_oos"],
            "regime": gate["regime"],
            "cost_stress": gate["cost_stress"],
            "slippage_stress": gate["slippage_stress"],
            "execution_mode_stress": gate["execution_mode_stress"],
            "intrabar_path_stress": gate["intrabar_path_stress"],
            "live_safety_check": gate["live_safety_check"],
        },
    }


def evaluate_full_gate(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams, with_launch_gate: bool) -> Dict:
    print(f"gate {label_for(params)}", flush=True)
    full_gate = gatekeeper_v2_for_long_trend(df_5m, df_4h, params, Path("."))
    out = {"full_size": compact_gate(full_gate)}
    if with_launch_gate:
        print(f"gate35 {label_for(params)}", flush=True)
        launch_gate = gatekeeper_v2_for_long_trend(df_5m, df_4h, with_overrides(params, position_pct=35.0), Path("."))
        out["launch_35pct"] = compact_gate(launch_gate)
    return out


def positioning_decision(base: Dict, gate_checks: Dict, ranked_non_base: List[Dict]) -> Dict:
    repeatable = [
        row for row in ranked_non_base
        if row["delta_vs_base"]["Return_pct"] > 10.0
        and row["delta_vs_base"]["CAGR_pct"] > 0.5
        and row["delta_vs_base"]["Sharpe"] >= -0.02
        and row["delta_vs_base"]["Calmar"] >= -0.05
        and row["delta_vs_base"]["MaxDD_pct"] >= -1.0
        and row["vs_buy_hold_change"]["return_gap_shrinks"]
        and row["vs_buy_hold_change"]["cagr_gap_shrinks"]
    ]
    stable_gate_count = 0
    for check in gate_checks.values():
        summary = check["full_size"]["gate_summary"]
        if all(bool(summary.get(name, False)) for name in NON_BASELINE_GATES):
            stable_gate_count += 1
    if len(repeatable) >= 2 and stable_gate_count >= 1:
        verdict = "A"
        label = "Still Worth Testing As Independent Main Strategy"
        rationale = (
            "The micro-neighborhood still shows repeatable CAGR and return improvement while preserving non-baseline gate stability, "
            "so the line still has room to keep pressing toward an independent main-strategy profile."
        )
    else:
        verdict = "B"
        label = "Better Defined As High-Quality Overlay"
        rationale = (
            "The line keeps strong risk-adjusted behavior and healthier drawdown structure, but the allowed neighborhood only offers "
            "incremental absolute-return improvement. That is not enough to materially change the gap to BTC buy-and-hold."
        )
    return {
        "verdict": verdict,
        "label": label,
        "repeatable_candidate_count": len(repeatable),
        "stable_gate_candidate_count": stable_gate_count,
        "rationale": rationale,
    }


def markdown_table(rows: List[Dict]) -> List[str]:
    lines = [
        "| Variant | Return% | CAGR% | Sharpe | Calmar | MaxDD% | PF | Trades | dRet | dCAGR | dSharpe | dCalmar | dMaxDD | BH gap shrinks? |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        s = row["stats"]
        d = row["delta_vs_base"]
        b = row["vs_buy_hold_change"]
        lines.append(
            f"| {row['label']} | {s['Return_pct']:.2f} | {s['CAGR_pct']:.2f} | {s['Sharpe']:.3f} | {s['Calmar']:.3f} | {s['MaxDD_pct']:.2f} | {s['PF']:.3f} | {s['Trades']} | {d['Return_pct']:+.2f} | {d['CAGR_pct']:+.2f} | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_pct']:+.2f} | {'yes' if (b['return_gap_shrinks'] and b['cagr_gap_shrinks']) else 'no'} |"
        )
    return lines


def write_positioning_report(payload: Dict) -> None:
    Path("squeeze20_positioning_report.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    summary_lines = [
        f"positioning={payload['positioning_decision']['label']}",
        f"verdict={payload['positioning_decision']['verdict']}",
        f"research_optimal={payload['current_research_optimal']}",
        f"continue_pushing_independent_strategy={str(payload['recommendation']['continue_independent_push'])}",
    ]
    Path("squeeze20_positioning_summary.txt").write_text("\n".join(summary_lines), encoding="utf-8")

    top_rows = payload["ranked_candidates"][:8]
    lines = [
        "# SQUEEZE20 Positioning Report",
        "",
        "## Conclusion",
        "",
        f"- Final judgment: {payload['positioning_decision']['label']} (Path {payload['positioning_decision']['verdict']})",
        f"- Current research_optimal: `{payload['current_research_optimal']}`",
        f"- Why: {payload['positioning_decision']['rationale']}",
        f"- Continue pushing toward independent main strategy: {payload['recommendation']['continue_independent_push']}",
        f"- Recommended framing now: {payload['recommendation']['framing']}",
        "",
        "## Neighborhood Summary",
        "",
        *markdown_table(top_rows),
        "",
        "## Buy-And-Hold Positioning",
        "",
        f"- Base vs B&H return gap: {payload['base']['buy_hold_delta']['return_vs_bh_pct']:.2f}pp",
        f"- Base vs B&H CAGR gap: {payload['base']['buy_hold_delta']['cagr_vs_bh_pct']:.2f}pp",
        f"- Best raw challenger vs B&H return gap change: {payload['best_raw_non_base']['vs_buy_hold_change']['return_gap_change_pct']:+.2f}pp",
        f"- Best raw challenger vs B&H CAGR gap change: {payload['best_raw_non_base']['vs_buy_hold_change']['cagr_gap_change_pct']:+.2f}pp",
        f"- Best raw challenger keeps risk-adjusted edge vs B&H: {payload['best_raw_non_base']['vs_buy_hold_change']['risk_adjusted_edge_kept']}",
        "",
        "## Gate Stability Check",
        "",
        f"- Base non-baseline gate summary: {json.dumps(payload['base']['full_gate']['full_size']['gate_summary'], ensure_ascii=False)}",
    ]
    for label, gate in payload["gate_checks"].items():
        lines.append(f"- `{label}` full-size gate summary: {json.dumps(gate['full_size']['gate_summary'], ensure_ascii=False)}")
        if "launch_35pct" in gate:
            lines.append(f"- `{label}` 35% gate summary: {json.dumps(gate['launch_35pct']['gate_summary'], ensure_ascii=False)}")
    lines.extend([
        "",
        "## Recommendation",
        "",
        f"- Main call: {payload['recommendation']['main_call']}",
        f"- Next step: {payload['recommendation']['next_step']}",
        f"- Break-even side check: {payload['break_even_side_check']['status']}",
    ])
    Path("SQUEEZE20_POSITIONING_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def write_gate_proposal(payload: Dict) -> None:
    base = payload["base"]
    lines = [
        "# Trend Gate Profile Proposal",
        "",
        "## Conclusion",
        "",
        "- Current `baseline_gate` clearly inherits a high-frequency / many-trades expectation from the old v85 lineage.",
        "- `Trades >= 250` is not a good fit for the current low-frequency trend mother.",
        "- This proposal is for review only. It should not be activated immediately and should not be used retroactively to force the current system through gatekeeping.",
        "",
        "## Evidence Of Mismatch",
        "",
        "- Current baseline gate thresholds are: Sharpe >= 0.80, MaxDD >= -30%, ProfitFactor >= 1.15, Trades >= 250.",
        f"- Current long-only research_optimal has {base['stats']['Trades']} trades, avg hold {base['behavior']['avg_hold_4h_bars']:.1f} 4H bars, and top10 winner contribution {base['behavior']['top10_winner_contrib_pct']:.1f}%.",
        "- That profile is a classic low-frequency trend process: few entries, long holds, large winner dependence, and trailing-stop exits.",
        "- Forcing a 250-trade minimum on this type of system encourages the wrong behavior: more signals, shorter holds, and a drift away from the mother process being studied.",
        "",
        "## Why Trades >= 250 Is A Poor Fit Here",
        "",
        "- It assumes opportunity count is the main proxy for statistical credibility, which is more defensible for higher-frequency or multi-leg systems than for trend systems driven by a small number of large moves.",
        "- It ignores holding-period structure. A system holding for roughly 10 days on average cannot naturally generate 250 trades over this sample without changing its identity.",
        "- It double-penalizes low-frequency trend systems because they already face winner concentration and regime dependence; adding a high trade-count floor pushes them toward over-trading.",
        "",
        "## Proposal For A Low-Frequency Trend Gate Profile",
        "",
        "- Minimum unique entries: require a lower floor such as 40-60 total entries over the full sample, not 250 trades.",
        "- Minimum yearly activity: require active entries in most yearly windows, for example at least 5 of 7 yearly slices with at least 3 entries.",
        "- Rolling OOS consistency: retain rolling OOS and yearly pass conditions as first-class requirements.",
        "- Risk floor: keep Sharpe, PF, and MaxDD minimums, but tune them for low-frequency systems instead of inheriting the legacy high-turnover profile.",
        "- Holding-period floor: require a median or average holding-period minimum to make sure the profile is truly low-frequency trend, not pseudo-low-trade noise.",
        "- Exposure consistency: track whether exposure remains within a stable band rather than collapsing into accidental under-investment.",
        "- Winner concentration cap: monitor large-winner concentration and reject pathological cases, but do not set the cap so tight that real trend systems become impossible to pass.",
        "",
        "## Why This Cannot Be Activated Yet",
        "",
        "- This repository currently has one primary low-frequency trend mother, not a validated family of such systems.",
        "- A new gate profile should be calibrated on multiple low-frequency trend candidates, not around a single winner.",
        "- The proposal should therefore be treated as an auditable discussion baseline for a later gate-review cycle, not as an immediate rules change.",
    ]
    Path("TREND_GATE_PROFILE_PROPOSAL.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    base_params = current_research_optimal()
    raw_candidates: List[TrendLongParams] = []
    for lookback in [20, 21, 22]:
        for stop in [3.1, 3.2, 3.3]:
            for trail in [5.0, 5.2]:
                raw_candidates.append(
                    with_overrides(
                        base_params,
                        donchian_entry_len=lookback,
                        initial_stop_atr=stop,
                        trail_atr_mult=trail,
                        break_even_after_atr=1e9,
                    )
                )

    raw_rows = [evaluate_raw(df_5m, df_4h, params) for params in raw_candidates]
    base_row = next(row for row in raw_rows if row["label"] == label_for(base_params))
    rows = [add_deltas(row, base_row) for row in raw_rows]
    rows.sort(key=lambda row: sort_key(row, base_row), reverse=True)

    best_raw_non_base = next(row for row in rows if row["label"] != base_row["label"])
    break_even_side_check = {"status": "not tested; no raw candidate cleared the evidence threshold for a restrained break-even side check", "row": None}
    if should_test_break_even(best_raw_non_base, base_row):
        be_params = with_overrides(TrendLongParams(**best_raw_non_base["params"]), break_even_after_atr=4.0)
        be_row = add_deltas(evaluate_raw(df_5m, df_4h, be_params), base_row)
        rows.append(be_row)
        rows.sort(key=lambda row: sort_key(row, base_row), reverse=True)
        break_even_side_check = {
            "status": f"tested `be=4.0` on {best_raw_non_base['label']}",
            "row": be_row,
        }
        best_raw_non_base = next(row for row in rows if row["label"] != base_row["label"])

    gate_targets = []
    for row in rows:
        if row["label"] == base_row["label"]:
            continue
        if row["label"] not in gate_targets:
            gate_targets.append(row["label"])
        if len(gate_targets) >= 2:
            break

    base_full_gate = json.loads(Path("squeeze20_lb20_stop3.2_gatekeeper_v2.json").read_text(encoding="utf-8"))
    base_launch_gate = json.loads(Path("squeeze20_lb20_stop3.2_gatekeeper_v2_35pct.json").read_text(encoding="utf-8"))
    base_row["full_gate"] = {
        "full_size": {
            "gate_summary": base_full_gate["gatekeeper_v2"]["full_size"]["gate_summary"],
            "final_pass": base_full_gate["gatekeeper_v2"]["full_size"]["final_pass"],
            "baseline_gate": base_full_gate["gatekeeper_v2"]["full_size"]["baseline_gate"],
            "trend_gate_mismatch": base_full_gate["gatekeeper_v2"]["full_size"]["trend_gate_mismatch"],
        },
        "launch_35pct": {
            "gate_summary": base_launch_gate["gate_summary"],
            "final_pass": base_launch_gate["final_pass"],
            "baseline_gate": base_launch_gate["baseline_gate"],
            "trend_gate_mismatch": base_launch_gate["trend_gate_mismatch"],
        },
    }

    gate_checks: Dict[str, Dict] = {}
    for idx, label in enumerate(gate_targets):
        row = next(r for r in rows if r["label"] == label)
        gate_checks[label] = evaluate_full_gate(
            df_5m,
            df_4h,
            TrendLongParams(**row["params"]),
            with_launch_gate=(idx == 0),
        )

    decision = positioning_decision(base_row, gate_checks, [row for row in rows if row["label"] != base_row["label"]])
    continue_push = decision["verdict"] == "A"
    recommendation = {
        "continue_independent_push": continue_push,
        "framing": "independent main-strategy candidate" if continue_push else "high-quality trend overlay",
        "main_call": (
            "Keep pushing toward independent main-strategy status."
            if continue_push
            else "Formally treat the line as a high-quality overlay unless a later local improvement materially shrinks the BTC buy-and-hold gap."
        ),
        "next_step": (
            "Continue a tightly-bounded local search for absolute-return improvement while preserving the current risk profile."
            if continue_push
            else "Stop treating marginal local improvements as evidence of imminent main-strategy status; future work should only continue if it can materially reduce the BTC buy-and-hold gap without degrading the current risk structure."
        ),
    }

    payload = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "current_research_optimal": base_row["label"],
        "default_research_tuple": DEFAULT_TUPLE,
        "stress_tuple": STRESS_TUPLE,
        "base": base_row,
        "candidate_grid": {
            "donchian_entry_len": [20, 21, 22],
            "initial_stop_atr": [3.1, 3.2, 3.3],
            "trail_atr_mult": [5.0, 5.2],
            "break_even": "disabled by default; one restrained 4.0 side-check only if raw evidence is strong",
        },
        "ranked_candidates": rows,
        "best_raw_non_base": best_raw_non_base,
        "gate_checks": gate_checks,
        "break_even_side_check": break_even_side_check,
        "positioning_decision": decision,
        "recommendation": recommendation,
    }

    write_positioning_report(payload)
    write_gate_proposal(payload)
    print(json.dumps({
        "verdict": decision["verdict"],
        "label": decision["label"],
        "best_raw_non_base": best_raw_non_base["label"],
        "continue_independent_push": continue_push,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
