#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight re-evaluation under the new intrabar default."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from universal_data_updater_5m import DataLoader5m
from v85_intrabar_backtest import V85Params
from v85_research_suite_v2 import ensure_datetime, realistic_research_params, run_backtest, run_gatekeeper_v2


def scheme_params(position_pct: float) -> V85Params:
    base = V85Params(
        position_pct=position_pct,
        initial_stop_atr=2.6,
        trail_start_atr=3.2,
        trail_offset_atr=2.6,
        tp1_atr=2.4,
        tp2_atr=4.0,
        adx_trend_level=24,
        squeeze_threshold=0.85,
        min_squeeze_candles=4,
        min_long_score=1,
        min_short_score=3,
        enable_partial_tp=False,
        enable_short=True,
        short_only_bear=True,
    )
    return realistic_research_params(base)


def compact(stats: dict) -> dict:
    return {
        "Return_pct": round(float(stats.get("TotalReturn_pct", 0.0)), 6),
        "CAGR_pct": round(float(stats.get("CAGR", 0.0)) * 100.0, 6),
        "Sharpe": round(float(stats.get("Sharpe", 0.0)), 6),
        "MaxDD_pct": round(float(stats.get("MaxDD_pct", 0.0)) * 100.0, 6),
        "PF": round(float(stats.get("ProfitFactor", 0.0)), 6),
        "Trades": int(stats.get("Trades", 0)),
    }


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    launch = scheme_params(25.0)
    research = scheme_params(60.0)

    launch_baseline = run_backtest(df_5m, df_4h, launch, True)
    research_baseline = run_backtest(df_5m, df_4h, research, True)
    launch_gate = run_gatekeeper_v2(df_5m, df_4h, launch, Path("."))

    report = {
        "generated_at_local": datetime.now().isoformat(),
        "default_tuple": {
            "entry_execution_mode": launch.entry_execution_mode,
            "intrabar_execution_model": launch.intrabar_execution_model,
            "intrabar_path_mode": launch.intrabar_path_mode,
            "slippage_fixed_bps": launch.slippage_fixed_bps,
            "slippage_breakout_extra_bps": launch.slippage_breakout_extra_bps,
            "slippage_stop_extra_bps": launch.slippage_stop_extra_bps,
            "slippage_range_weight": launch.slippage_range_weight,
            "slippage_max_bps": launch.slippage_max_bps,
        },
        "launch_optimal_redefault": {
            "params": asdict(launch),
            "baseline": compact(launch_baseline["stats"]),
            "gate_summary": launch_gate["gate_summary"],
            "final_pass": bool(launch_gate["final_pass"]),
        },
        "research_optimal_redefault": {
            "params": asdict(research),
            "baseline": compact(research_baseline["stats"]),
        },
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir = Path("data") / f"intrabar_redefault_reval_{ts}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = [
        "# Intrabar Redefault Re-evaluation",
        "",
        f"- default_tuple: {launch.entry_execution_mode}+{launch.intrabar_execution_model}+{launch.intrabar_path_mode}+full_model",
        f"- launch_final_pass: {report['launch_optimal_redefault']['final_pass']}",
        f"- launch_baseline: {json.dumps(report['launch_optimal_redefault']['baseline'], ensure_ascii=False)}",
        f"- launch_gate_summary: {json.dumps(report['launch_optimal_redefault']['gate_summary'], ensure_ascii=False)}",
        f"- research_baseline: {json.dumps(report['research_optimal_redefault']['baseline'], ensure_ascii=False)}",
        "",
    ]
    (outdir / "summary.md").write_text("\n".join(summary), encoding="utf-8")
    Path("intrabar_redefault_reval.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    Path("intrabar_redefault_summary.txt").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
