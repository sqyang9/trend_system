#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v85_research_suite_v2.py
Gatekeeper V2 and realistic pre-live research utilities.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import inspect
import io
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_intrabar_backtest import IntrabarBacktestEngine, V85Params
from v85_live_execution import PaperExecutionAdapter, ProtectionRequest, PositionSnapshot
from v85_order_reconcile import reconcile_state
from v85_state_recovery import JSONStateStore


def ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    return out.sort_values("timestamp").reset_index(drop=True)


def with_overrides(params: V85Params, **overrides) -> V85Params:
    data = asdict(params)
    data.update(overrides)
    return V85Params(**data)


def realistic_research_params(base: V85Params | None = None) -> V85Params:
    params = base or V85Params()
    return with_overrides(
        params,
        # Daily research default: causal but not overly harsh.
        entry_execution_mode="next_bar_open",
        intrabar_path_mode="midpoint",
        intrabar_execution_model="legacy_bar_extrema",
        slippage_fixed_bps=max(float(params.slippage_fixed_bps), 5.0),
        slippage_breakout_extra_bps=max(float(params.slippage_breakout_extra_bps), 5.0),
        slippage_stop_extra_bps=max(float(params.slippage_stop_extra_bps), 8.0),
        slippage_range_weight=max(float(params.slippage_range_weight), 0.05),
        slippage_max_bps=max(float(params.slippage_max_bps), 25.0),
    )


def run_backtest(
    df_5m: pd.DataFrame,
    df_4h: pd.DataFrame,
    params: V85Params,
    use_intrabar: bool,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> Dict:
    d5 = ensure_datetime(df_5m)
    d4 = ensure_datetime(df_4h)
    if start is not None:
        d5 = d5[d5["timestamp"] >= start]
        d4 = d4[d4["timestamp"] >= start]
    if end is not None:
        d5 = d5[d5["timestamp"] < end]
        d4 = d4[d4["timestamp"] < end]
    engine = IntrabarBacktestEngine(params, use_intrabar_stop=use_intrabar)
    with contextlib.redirect_stdout(io.StringIO()):
        return engine.run(d5.reset_index(drop=True), d4.reset_index(drop=True))


def intrabar_behavior_stats(result: Dict) -> Dict:
    trades = result.get("trades")
    if trades is None or trades.empty:
        return {
            "unique_entries": 0,
            "avg_legs_per_entry": 0.0,
            "avg_hold_5m_bars": 0.0,
            "avg_hold_4h_bars": 0.0,
            "median_hold_5m_bars": 0.0,
            "exit_mix": {},
            "pnl_quantiles": {},
        }
    df = trades.copy()
    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)
    df["exit_time"] = pd.to_datetime(df["exit_time"], utc=True)
    hold_minutes = (df["exit_time"] - df["entry_time"]).dt.total_seconds() / 60.0
    entry_groups = df.groupby(["entry_time", "direction", "entry_price"], dropna=False)["pnl"].sum().reset_index(name="entry_pnl")
    legs_per_entry = float(len(df) / len(entry_groups)) if len(entry_groups) > 0 else 0.0
    pnl_quantiles = df["pnl"].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).to_dict()
    return {
        "unique_entries": int(len(entry_groups)),
        "avg_legs_per_entry": legs_per_entry,
        "avg_hold_5m_bars": float((hold_minutes / 5.0).mean()) if len(df) > 0 else 0.0,
        "avg_hold_4h_bars": float((hold_minutes / 240.0).mean()) if len(df) > 0 else 0.0,
        "median_hold_5m_bars": float((hold_minutes / 5.0).median()) if len(df) > 0 else 0.0,
        "exit_mix": df["exit_reason"].value_counts(normalize=True).to_dict(),
        "pnl_quantiles": {str(k): float(v) for k, v in pnl_quantiles.items()},
    }


def compare_intrabar_models(
    df_5m: pd.DataFrame,
    df_4h: pd.DataFrame,
    base_params: V85Params,
    scenarios: Iterable[Dict],
    use_intrabar: bool = True,
) -> List[Dict]:
    rows: List[Dict] = []
    for scenario in scenarios:
        name = str(scenario.get("name", "scenario"))
        overrides = dict(scenario.get("overrides", {}))
        params = with_overrides(base_params, **overrides)
        result = run_backtest(df_5m, df_4h, params, use_intrabar)
        stats = result["stats"]
        rows.append(
            {
                "name": name,
                "config": asdict(params),
                "stats": stats,
                "behavior": intrabar_behavior_stats(result),
            }
        )
    return rows


def data_quality_check(df: pd.DataFrame, tf_minutes: int, name: str) -> Dict:
    ts = pd.to_datetime(df["timestamp"], utc=True).sort_values().reset_index(drop=True)
    diffs = ts.diff().dt.total_seconds() / 60.0
    non_standard = diffs[(diffs.notna()) & (np.abs(diffs - tf_minutes) > 1e-9)]
    now_utc = pd.Timestamp.now(tz="UTC")
    recency_days = float((now_utc - ts.iloc[-1]).total_seconds() / 86400.0)
    result = {
        "name": name,
        "rows": int(len(df)),
        "start": str(ts.iloc[0]),
        "end": str(ts.iloc[-1]),
        "duplicates": int(df.duplicated(subset=["timestamp"]).sum()),
        "monotonic": bool(ts.is_monotonic_increasing),
        "non_standard_interval_count": int(len(non_standard)),
        "recency_days": recency_days,
    }
    result["pass"] = result["duplicates"] == 0 and result["monotonic"] and result["non_standard_interval_count"] == 0 and recency_days <= 2.0
    return result


def reproducibility_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params) -> Dict:
    r1 = run_backtest(df_5m, df_4h, params, True)
    r2 = run_backtest(df_5m, df_4h, params, True)
    keys = ["FinalEquity", "TotalReturn_pct", "CAGR", "Sharpe", "MaxDD_pct", "ProfitFactor", "Trades", "WinRate_pct"]
    diffs = {k: abs(float(r1["stats"].get(k, 0.0)) - float(r2["stats"].get(k, 0.0))) for k in keys}
    return {"max_stat_diff": max(diffs.values()) if diffs else 0.0, "same_trade_count": len(r1["trades"]) == len(r2["trades"]), "pass": bool((max(diffs.values()) if diffs else 0.0) < 1e-10 and len(r1["trades"]) == len(r2["trades"])), "baseline_stats": r1["stats"]}


def baseline_gate(stats: Dict) -> Dict:
    sharpe = float(stats.get("Sharpe", 0.0))
    maxdd = float(stats.get("MaxDD_pct", 0.0))
    pf = float(stats.get("ProfitFactor", 0.0))
    trades = int(stats.get("Trades", 0))
    passed = (sharpe >= 0.80) and (maxdd >= -0.30) and (pf >= 1.15) and (trades >= 250)
    return {"Sharpe": sharpe, "MaxDD_pct": maxdd, "ProfitFactor": pf, "Trades": trades, "pass": passed}


def yearly_eval(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params | None = None) -> Dict:
    params = params or realistic_research_params()
    years = sorted(ensure_datetime(df_4h)["timestamp"].dt.year.unique().tolist())
    rows = []
    for year in years:
        start = pd.Timestamp(f"{year}-01-01", tz="UTC")
        end = pd.Timestamp(f"{year + 1}-01-01", tz="UTC")
        sub = ensure_datetime(df_4h)
        sub = sub[(sub["timestamp"] >= start) & (sub["timestamp"] < end)]
        if len(sub) < 180:
            continue
        result = run_backtest(df_5m, df_4h, params, True, start, end)
        stats = result["stats"]
        rows.append({"year": int(year), "CAGR": float(stats.get("CAGR", 0.0)), "Sharpe": float(stats.get("Sharpe", 0.0)), "MaxDD_pct": float(stats.get("MaxDD_pct", 0.0)), "Trades": int(stats.get("Trades", 0)), "Return_pct": float(stats.get("TotalReturn_pct", 0.0))})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_year_data"}
    positive_year_ratio = float((df["CAGR"] > 0).mean())
    avg_sharpe = float(df["Sharpe"].mean())
    worst_return = float(df["Return_pct"].min())
    passed = (positive_year_ratio >= 0.60) and (avg_sharpe >= 0.40) and (worst_return > -35.0)
    return {"rows": rows, "positive_year_ratio": positive_year_ratio, "avg_sharpe": avg_sharpe, "worst_return_pct": worst_return, "pass": passed}

def rolling_oos_eval(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params | None = None, train_years: int = 2) -> Dict:
    params = params or realistic_research_params()
    years = sorted(ensure_datetime(df_4h)["timestamp"].dt.year.unique().tolist())
    rows = []
    for oos_year in years:
        train_set = [y for y in years if (oos_year - train_years) <= y < oos_year]
        if len(train_set) < train_years:
            continue
        start = pd.Timestamp(f"{oos_year}-01-01", tz="UTC")
        end = pd.Timestamp(f"{oos_year + 1}-01-01", tz="UTC")
        sub = ensure_datetime(df_4h)
        sub = sub[(sub["timestamp"] >= start) & (sub["timestamp"] < end)]
        if len(sub) < 180:
            continue
        result = run_backtest(df_5m, df_4h, params, True, start, end)
        stats = result["stats"]
        rows.append({"oos_year": int(oos_year), "train_years": train_set, "Sharpe": float(stats.get("Sharpe", 0.0)), "CAGR": float(stats.get("CAGR", 0.0)), "Return_pct": float(stats.get("TotalReturn_pct", 0.0)), "Trades": int(stats.get("Trades", 0))})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_oos_data"}
    avg_sharpe = float(df["Sharpe"].mean())
    positive_ratio = float((df["CAGR"] > 0).mean())
    passed = (avg_sharpe >= 0.30) and (positive_ratio >= 0.55)
    return {"rows": rows, "avg_sharpe": avg_sharpe, "positive_ratio": positive_ratio, "pass": passed}


def regime_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params | None = None) -> Dict:
    params = params or realistic_research_params()
    regimes = [("bull_2020_2021", "2020-01-01", "2022-01-01"), ("bear_2022", "2022-01-01", "2023-01-01"), ("mixed_2023_2025", "2023-01-01", "2026-01-01")]
    rows = []
    for name, start_text, end_text in regimes:
        start = pd.Timestamp(start_text, tz="UTC")
        end = pd.Timestamp(end_text, tz="UTC")
        sub = ensure_datetime(df_4h)
        sub = sub[(sub["timestamp"] >= start) & (sub["timestamp"] < end)]
        if len(sub) < 180:
            continue
        result = run_backtest(df_5m, df_4h, params, True, start, end)
        stats = result["stats"]
        rows.append({"regime": name, "Return_pct": float(stats.get("TotalReturn_pct", 0.0)), "Sharpe": float(stats.get("Sharpe", 0.0)), "MaxDD_pct": float(stats.get("MaxDD_pct", 0.0)), "Trades": int(stats.get("Trades", 0))})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_regimes"}
    passed = bool((df["Return_pct"] > -35.0).all() and (df["MaxDD_pct"] > -0.40).all())
    return {"rows": rows, "pass": passed}


def cost_stress_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params | None = None) -> Dict:
    params = params or realistic_research_params()
    commissions = [0.06, 0.10, 0.15, 0.20]
    rows = []
    for commission in commissions:
        scenario = with_overrides(params, commission_pct=commission)
        result = run_backtest(df_5m, df_4h, scenario, True)
        stats = result["stats"]
        rows.append({"commission_pct": commission, "Return_pct": float(stats.get("TotalReturn_pct", 0.0)), "Sharpe": float(stats.get("Sharpe", 0.0)), "MaxDD_pct": float(stats.get("MaxDD_pct", 0.0))})
    df = pd.DataFrame(rows)
    worst = df.iloc[-1]
    passed = (float(worst["Return_pct"]) > 0.0) and (float(worst["Sharpe"]) >= 0.25) and (float(worst["MaxDD_pct"]) >= -0.35)
    return {"rows": rows, "pass": passed}


def slippage_stress_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params | None = None) -> Dict:
    params = params or realistic_research_params()
    scenarios = [
        ("research_default", {}),
        ("fixed_10", {"slippage_fixed_bps": 10.0, "slippage_breakout_extra_bps": 5.0, "slippage_stop_extra_bps": 10.0, "slippage_range_weight": 0.05, "slippage_max_bps": 30.0}),
        ("fixed_15", {"slippage_fixed_bps": 15.0, "slippage_breakout_extra_bps": 10.0, "slippage_stop_extra_bps": 15.0, "slippage_range_weight": 0.08, "slippage_max_bps": 40.0}),
    ]
    rows = []
    for name, overrides in scenarios:
        scenario = with_overrides(params, **overrides)
        result = run_backtest(df_5m, df_4h, scenario, True)
        stats = result["stats"]
        rows.append({"scenario": name, "Return_pct": float(stats.get("TotalReturn_pct", 0.0)), "Sharpe": float(stats.get("Sharpe", 0.0)), "MaxDD_pct": float(stats.get("MaxDD_pct", 0.0))})
    df = pd.DataFrame(rows)
    worst = df.iloc[-1]
    passed = (float(worst["Return_pct"]) > -20.0) and (float(worst["Sharpe"]) >= 0.0) and (float(worst["MaxDD_pct"]) >= -0.40)
    return {"rows": rows, "pass": passed}


def execution_mode_stress_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params | None = None) -> Dict:
    params = params or realistic_research_params()
    modes = ["next_bar_open", "close_plus_delay_bps", "live_runner_next_5m_close"]
    rows = []
    for mode in modes:
        scenario = with_overrides(params, entry_execution_mode=mode)
        result = run_backtest(df_5m, df_4h, scenario, True)
        stats = result["stats"]
        rows.append({"mode": mode, "Return_pct": float(stats.get("TotalReturn_pct", 0.0)), "Sharpe": float(stats.get("Sharpe", 0.0)), "MaxDD_pct": float(stats.get("MaxDD_pct", 0.0))})
    df = pd.DataFrame(rows)
    passed = bool((df["Return_pct"] > -25.0).all() and (df["MaxDD_pct"] > -0.40).all())
    return {"rows": rows, "pass": passed}


def intrabar_path_stress_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params | None = None) -> Dict:
    params = params or realistic_research_params()
    modes = ["pessimistic", "midpoint", "volatility_aware", "optimistic"]
    rows = []
    for mode in modes:
        scenario = with_overrides(params, intrabar_path_mode=mode)
        result = run_backtest(df_5m, df_4h, scenario, True)
        stats = result["stats"]
        rows.append({"mode": mode, "Return_pct": float(stats.get("TotalReturn_pct", 0.0)), "Sharpe": float(stats.get("Sharpe", 0.0)), "MaxDD_pct": float(stats.get("MaxDD_pct", 0.0))})
    df = pd.DataFrame(rows)
    pessimistic_row = df[df["mode"] == "pessimistic"].iloc[0]
    passed = (float(pessimistic_row["Return_pct"]) > -25.0) and (float(pessimistic_row["MaxDD_pct"]) > -0.40)
    return {"rows": rows, "pass": passed}


def live_safety_check(workdir: Path) -> Dict:
    importlib.invalidate_caches()
    live_exec = importlib.import_module("v85_live_execution")
    runner = importlib.import_module("v85_live_runner")
    runner_impl = importlib.import_module("v85_live_runner_v2")
    state = importlib.import_module("v85_state_recovery")

    adapter = PaperExecutionAdapter()
    protection = adapter.place_protection(ProtectionRequest(symbol="BTC/USDT:USDT", side="sell", amount=0.1, stop_trigger_price=50000.0))
    amended = adapter.amend_protection(protection.protection_id, ProtectionRequest(symbol="BTC/USDT:USDT", side="sell", amount=0.1, stop_trigger_price=49000.0))
    cancelled = adapter.cancel_protection(protection.protection_id, "BTC/USDT:USDT")

    tmp_state = workdir / "data" / "gatekeeper_v2_state_tmp.json"
    store = JSONStateStore(tmp_state)
    store.upsert_position("BTC/USDT:USDT", 0.1, "long", 60000.0)
    report = reconcile_state(store.load(), [PositionSnapshot(symbol="BTC/USDT:USDT", side="long", contracts=0.1, entry_price=60000.0, unrealized_pnl=0.0, raw={})], [], [])
    if tmp_state.exists():
        tmp_state.unlink()

    checks = {
        "has_protection_interface": all(hasattr(live_exec.ExecutionAdapter, name) for name in ["place_protection", "amend_protection", "cancel_protection", "fetch_protection_orders"]),
        "paper_protection_roundtrip": bool(protection.protection_id and amended.status and cancelled),
        "state_has_protection_bucket": "protection_orders" in state.JSONStateStore.default_state(),
        "state_has_strategy_targets": "strategy_targets" in state.JSONStateStore.default_state(),
        "runner_has_native_protection_sync": hasattr(runner_impl, "sync_native_protection"),
        "runner_has_kill_switch_mode": ("kill_switch_mode" in inspect.getsource(runner_impl)) if hasattr(runner_impl, "main") else True,
        "reconcile_detects_missing_protection": any(a.action == "missing_protection" for a in report.actions),
    }
    checks["pass"] = all(checks.values())
    return checks

def engineering_gate(workdir: Path) -> Dict:
    names = {p.name.lower() for p in workdir.glob("*.py")}
    checks = {
        "has_live_execution_module": any("live_execution" in n for n in names),
        "has_kill_switch_module": any("risk" in n or "kill" in n for n in names),
        "has_state_recovery_module": any("state" in n or "recovery" in n for n in names),
        "has_reconcile_module": any("reconcile" in n for n in names),
    }
    checks["pass"] = all(checks.values())
    return checks


def run_gatekeeper_v2(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params, workdir: Path) -> Dict:
    params = realistic_research_params(params)
    baseline = run_backtest(df_5m, df_4h, params, True)
    report = {
        "baseline_gate": baseline_gate(baseline["stats"]),
        "yearly": yearly_eval(df_5m, df_4h, params),
        "rolling_oos": rolling_oos_eval(df_5m, df_4h, params),
        "regime": regime_test(df_5m, df_4h, params),
        "cost_stress": cost_stress_test(df_5m, df_4h, params),
        "slippage_stress": slippage_stress_test(df_5m, df_4h, params),
        "execution_mode_stress": execution_mode_stress_test(df_5m, df_4h, params),
        "intrabar_path_stress": intrabar_path_stress_test(df_5m, df_4h, params),
        "live_safety_check": live_safety_check(workdir),
        "engineering_gate": engineering_gate(workdir),
        "baseline_stats": baseline["stats"],
        "params": asdict(params),
    }
    gate_summary = {name: bool(report[name].get("pass", False)) for name in ["baseline_gate", "yearly", "rolling_oos", "regime", "cost_stress", "slippage_stress", "execution_mode_stress", "intrabar_path_stress", "live_safety_check"]}
    report["gate_summary"] = gate_summary
    report["final_pass"] = all(gate_summary.values())
    return report


def write_markdown(report: Dict, md_path: Path) -> None:
    lines = ["# Gatekeeper V2 Report", "", f"- FinalPass: {'PASS' if report['final_pass'] else 'FAIL'}", f"- Sharpe: {report['baseline_stats']['Sharpe']:.3f}", f"- MaxDD: {report['baseline_stats']['MaxDD_pct'] * 100.0:.2f}%", f"- Trades: {report['baseline_stats']['Trades']}", "", "## Gate Summary"]
    for key, value in report["gate_summary"].items():
        lines.append(f"- {key}: {'PASS' if value else 'FAIL'}")
    md_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="V85 realistic pre-live research suite")
    ap.add_argument("--data_dir", default="./data")
    ap.add_argument("--outdir", default=None)
    args = ap.parse_args()

    loader = DataLoader5m(args.data_dir)
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    params = realistic_research_params()
    report = run_gatekeeper_v2(df_5m, df_4h, params, Path("."))

    outdir = Path(args.outdir) if args.outdir else Path(args.data_dir) / f"gatekeeper_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report, outdir / "summary.md")
    print(json.dumps({"final_pass": report["final_pass"], "gate_summary": report["gate_summary"]}, indent=2, ensure_ascii=False))


__all__ = [
    "ensure_datetime",
    "with_overrides",
    "realistic_research_params",
    "run_backtest",
    "data_quality_check",
    "reproducibility_test",
    "baseline_gate",
    "yearly_eval",
    "rolling_oos_eval",
    "regime_test",
    "cost_stress_test",
    "slippage_stress_test",
    "execution_mode_stress_test",
    "intrabar_path_stress_test",
    "live_safety_check",
    "engineering_gate",
    "run_gatekeeper_v2",
    "write_markdown",
    "main",
]


if __name__ == "__main__":
    main()




