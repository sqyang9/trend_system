#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v85_prelive_research_suite.py
=============================
基于现有历史数据执行实盘前研发测试（离线）

覆盖：
1. 数据质量与时效性
2. 回测复现性
3. 基线表现（盘中止损 / 收盘止损）
4. 年度稳健性
5. 滚动样本外评估（固定参数）
6. 蒙特卡洛（Block Bootstrap）
7. 参数敏感性
8. 手续费压力测试
9. 市场状态（Regime）测试
10. 工程上线门禁（静态检查）
"""

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_intrabar_backtest import V85Params, IntrabarBacktestEngine


def ensure_datetime(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    return out


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
        "expected_interval_min": tf_minutes,
        "non_standard_interval_count": int(len(non_standard)),
        "max_gap_min": float(non_standard.max()) if len(non_standard) else float(tf_minutes),
        "recency_days": recency_days,
    }

    # 实盘门禁：必须新鲜（<= 2天）
    result["pass"] = (
        result["duplicates"] == 0
        and result["monotonic"]
        and result["non_standard_interval_count"] == 0
        and recency_days <= 2.0
    )
    return result


def run_backtest(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params, use_intrabar: bool,
                 start: pd.Timestamp = None, end: pd.Timestamp = None) -> Dict:
    d5 = df_5m.copy()
    d4 = df_4h.copy()

    if start is not None:
        d5 = d5[d5["timestamp"] >= start]
        d4 = d4[d4["timestamp"] >= start]
    if end is not None:
        d5 = d5[d5["timestamp"] < end]
        d4 = d4[d4["timestamp"] < end]

    d5 = d5.reset_index(drop=True)
    d4 = d4.reset_index(drop=True)

    engine = IntrabarBacktestEngine(params, use_intrabar_stop=use_intrabar)
    return engine.run(d5, d4)


def reproducibility_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
    p = V85Params()
    r1 = run_backtest(df_5m, df_4h, p, True)
    r2 = run_backtest(df_5m, df_4h, p, True)

    keys = ["FinalEquity", "TotalReturn_pct", "CAGR", "Sharpe", "MaxDD_pct", "ProfitFactor", "Trades", "WinRate_pct"]
    diffs = {}
    for k in keys:
        v1 = float(r1["stats"].get(k, 0.0))
        v2 = float(r2["stats"].get(k, 0.0))
        diffs[k] = abs(v1 - v2)

    max_diff = max(diffs.values()) if diffs else 0.0
    same_trade_count = len(r1["trades"]) == len(r2["trades"])

    return {
        "max_stat_diff": max_diff,
        "same_trade_count": same_trade_count,
        "pass": bool(max_diff < 1e-10 and same_trade_count),
        "baseline_stats": r1["stats"],
    }


def baseline_gate(stats: Dict) -> Dict:
    sharpe = float(stats.get("Sharpe", 0.0))
    maxdd = float(stats.get("MaxDD_pct", 0.0))
    pf = float(stats.get("ProfitFactor", 0.0))
    trades = int(stats.get("Trades", 0))

    passed = (sharpe >= 1.0) and (maxdd >= -0.30) and (pf >= 1.2) and (trades >= 300)
    return {
        "Sharpe": sharpe,
        "MaxDD_pct": maxdd,
        "ProfitFactor": pf,
        "Trades": trades,
        "pass": passed,
    }


def yearly_eval(df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
    years = sorted(df_4h["timestamp"].dt.year.unique().tolist())
    p = V85Params()
    rows = []

    for y in years:
        s = pd.Timestamp(f"{y}-01-01", tz="UTC")
        e = pd.Timestamp(f"{y+1}-01-01", tz="UTC")
        sub = df_4h[(df_4h["timestamp"] >= s) & (df_4h["timestamp"] < e)]
        if len(sub) < 180:
            continue
        r = run_backtest(df_5m, df_4h, p, True, s, e)
        st = r["stats"]
        rows.append({
            "year": int(y),
            "CAGR": float(st.get("CAGR", 0.0)),
            "Sharpe": float(st.get("Sharpe", 0.0)),
            "MaxDD_pct": float(st.get("MaxDD_pct", 0.0)),
            "Trades": int(st.get("Trades", 0)),
            "Return_pct": float(st.get("TotalReturn_pct", 0.0)),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_year_data"}

    positive_year_ratio = float((df["CAGR"] > 0).mean())
    avg_sharpe = float(df["Sharpe"].mean())
    worst_return = float(df["Return_pct"].min())

    passed = (positive_year_ratio >= 0.70) and (avg_sharpe >= 0.70) and (worst_return > -30)
    return {
        "rows": rows,
        "positive_year_ratio": positive_year_ratio,
        "avg_sharpe": avg_sharpe,
        "worst_return_pct": worst_return,
        "pass": passed,
    }


def rolling_oos_eval(df_5m: pd.DataFrame, df_4h: pd.DataFrame, train_years: int = 2) -> Dict:
    years = sorted(df_4h["timestamp"].dt.year.unique().tolist())
    p = V85Params()
    rows = []

    for oos_year in years:
        train_set = [y for y in years if (oos_year - train_years) <= y < oos_year]
        if len(train_set) < train_years:
            continue

        s = pd.Timestamp(f"{oos_year}-01-01", tz="UTC")
        e = pd.Timestamp(f"{oos_year+1}-01-01", tz="UTC")
        sub = df_4h[(df_4h["timestamp"] >= s) & (df_4h["timestamp"] < e)]
        if len(sub) < 180:
            continue

        r = run_backtest(df_5m, df_4h, p, True, s, e)
        st = r["stats"]
        rows.append({
            "oos_year": int(oos_year),
            "train_years": train_set,
            "Sharpe": float(st.get("Sharpe", 0.0)),
            "CAGR": float(st.get("CAGR", 0.0)),
            "Return_pct": float(st.get("TotalReturn_pct", 0.0)),
            "Trades": int(st.get("Trades", 0)),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_oos_data"}

    avg_sharpe = float(df["Sharpe"].mean())
    positive_ratio = float((df["CAGR"] > 0).mean())
    passed = (avg_sharpe >= 0.5) and (positive_ratio >= 0.6)

    return {
        "rows": rows,
        "avg_sharpe": avg_sharpe,
        "positive_ratio": positive_ratio,
        "pass": passed,
    }


def monte_carlo_from_trades(trades: pd.DataFrame, span_years: float, n_sims: int = 1500, block_size: int = 3) -> Dict:
    if trades.empty:
        return {"pass": False, "reason": "no_trades"}

    init_equity = 10000.0
    pnl = trades["pnl"].values

    equity = init_equity
    returns = []
    for p in pnl:
        if equity > 0:
            returns.append(p / equity)
        equity += p
    returns = np.asarray(returns)

    if len(returns) == 0:
        return {"pass": False, "reason": "empty_returns"}

    np.random.seed(42)
    m = len(returns)
    cagrs = np.empty(n_sims)
    maxdds = np.empty(n_sims)

    for i in range(n_sims):
        seq = []
        while len(seq) < m:
            start = np.random.randint(0, max(1, m - block_size + 1))
            seq.extend(returns[start:start + block_size])
        seq = np.asarray(seq[:m])

        eq = np.empty(m + 1)
        eq[0] = init_equity
        for j, r in enumerate(seq):
            eq[j + 1] = eq[j] * (1.0 + r)

        ratio = max(eq[-1] / init_equity, 1e-12)
        cagrs[i] = (ratio ** (1.0 / max(span_years, 1e-6))) - 1.0

        peak = eq[0]
        max_dd = 0.0
        for v in eq:
            peak = max(peak, v)
            dd = (v / peak - 1.0) if peak > 0 else 0.0
            max_dd = min(max_dd, dd)
        maxdds[i] = max_dd

    out = {
        "cagr_p05": float(np.percentile(cagrs, 5)),
        "cagr_p50": float(np.percentile(cagrs, 50)),
        "cagr_p95": float(np.percentile(cagrs, 95)),
        "maxdd_p50": float(np.percentile(maxdds, 50)),
        "maxdd_p95": float(np.percentile(maxdds, 95)),
        "prob_positive": float(np.mean(cagrs > 0)),
    }
    out["pass"] = (out["cagr_p05"] > 0) and (out["prob_positive"] >= 0.8)
    return out


def sensitivity_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
    scenarios = []

    def add(param: str, values: List):
        for v in values:
            scenarios.append((f"{param}={v}", {param: v}))

    add("initial_stop_atr", [2.0, 2.8])
    add("trail_start_atr", [2.5, 3.5])
    add("trail_offset_atr", [2.4, 3.2])
    add("tp1_atr", [1.8, 2.4])
    add("tp2_atr", [3.0, 4.0])
    add("position_pct", [40.0, 80.0])
    add("min_long_score", [2])
    add("min_short_score", [2, 4])

    rows = []
    for name, kv in scenarios:
        p = V85Params(**kv)
        r = run_backtest(df_5m, df_4h, p, True)
        st = r["stats"]
        rows.append({
            "scenario": name,
            "Return_pct": float(st.get("TotalReturn_pct", 0.0)),
            "Sharpe": float(st.get("Sharpe", 0.0)),
            "MaxDD_pct": float(st.get("MaxDD_pct", 0.0)),
            "Trades": int(st.get("Trades", 0)),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_scenarios"}

    robust_ratio = float(((df["Return_pct"] > 0) & (df["Sharpe"] > 0.5)).mean())
    worst_return = float(df["Return_pct"].min())
    pass_flag = (robust_ratio >= 0.75) and (worst_return > -30)

    return {
        "rows": rows,
        "robust_ratio": robust_ratio,
        "worst_return_pct": worst_return,
        "pass": pass_flag,
    }


def cost_stress_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
    commissions = [0.06, 0.10, 0.15, 0.20]
    rows = []
    for c in commissions:
        p = V85Params(commission_pct=c)
        r = run_backtest(df_5m, df_4h, p, True)
        st = r["stats"]
        rows.append({
            "commission_pct": c,
            "Return_pct": float(st.get("TotalReturn_pct", 0.0)),
            "Sharpe": float(st.get("Sharpe", 0.0)),
            "MaxDD_pct": float(st.get("MaxDD_pct", 0.0)),
        })

    df = pd.DataFrame(rows)
    worst = df.iloc[-1]
    pass_flag = (float(worst["Return_pct"]) > 0) and (float(worst["Sharpe"]) >= 0.5) and (float(worst["MaxDD_pct"]) >= -0.35)

    return {
        "rows": rows,
        "pass": bool(pass_flag),
    }


def regime_test(df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
    regimes = [
        ("bull_2020_2021", "2020-01-01", "2022-01-01"),
        ("bear_2022", "2022-01-01", "2023-01-01"),
        ("mixed_2023_2025", "2023-01-01", "2026-01-01"),
    ]
    rows = []
    p = V85Params()

    for name, s, e in regimes:
        s_ts = pd.Timestamp(s, tz="UTC")
        e_ts = pd.Timestamp(e, tz="UTC")
        sub = df_4h[(df_4h["timestamp"] >= s_ts) & (df_4h["timestamp"] < e_ts)]
        if len(sub) < 180:
            continue
        r = run_backtest(df_5m, df_4h, p, True, s_ts, e_ts)
        st = r["stats"]
        rows.append({
            "regime": name,
            "Return_pct": float(st.get("TotalReturn_pct", 0.0)),
            "Sharpe": float(st.get("Sharpe", 0.0)),
            "MaxDD_pct": float(st.get("MaxDD_pct", 0.0)),
            "Trades": int(st.get("Trades", 0)),
        })

    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_regimes"}

    pass_flag = bool((df["Return_pct"] > -30).all() and (df["MaxDD_pct"] > -0.35).all())
    return {
        "rows": rows,
        "pass": pass_flag,
    }


def engineering_gate(workdir: Path) -> Dict:
    py_files = list(workdir.glob("*.py"))
    names = {p.name.lower() for p in py_files}

    has_live_exec = any("live" in n and ("trade" in n or "exec" in n or "order" in n) for n in names)
    has_kill_switch = any("kill" in n or "risk" in n for n in names)
    has_state_store = any("state" in n or "checkpoint" in n or "recovery" in n for n in names)
    has_recon = any("reconcile" in n or "sync" in n for n in names)

    checks = {
        "has_live_execution_module": has_live_exec,
        "has_kill_switch_or_runtime_risk_module": has_kill_switch,
        "has_state_recovery_module": has_state_store,
        "has_order_reconciliation_module": has_recon,
    }
    checks["pass"] = all(checks.values())
    return checks


def write_markdown(report: Dict, md_path: Path):
    lines = []
    lines.append("# V85 Prelive Research Report")
    lines.append("")
    lines.append(f"- GeneratedAtUTC: {report['meta']['generated_at_utc']}")
    lines.append(f"- DataRange5m: {report['meta']['data_5m_start']} -> {report['meta']['data_5m_end']}")
    lines.append(f"- DataRange4h: {report['meta']['data_4h_start']} -> {report['meta']['data_4h_end']}")
    lines.append("")
    lines.append("## Gate Summary")
    for k, v in report["gate_summary"].items():
        lines.append(f"- {k}: {'PASS' if v else 'FAIL'}")
    lines.append("")
    lines.append(f"## Final Verdict")
    lines.append(f"- {report['final_verdict']}")
    lines.append("")
    lines.append("## Key Findings")
    for item in report["key_findings"]:
        lines.append(f"- {item}")

    md_path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="V85 实盘前研发测试（基于现有数据）")
    ap.add_argument("--data_dir", default="./data")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--mc_n", type=int, default=1500)
    args = ap.parse_args()

    outdir = Path(args.outdir) if args.outdir else Path(args.data_dir) / f"v85_prelive_research_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    outdir.mkdir(parents=True, exist_ok=True)

    loader = DataLoader5m(args.data_dir)
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    print("[1/10] 数据质量检查...")
    dq_5m = data_quality_check(df_5m, 5, "5m")
    dq_4h = data_quality_check(df_4h, 240, "4h_from_5m")

    print("[2/10] 回测复现性测试...")
    reproducibility = reproducibility_test(df_5m, df_4h)
    baseline_stats = reproducibility["baseline_stats"]

    print("[3/10] 基线与无盘中止损对照...")
    p = V85Params()
    intrabar_result = run_backtest(df_5m, df_4h, p, True)
    no_intrabar_result = run_backtest(df_5m, df_4h, p, False)
    baseline_gate_result = baseline_gate(intrabar_result["stats"])

    print("[4/10] 年度稳健性测试...")
    yearly = yearly_eval(df_5m, df_4h)

    print("[5/10] 滚动OOS测试...")
    rolling_oos = rolling_oos_eval(df_5m, df_4h, train_years=2)

    print("[6/10] 蒙特卡洛测试...")
    span_years = float(intrabar_result["stats"].get("Years", 1.0))
    mc = monte_carlo_from_trades(intrabar_result["trades"], span_years, n_sims=args.mc_n)

    print("[7/10] 参数敏感性测试...")
    sensitivity = sensitivity_test(df_5m, df_4h)

    print("[8/10] 手续费压力测试...")
    cost_stress = cost_stress_test(df_5m, df_4h)

    print("[9/10] Regime测试...")
    regime = regime_test(df_5m, df_4h)

    print("[10/10] 工程上线门禁检查...")
    eng = engineering_gate(Path("."))

    gate_summary = {
        "data_quality_5m": dq_5m["pass"],
        "data_quality_4h": dq_4h["pass"],
        "reproducibility": reproducibility["pass"],
        "baseline_performance": baseline_gate_result["pass"],
        "yearly_robustness": yearly.get("pass", False),
        "rolling_oos": rolling_oos.get("pass", False),
        "monte_carlo": mc.get("pass", False),
        "sensitivity": sensitivity.get("pass", False),
        "cost_stress": cost_stress.get("pass", False),
        "regime": regime.get("pass", False),
        "engineering_gate": eng["pass"],
    }

    critical = [
        gate_summary["data_quality_5m"],
        gate_summary["data_quality_4h"],
        gate_summary["baseline_performance"],
        gate_summary["yearly_robustness"],
        gate_summary["rolling_oos"],
        gate_summary["monte_carlo"],
        gate_summary["sensitivity"],
        gate_summary["cost_stress"],
        gate_summary["engineering_gate"],
    ]

    final_verdict = "GO" if all(critical) else "NO_GO"

    key_findings = []
    if not dq_5m["pass"] or not dq_4h["pass"]:
        key_findings.append("数据门禁未通过：当前数据不是近2天最新，实盘前必须先补齐最新行情。")
    if not eng["pass"]:
        key_findings.append("工程门禁未通过：缺少实盘执行、状态恢复、对账、运行时Kill Switch等关键模块。")
    if baseline_gate_result["pass"]:
        key_findings.append("离线历史回测指标达到研究阈值（Sharpe/PF/回撤）。")
    else:
        key_findings.append("离线历史回测指标未达到研究阈值。")

    report = {
        "meta": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "data_5m_start": str(df_5m["timestamp"].min()),
            "data_5m_end": str(df_5m["timestamp"].max()),
            "data_4h_start": str(df_4h["timestamp"].min()),
            "data_4h_end": str(df_4h["timestamp"].max()),
            "rows_5m": int(len(df_5m)),
            "rows_4h": int(len(df_4h)),
            "output_dir": str(outdir),
        },
        "data_quality": {
            "5m": dq_5m,
            "4h_from_5m": dq_4h,
        },
        "reproducibility": reproducibility,
        "baseline": {
            "intrabar_stats": intrabar_result["stats"],
            "no_intrabar_stats": no_intrabar_result["stats"],
            "gate": baseline_gate_result,
        },
        "yearly": yearly,
        "rolling_oos": rolling_oos,
        "monte_carlo": mc,
        "sensitivity": sensitivity,
        "cost_stress": cost_stress,
        "regime": regime,
        "engineering_gate": eng,
        "gate_summary": gate_summary,
        "final_verdict": final_verdict,
        "key_findings": key_findings,
    }

    (outdir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    pd.DataFrame(yearly.get("rows", [])).to_csv(outdir / "yearly_rows.csv", index=False)
    pd.DataFrame(rolling_oos.get("rows", [])).to_csv(outdir / "rolling_oos_rows.csv", index=False)
    pd.DataFrame(sensitivity.get("rows", [])).to_csv(outdir / "sensitivity_rows.csv", index=False)
    pd.DataFrame(cost_stress.get("rows", [])).to_csv(outdir / "cost_stress_rows.csv", index=False)
    pd.DataFrame(regime.get("rows", [])).to_csv(outdir / "regime_rows.csv", index=False)

    write_markdown(report, outdir / "summary.md")

    print("=" * 70)
    print("PRELIVE RESEARCH SUITE FINISHED")
    print("=" * 70)
    print(f"Final verdict: {final_verdict}")
    print(f"Report: {outdir / 'report.json'}")
    print(f"Summary: {outdir / 'summary.md'}")


if __name__ == "__main__":
    main()
