#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Long+short parameter optimization for the V85 trend system.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import random
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_intrabar_backtest import IntrabarBacktestEngine, V85Params
from v85_prelive_research_suite import baseline_gate


def load_dataset(data_dir: str, refresh: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    loader = DataLoader5m(data_dir)
    if refresh:
        df_5m = loader.fetch_5m_data()
        loader.resample_to_1h(df_5m)
        df_4h = loader.resample_to_4h(df_5m)
    else:
        df_5m, df_4h = loader.load_data()

    df_5m = df_5m.copy()
    df_4h = df_4h.copy()
    df_5m["timestamp"] = pd.to_datetime(df_5m["timestamp"], utc=True)
    df_4h["timestamp"] = pd.to_datetime(df_4h["timestamp"], utc=True)
    return df_5m, df_4h


def candidate_space() -> list[dict]:
    return [
        {
            "position_pct": position_pct,
            "initial_stop_atr": initial_stop_atr,
            "trail_start_atr": trail_start_atr,
            "trail_offset_atr": trail_offset_atr,
            "tp1_atr": tp1_atr,
            "tp2_atr": tp2_atr,
            "min_long_score": min_long_score,
            "min_short_score": min_short_score,
            "adx_trend_level": adx_trend_level,
            "squeeze_threshold": squeeze_threshold,
            "min_squeeze_candles": min_squeeze_candles,
            "enable_partial_tp": enable_partial_tp,
        }
        for position_pct in [25.0, 30.0, 35.0, 40.0]
        for initial_stop_atr in [2.2, 2.4, 2.6, 2.8]
        for trail_start_atr in [2.8, 3.0, 3.2, 3.5]
        for trail_offset_atr in [2.4, 2.6, 2.8, 3.0]
        for tp1_atr in [2.1, 2.4, 2.8]
        for tp2_atr in [3.5, 4.0, 4.5]
        for min_long_score in [1, 2]
        for min_short_score in [3, 4]
        for adx_trend_level in [20.0, 22.0, 24.0]
        for squeeze_threshold in [0.85, 0.90, 0.95]
        for min_squeeze_candles in [4, 5]
        for enable_partial_tp in [True, False]
    ]


def run_backtest(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params) -> dict:
    engine = IntrabarBacktestEngine(params, use_intrabar_stop=True)
    with contextlib.redirect_stdout(io.StringIO()):
        return engine.run(df_5m, df_4h)


def run_window_backtest(
    df_5m: pd.DataFrame,
    df_4h: pd.DataFrame,
    params: V85Params,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> dict:
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
    return run_backtest(d5, d4, params)


def objective_from_result(result: dict) -> float:
    stats = result["stats"]
    trades = max(float(stats.get("Trades", 0)), 1.0)
    sharpe = float(stats.get("Sharpe", 0.0))
    cagr = float(stats.get("CAGR", 0.0))
    maxdd = abs(float(stats.get("MaxDD_pct", 0.0)))
    pf = float(stats.get("ProfitFactor", 0.0))

    score = sharpe * 4.0 + cagr * 2.5 + max(0.0, pf - 1.0) * 1.5
    score -= maxdd * 4.0
    if trades < 500:
        score -= 0.4
    return score


def evaluate_candidate(df_5m: pd.DataFrame, df_4h: pd.DataFrame, overrides: dict) -> dict:
    params = V85Params(**overrides)
    result = run_backtest(df_5m, df_4h, params)
    stats = result["stats"]
    gate = baseline_gate(stats)
    return {
        "params": asdict(params),
        "stats": {
            "TotalReturn_pct": float(stats["TotalReturn_pct"]),
            "CAGR_pct": float(stats["CAGR"] * 100.0),
            "Sharpe": float(stats["Sharpe"]),
            "MaxDD_pct": float(stats["MaxDD_pct"] * 100.0),
            "ProfitFactor": float(stats["ProfitFactor"]),
            "Trades": int(stats["Trades"]),
            "WinRate_pct": float(stats["WinRate_pct"]),
            "LongTrades": int(stats["LongTrades"]),
            "ShortTrades": int(stats["ShortTrades"]),
            "FinalEquity": float(stats["FinalEquity"]),
        },
        "baseline_gate": gate,
        "objective": objective_from_result(result),
    }


def yearly_eval_with_params(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params) -> dict:
    years = sorted(df_4h["timestamp"].dt.year.unique().tolist())
    rows = []

    for year in years:
        start = pd.Timestamp(f"{year}-01-01", tz="UTC")
        end = pd.Timestamp(f"{year + 1}-01-01", tz="UTC")
        sub = df_4h[(df_4h["timestamp"] >= start) & (df_4h["timestamp"] < end)]
        if len(sub) < 180:
            continue
        result = run_window_backtest(df_5m, df_4h, params, start, end)
        stats = result["stats"]
        rows.append(
            {
                "year": int(year),
                "CAGR": float(stats.get("CAGR", 0.0)),
                "Sharpe": float(stats.get("Sharpe", 0.0)),
                "MaxDD_pct": float(stats.get("MaxDD_pct", 0.0)),
                "Trades": int(stats.get("Trades", 0)),
                "Return_pct": float(stats.get("TotalReturn_pct", 0.0)),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_year_data"}

    positive_year_ratio = float((df["CAGR"] > 0).mean())
    avg_sharpe = float(df["Sharpe"].mean())
    worst_return = float(df["Return_pct"].min())
    passed = (positive_year_ratio >= 0.70) and (avg_sharpe >= 0.70) and (worst_return > -30.0)
    return {
        "rows": rows,
        "positive_year_ratio": positive_year_ratio,
        "avg_sharpe": avg_sharpe,
        "worst_return_pct": worst_return,
        "pass": passed,
    }


def rolling_oos_eval_with_params(
    df_5m: pd.DataFrame,
    df_4h: pd.DataFrame,
    params: V85Params,
    train_years: int = 2,
) -> dict:
    years = sorted(df_4h["timestamp"].dt.year.unique().tolist())
    rows = []

    for oos_year in years:
        train_set = [y for y in years if (oos_year - train_years) <= y < oos_year]
        if len(train_set) < train_years:
            continue

        start = pd.Timestamp(f"{oos_year}-01-01", tz="UTC")
        end = pd.Timestamp(f"{oos_year + 1}-01-01", tz="UTC")
        sub = df_4h[(df_4h["timestamp"] >= start) & (df_4h["timestamp"] < end)]
        if len(sub) < 180:
            continue

        result = run_window_backtest(df_5m, df_4h, params, start, end)
        stats = result["stats"]
        rows.append(
            {
                "oos_year": int(oos_year),
                "train_years": train_set,
                "Sharpe": float(stats.get("Sharpe", 0.0)),
                "CAGR": float(stats.get("CAGR", 0.0)),
                "Return_pct": float(stats.get("TotalReturn_pct", 0.0)),
                "Trades": int(stats.get("Trades", 0)),
            }
        )

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


def cost_stress_with_params(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params) -> dict:
    rows = []
    base = asdict(params)
    for commission_pct in [0.06, 0.10, 0.15, 0.20]:
        stress_params = V85Params(**{**base, "commission_pct": commission_pct})
        result = run_backtest(df_5m, df_4h, stress_params)
        stats = result["stats"]
        rows.append(
            {
                "commission_pct": commission_pct,
                "Return_pct": float(stats.get("TotalReturn_pct", 0.0)),
                "Sharpe": float(stats.get("Sharpe", 0.0)),
                "MaxDD_pct": float(stats.get("MaxDD_pct", 0.0)),
            }
        )

    df = pd.DataFrame(rows)
    worst = df.iloc[-1]
    passed = (
        float(worst["Return_pct"]) > 0.0
        and float(worst["Sharpe"]) >= 0.5
        and float(worst["MaxDD_pct"]) >= -0.35
    )
    return {"rows": rows, "pass": bool(passed)}


def regime_test_with_params(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: V85Params) -> dict:
    rows = []
    regimes = [
        ("bull_2020_2021", "2020-01-01", "2022-01-01"),
        ("bear_2022", "2022-01-01", "2023-01-01"),
        ("mixed_2023_2025", "2023-01-01", "2026-01-01"),
    ]

    for name, start_text, end_text in regimes:
        start = pd.Timestamp(start_text, tz="UTC")
        end = pd.Timestamp(end_text, tz="UTC")
        sub = df_4h[(df_4h["timestamp"] >= start) & (df_4h["timestamp"] < end)]
        if len(sub) < 180:
            continue
        result = run_window_backtest(df_5m, df_4h, params, start, end)
        stats = result["stats"]
        rows.append(
            {
                "regime": name,
                "Return_pct": float(stats.get("TotalReturn_pct", 0.0)),
                "Sharpe": float(stats.get("Sharpe", 0.0)),
                "MaxDD_pct": float(stats.get("MaxDD_pct", 0.0)),
                "Trades": int(stats.get("Trades", 0)),
            }
        )

    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": rows, "pass": False, "reason": "no_regimes"}

    passed = bool((df["Return_pct"] > -30.0).all() and (df["MaxDD_pct"] > -0.35).all())
    return {"rows": rows, "pass": passed}


def enrich_top_candidate(df_5m: pd.DataFrame, df_4h: pd.DataFrame, candidate: dict) -> dict:
    params = V85Params(**candidate["params"])
    candidate["yearly"] = yearly_eval_with_params(df_5m, df_4h, params)
    candidate["rolling_oos"] = rolling_oos_eval_with_params(df_5m, df_4h, params, train_years=2)
    candidate["cost_stress"] = cost_stress_with_params(df_5m, df_4h, params)
    candidate["regime"] = regime_test_with_params(df_5m, df_4h, params)

    candidate["live_score"] = candidate["objective"]
    if not candidate["cost_stress"].get("pass", False):
        candidate["live_score"] -= 1.0
    if not candidate["yearly"].get("pass", False):
        candidate["live_score"] -= 0.7
    if not candidate["rolling_oos"].get("pass", False):
        candidate["live_score"] -= 0.7
    if not candidate["regime"].get("pass", False):
        candidate["live_score"] -= 0.5
    candidate["recommended"] = (
        candidate["baseline_gate"]["pass"]
        and candidate["cost_stress"].get("pass", False)
        and candidate["yearly"].get("pass", False)
        and candidate["rolling_oos"].get("pass", False)
        and candidate["regime"].get("pass", False)
    )
    return candidate


def summarize(best: dict) -> str:
    s = best["stats"]
    p = best["params"]
    return (
        f"Sharpe={s['Sharpe']:.3f}, CAGR={s['CAGR_pct']:.2f}%, MaxDD={s['MaxDD_pct']:.2f}%, "
        f"PF={s['ProfitFactor']:.3f}, Trades={s['Trades']}, objective={best['objective']:.3f}, "
        f"live_score={best.get('live_score', best['objective']):.3f}, recommended={best.get('recommended', False)}, "
        f"params={{position_pct={p['position_pct']}, initial_stop_atr={p['initial_stop_atr']}, "
        f"trail_start_atr={p['trail_start_atr']}, trail_offset_atr={p['trail_offset_atr']}, "
        f"tp1_atr={p['tp1_atr']}, tp2_atr={p['tp2_atr']}, min_long_score={p['min_long_score']}, "
        f"min_short_score={p['min_short_score']}, adx_trend_level={p['adx_trend_level']}, "
        f"squeeze_threshold={p['squeeze_threshold']}, min_squeeze_candles={p['min_squeeze_candles']}, "
        f"enable_partial_tp={p['enable_partial_tp']}}}"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Optimize long+short V85 parameters")
    ap.add_argument("--data_dir", default="./data")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--refresh_data", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--sample_n", type=int, default=80)
    ap.add_argument("--top_n", type=int, default=8)
    args = ap.parse_args()

    outdir = Path(args.outdir) if args.outdir else Path(args.data_dir) / f"v85_longshort_opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    outdir.mkdir(parents=True, exist_ok=True)

    df_5m, df_4h = load_dataset(args.data_dir, args.refresh_data)

    space = candidate_space()
    rnd = random.Random(args.seed)
    sample_n = min(args.sample_n, len(space))
    sampled = rnd.sample(space, sample_n)

    results = []
    for idx, overrides in enumerate(sampled, start=1):
        candidate = evaluate_candidate(df_5m, df_4h, overrides)
        candidate["rank_seed_index"] = idx
        results.append(candidate)
        print(f"[{idx}/{sample_n}] objective={candidate['objective']:.3f} sharpe={candidate['stats']['Sharpe']:.3f} trades={candidate['stats']['Trades']}")

    results.sort(key=lambda x: x["objective"], reverse=True)
    top = results[: args.top_n]
    enriched = [enrich_top_candidate(df_5m, df_4h, row) for row in top]
    enriched.sort(key=lambda x: x["live_score"], reverse=True)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sample_n": sample_n,
        "top_n": args.top_n,
        "data_5m_end": str(df_5m["timestamp"].max()),
        "data_4h_end": str(df_4h["timestamp"].max()),
        "best_candidate": enriched[0] if enriched else None,
        "top_candidates": enriched,
    }

    (outdir / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    pd.DataFrame(
        [
            {
                "live_score": row["live_score"],
                "objective": row["objective"],
                **row["stats"],
                **{
                    "position_pct": row["params"]["position_pct"],
                    "initial_stop_atr": row["params"]["initial_stop_atr"],
                    "trail_start_atr": row["params"]["trail_start_atr"],
                    "trail_offset_atr": row["params"]["trail_offset_atr"],
                    "tp1_atr": row["params"]["tp1_atr"],
                    "tp2_atr": row["params"]["tp2_atr"],
                    "min_long_score": row["params"]["min_long_score"],
                    "min_short_score": row["params"]["min_short_score"],
                    "adx_trend_level": row["params"]["adx_trend_level"],
                    "squeeze_threshold": row["params"]["squeeze_threshold"],
                    "min_squeeze_candles": row["params"]["min_squeeze_candles"],
                    "enable_partial_tp": row["params"]["enable_partial_tp"],
                    "recommended": row["recommended"],
                },
            }
            for row in enriched
        ]
    ).to_csv(outdir / "top_candidates.csv", index=False)

    summary = summarize(enriched[0]) if enriched else "No candidate produced."
    (outdir / "summary.txt").write_text(summary, encoding="utf-8")

    print("=" * 70)
    print("LONG+SHORT OPTIMIZATION FINISHED")
    print("=" * 70)
    print(summary)
    print(f"Report: {outdir / 'report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
