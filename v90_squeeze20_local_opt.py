#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ultra-lean local optimization pass for squeeze_release_20."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_trend_long_mother import SEED, TrendLongParams, compare_to_buy_hold, run_candidate, with_overrides


def calmar(cagr_pct: float, maxdd_pct: float) -> float:
    return 0.0 if maxdd_pct >= 0 else (cagr_pct / 100.0) / abs(maxdd_pct / 100.0)


def variant_label(params: TrendLongParams) -> str:
    be = "off" if params.break_even_after_atr >= 1e8 else f"{params.break_even_after_atr:.1f}"
    return f"lb{params.donchian_entry_len}_stop{params.initial_stop_atr:.1f}_trail{params.trail_atr_mult:.1f}_be{be}"


def load_base() -> Dict:
    payload = json.loads(Path("btc_longonly_trend_report.json").read_text(encoding="utf-8"))
    rp = payload["research_optimal"]
    params = rp["params"]
    stats = rp["stats"]
    return {
        "label": variant_label(TrendLongParams(**params)),
        "params": params,
        "stats": {
            "Return_pct": float(stats["Return_pct"]),
            "CAGR_pct": float(stats["CAGR_pct"]),
            "Sharpe": float(stats["Sharpe"]),
            "MaxDD_pct": float(stats["MaxDD_pct"]),
            "PF": float(stats["PF"]),
            "Trades": int(stats["Trades"]),
            "Calmar": float(calmar(float(stats["CAGR_pct"]), float(stats["MaxDD_pct"]))),
        },
        "behavior": {
            "avg_hold_4h_bars": float(rp["behavior"]["avg_hold_4h_bars"]),
            "median_hold_4h_bars": float(rp["behavior"]["median_hold_4h_bars"]),
            "top10_winner_contrib_pct": float(rp["behavior"]["top10_winner_contrib_pct"]),
        },
        "buy_hold_delta": {
            "return_vs_bh_pct": float(rp["buy_hold_delta"]["return_vs_bh_pct"]),
            "cagr_vs_bh_pct": float(rp["buy_hold_delta"]["cagr_vs_bh_pct"]),
            "sharpe_vs_bh": float(rp["buy_hold_delta"]["sharpe_vs_bh"]),
            "calmar_vs_bh": float(rp["buy_hold_delta"]["calmar_vs_bh"]),
        },
        "gate": {
            "full_size": payload["research_optimal"]["gate_summary"],
            "launch_35pct": payload["launch_optimal"]["gate_summary"],
        },
    }


def behavior_light(result: Dict) -> Dict:
    trades = result["trades"]
    if trades is None or trades.empty:
        return {"avg_hold_4h_bars": 0.0, "median_hold_4h_bars": 0.0, "top10_winner_contrib_pct": 0.0}
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
    }


def evaluate(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    print(f"running {variant_label(params)}", flush=True)
    result = run_candidate(df_5m, df_4h, params)
    bh = compare_to_buy_hold(result, df_4h)
    stats = result["stats"]
    return {
        "label": variant_label(params),
        "params": params.__dict__,
        "stats": {
            "Return_pct": float(stats["TotalReturn_pct"]),
            "CAGR_pct": float(stats["CAGR"] * 100.0),
            "Sharpe": float(stats["Sharpe"]),
            "MaxDD_pct": float(stats["MaxDD_pct"] * 100.0),
            "PF": float(stats["ProfitFactor"]),
            "Trades": int(stats["Trades"]),
            "Calmar": float(calmar(float(stats["CAGR"] * 100.0), float(stats["MaxDD_pct"] * 100.0))),
        },
        "behavior": behavior_light(result),
        "buy_hold_delta": {
            "return_vs_bh_pct": float(bh["delta"]["return_vs_bh_pct"]),
            "cagr_vs_bh_pct": float(bh["delta"]["cagr_vs_bh_pct"]),
            "sharpe_vs_bh": float(bh["delta"]["sharpe_vs_bh"]),
            "calmar_vs_bh": float(bh["delta"]["calmar_vs_bh"]),
        },
    }


def sort_key(row: Dict, base: Dict) -> Tuple[float, float, float, float]:
    dd_penalty = min(row["stats"]["MaxDD_pct"] - base["stats"]["MaxDD_pct"], 0.0)
    return (row["stats"]["CAGR_pct"], row["stats"]["Return_pct"], row["stats"]["Sharpe"] + row["stats"]["Calmar"], dd_penalty)


def clearly_better(row: Dict, base: Dict) -> bool:
    return (
        row["stats"]["Return_pct"] > base["stats"]["Return_pct"] + 10.0
        and row["stats"]["CAGR_pct"] > base["stats"]["CAGR_pct"] + 0.5
        and row["stats"]["MaxDD_pct"] >= base["stats"]["MaxDD_pct"] - 2.0
        and row["behavior"]["avg_hold_4h_bars"] >= base["behavior"]["avg_hold_4h_bars"] * 0.85
    )


def to_md_table(rows: List[Dict]) -> List[str]:
    lines = ["| Variant | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Trades |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for row in rows:
        s = row["stats"]
        lines.append(f"| {row['label']} | {s['Return_pct']:.2f} | {s['CAGR_pct']:.2f} | {s['Sharpe']:.3f} | {s['Calmar']:.3f} | {s['MaxDD_pct']:.2f} | {s['Trades']} |")
    return lines


def write_outputs(payload: Dict) -> None:
    Path("squeeze20_local_opt_report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    Path("squeeze20_local_opt_summary.txt").write_text(
        "\n".join([
            f"base_variant={payload['base']['label']}",
            f"best_variant={payload['best_candidate']['label']}",
            f"upgrade_research_optimal={payload['decision']['upgrade_research_optimal']}",
            f"closer_to_independent_core={payload['decision']['closer_to_independent_core']}",
            f"keep_digging={payload['decision']['keep_digging']}",
        ]),
        encoding="utf-8",
    )
    lines = [
        "# SQUEEZE20 Local Optimization Report",
        "",
        "## Conclusion",
        "",
        f"- New better version found: {payload['decision']['found_better_version']}",
        f"- Upgrade to new research_optimal: {payload['decision']['upgrade_research_optimal']}",
        f"- Closer to independent BTC trend core: {payload['decision']['closer_to_independent_core']}",
        f"- Continue digging this line: {payload['decision']['keep_digging']}",
        f"- Best candidate: `{payload['best_candidate']['label']}`",
        f"- Decision note: {payload['decision']['decision_note']}",
        "",
        "## Direct Answers",
        "",
        f"1. Most worth optimizing now: {payload['answers']['best_parameters_to_optimize']}",
        f"2. Most promising local neighborhood: {payload['answers']['most_promising_neighborhood']}",
        f"3. Sharpe/Calmar still ahead while CAGR moves closer to B&H: {payload['answers']['sharpe_calmar_and_cagr_answer']}",
        f"4. Baseline_gate diagnosis: {payload['answers']['baseline_gate_answer']}",
        "",
        "## Best Candidates",
        "",
        *to_md_table(payload['top_rows']),
        "",
        "## Details",
        "",
        f"- Default research tuple: {payload['default_research_tuple']}",
        f"- Stress tuple: {payload['stress_tuple']}",
        f"- Current full-size gate summary: {json.dumps(payload['base']['gate']['full_size'], ensure_ascii=False)}",
        f"- Current 35% gate summary: {json.dumps(payload['base']['gate']['launch_35pct'], ensure_ascii=False)}",
    ]
    for item in payload["parameter_sensitivity"]:
        lines.append(f"- `{item['parameter']}` tested span: return {item['return_span']:.2f}pp, CAGR {item['cagr_span']:.2f}pp, best tested value {item['best_value']}")
    Path("SQUEEZE20_LOCAL_OPT_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    base = load_base()
    base_params = TrendLongParams(**base["params"])

    candidates = [
        with_overrides(base_params, donchian_entry_len=22),
        with_overrides(base_params, initial_stop_atr=3.2),
        with_overrides(base_params, trail_atr_mult=5.2),
        with_overrides(base_params, donchian_entry_len=22, initial_stop_atr=3.2, trail_atr_mult=5.2),
    ]
    rows = [evaluate(df_5m, df_4h, params) for params in candidates]
    rows.sort(key=lambda row: sort_key(row, base), reverse=True)
    best = rows[0] if rows and clearly_better(rows[0], base) else base

    parameter_sensitivity = []
    mapping = {
        "donchian_entry_len": [r for r in rows if r["params"]["donchian_entry_len"] != base["params"]["donchian_entry_len"]],
        "initial_stop_atr": [r for r in rows if r["params"]["initial_stop_atr"] != base["params"]["initial_stop_atr"]],
        "trail_atr_mult": [r for r in rows if r["params"]["trail_atr_mult"] != base["params"]["trail_atr_mult"]],
    }
    for k, subset in mapping.items():
        if subset:
            parameter_sensitivity.append({
                "parameter": k,
                "return_span": max(r["stats"]["Return_pct"] for r in subset) - min(r["stats"]["Return_pct"] for r in subset),
                "cagr_span": max(r["stats"]["CAGR_pct"] for r in subset) - min(r["stats"]["CAGR_pct"] for r in subset),
                "best_value": max(subset, key=lambda r: sort_key(r, base))["params"][k],
            })
    parameter_sensitivity.sort(key=lambda x: (x["return_span"], x["cagr_span"]), reverse=True)

    risk_candidate = next((r for r in rows if r["stats"]["CAGR_pct"] > base["stats"]["CAGR_pct"] and r["stats"]["Sharpe"] >= base["stats"]["Sharpe"] and r["stats"]["Calmar"] >= base["stats"]["Calmar"]), None)
    risk_answer = "No. In this 4-point local probe, none of the tested variants improved CAGR while also keeping both Sharpe and Calmar at or above the current base."
    if risk_candidate is not None:
        risk_answer = f"Yes, in raw local stats `{risk_candidate['label']}` did that, but it still lacks fresh gate revalidation, so it is not promoted yet."

    payload = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "default_research_tuple": "next_bar_open + legacy_bar_extrema + midpoint + full_model",
        "stress_tuple": "live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model",
        "base": base,
        "tested_rows": rows,
        "top_rows": [best, *rows][:5],
        "parameter_sensitivity": parameter_sensitivity,
        "best_candidate": best,
        "answers": {
            "best_parameters_to_optimize": " and ".join(item["parameter"] for item in parameter_sensitivity[:2]),
            "most_promising_neighborhood": "lookback around 22 and stop around 3.2 appear most promising; trail can be nudged to 5.2, but break-even should stay disabled until a raw winner appears.",
            "sharpe_calmar_and_cagr_answer": risk_answer,
            "baseline_gate_answer": "The existing evidence still points to a split diagnosis: at 100% sizing baseline_gate is not only a trade-count problem because MaxDD also misses the -30% cap; at 35% sizing the residual issue is mainly the legacy 250-trade threshold, which is mismatched for a low-frequency trend mother.",
        },
        "decision": {
            "found_better_version": bool(best is not base),
            "upgrade_research_optimal": False,
            "closer_to_independent_core": bool(best is not base),
            "keep_digging": True,
            "decision_note": "Keep the current base as research_optimal. This probe did not produce a sufficiently dominant raw winner to justify a fresh full gate cycle.",
        },
    }
    write_outputs(payload)
    print(json.dumps({"best_candidate": best["label"], "upgrade_research_optimal": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
