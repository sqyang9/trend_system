#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Risk-Off archive plus graded AddOn study on the locked baseline."""

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
from v90_riskoff_promotion_validation import TIME_SLICES
from v90_trend_long_mother import SEED, TrendLongParams, run_candidate, with_overrides


INIT_EQUITY = 10000.0
ANNUALIZATION_4H = np.sqrt(252.0 * 6.0)
DEFAULT_TUPLE = "next_bar_open + legacy_bar_extrema + midpoint + full_model"
STRESS_TUPLE = "live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model"

ARCHIVE_MD = Path("RISKOFF_STATUS_ARCHIVE.md")
ARCHIVE_JSON = Path("riskoff_status_archive.json")
ARCHIVE_TXT = Path("riskoff_status_archive_summary.txt")
GRADING_MD = Path("BTC_ADDON_GRADING_REPORT.md")
GRADING_JSON = Path("btc_addon_grading_report.json")
GRADING_TXT = Path("btc_addon_grading_summary.txt")
ACTIVE_MAINLINE_MD = Path("ACTIVE_MAINLINE_STATUS.md")

OVERLAY_REPORT = Path("btc_overlay_integration_report.json")
ASSET_MGMT_REPORT = Path("btc_asset_management_system_report.json")
ALIGNMENT_REPORT = Path("btc_riskoff_alignment_report.json")
CORE_LEVEL_REPORT = Path("btc_core_riskoff_level_report.json")
PROMOTION_V1_REPORT = Path("btc_riskoff_promotion_report.json")
PROMOTION_V2_REPORT = Path("btc_riskoff_promotion_v2_report.json")
LAST_MILE_REPORT = Path("btc_riskoff_reentry_last_mile.json")

WF_TEST_YEARS = [2023, 2024, 2025]
GRADE_WEIGHTS = {"weak": 0.25, "base": 0.35, "strong": 0.50}
GRADING_SCHEMES = [
    {
        "name": "breakout_slope",
        "title": "Breakout Quality + Slope",
        "description": "Grade entries by breakout distance, EMA slope, and close location.",
        "features": {
            "breakout_distance_atr": 0.45,
            "ema_slope_atr": 0.35,
            "close_location": 0.20,
        },
    },
    {
        "name": "adx_close_range",
        "title": "ADX + Close Location + Range",
        "description": "Grade entries by directional strength, close location, and bar expansion.",
        "features": {
            "adx": 0.40,
            "close_location": 0.30,
            "bar_range_atr": 0.30,
        },
    },
    {
        "name": "compression_breakout",
        "title": "Compression + Breakout Release",
        "description": "Grade entries by squeeze quality, squeeze persistence, and breakout distance.",
        "features": {
            "compression_quality": 0.35,
            "squeeze_count": 0.25,
            "breakout_distance_atr": 0.40,
        },
    },
]


def current_research_optimal(**overrides) -> TrendLongParams:
    params = TrendLongParams(
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
    return with_overrides(params, **overrides)


def calmar(cagr: float, maxdd: float) -> float:
    return 0.0 if maxdd >= 0.0 else float(cagr) / abs(float(maxdd))


def pf_from_equity(equity: pd.Series) -> float:
    pnl = equity.diff().fillna(0.0)
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    return 0.0 if gross_loss <= 0.0 else gross_profit / gross_loss


def max_drawdown_duration_bars(drawdown: pd.Series) -> int:
    best = cur = 0
    for is_dd in (drawdown < 0).tolist():
        if is_dd:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def compute_metrics(equity: pd.Series, exposure: pd.Series) -> Dict:
    equity = equity.astype(float)
    exposure = exposure.astype(float).reindex(equity.index).ffill().fillna(0.0)
    ret = equity.pct_change().fillna(0.0)
    drawdown = equity / equity.cummax() - 1.0
    years = max((equity.index[-1] - equity.index[0]).total_seconds() / 86400.0, 1.0) / 365.25
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = (float(equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0) if years > 0 else 0.0
    std = float(ret.std())
    sharpe = float(ret.mean()) / std * ANNUALIZATION_4H if std > 0 else 0.0
    dd_bars = max_drawdown_duration_bars(drawdown)
    return {
        "TotalReturn_pct": total_return * 100.0,
        "CAGR_pct": cagr * 100.0,
        "Sharpe": sharpe,
        "Calmar": calmar(cagr, float(drawdown.min())),
        "MaxDD_pct": float(drawdown.min() * 100.0),
        "PF": pf_from_equity(equity),
        "Exposure_pct": float(exposure.mean() * 100.0),
        "MaxDDDuration_bars_4h": dd_bars,
        "MaxDDDuration_days": float(dd_bars * 4.0 / 24.0),
    }


def compute_slice_metrics(equity: pd.Series, exposure: pd.Series) -> Dict:
    if len(equity) < 2:
        return {
            "TotalReturn_pct": 0.0,
            "CAGR_pct": 0.0,
            "Sharpe": 0.0,
            "Calmar": 0.0,
            "MaxDD_pct": 0.0,
            "Exposure_pct": 0.0,
        }
    return compute_metrics(equity, exposure)


def yearly_returns(equity: pd.Series) -> List[Dict]:
    rows = []
    for year, sub in equity.to_frame("equity").groupby(equity.index.year):
        if len(sub) < 2:
            continue
        rows.append({
            "year": int(year),
            "Return_pct": float((sub["equity"].iloc[-1] / sub["equity"].iloc[0] - 1.0) * 100.0),
        })
    return rows


def delta_metrics(metrics: Dict, baseline: Dict) -> Dict:
    return {
        "Return_pct": float(metrics["TotalReturn_pct"] - baseline["TotalReturn_pct"]),
        "CAGR_pct": float(metrics["CAGR_pct"] - baseline["CAGR_pct"]),
        "Sharpe": float(metrics["Sharpe"] - baseline["Sharpe"]),
        "Calmar": float(metrics["Calmar"] - baseline["Calmar"]),
        "MaxDD_improvement_pct": float(abs(baseline["MaxDD_pct"]) - abs(metrics["MaxDD_pct"])),
    }


def bh_equity(close: pd.Series) -> pd.Series:
    rel = close / float(close.iloc[0])
    return INIT_EQUITY * rel


def period_return(equity: pd.Series, start: str, end: str) -> float:
    sub = equity[(equity.index >= pd.Timestamp(start, tz="UTC")) & (equity.index < pd.Timestamp(end, tz="UTC"))]
    if len(sub) < 2:
        return 0.0
    return float((sub.iloc[-1] / sub.iloc[0] - 1.0) * 100.0)


def rank_against_train(train_values: pd.Series, values: pd.Series) -> pd.Series:
    arr = np.sort(train_values.astype(float).dropna().to_numpy())
    if arr.size == 0:
        return pd.Series(0.5, index=values.index, dtype=float)
    ranks = np.searchsorted(arr, values.astype(float).to_numpy(), side="right") / float(arr.size)
    return pd.Series(ranks, index=values.index, dtype=float)


def load_overlay_artifact() -> Dict:
    data = json.loads(OVERLAY_REPORT.read_text(encoding="utf-8"))
    idx = pd.to_datetime(data["timeseries"]["timestamp"], utc=True)
    return {
        "artifact": data,
        "index": idx,
        "bh_equity": pd.Series(data["timeseries"]["B&H"], index=idx, dtype=float),
        "addon_equity": pd.Series(data["timeseries"]["AddOnOverlay"], index=idx, dtype=float),
        "addon_metrics": data["schemes"]["AddOnOverlay"]["metrics"],
        "bh_metrics": data["schemes"]["B&H"]["metrics"],
    }


def prepare_base_run(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    result = run_candidate(df_5m, df_4h, params)
    signals = result["signals"].reset_index().copy()
    signals["timestamp"] = pd.to_datetime(signals["timestamp"], utc=True)
    trade_meta = result["trade_meta"].copy()
    trade_meta["entry_time"] = pd.to_datetime(trade_meta["entry_time"], utc=True)
    trade_meta["exit_time"] = pd.to_datetime(trade_meta["exit_time"], utc=True)
    rows = []
    for trade_id, meta in trade_meta.reset_index(drop=True).iterrows():
        signal_idx = int(meta["entry_index"]) - 1
        if signal_idx < 0 or signal_idx >= len(signals):
            continue
        signal = signals.iloc[signal_idx]
        atr = max(float(signal["atr"]), 1e-9)
        bb_width_norm = float(signal["bb_width_norm"]) if pd.notna(signal["bb_width_norm"]) else np.nan
        compression_quality = 1.0 / max(bb_width_norm, 1e-6) if pd.notna(bb_width_norm) and bb_width_norm > 0 else 0.0
        rows.append({
            "trade_id": int(trade_id),
            "signal_time": pd.Timestamp(signal["timestamp"]),
            "entry_time": pd.Timestamp(meta["entry_time"]),
            "exit_time": pd.Timestamp(meta["exit_time"]),
            "entry_price": float(meta["entry_price"]),
            "exit_price": float(meta["exit_price"]),
            "exit_reason": str(meta["exit_reason"]),
            "breakout_distance_atr": float((float(signal["close"]) - float(signal["donchian_high_entry"])) / atr),
            "ema_slope_atr": float(float(signal["ema_slope"]) / atr),
            "trend_distance_atr": float((float(signal["close"]) - float(signal["ema"])) / atr),
            "adx": float(signal["adx"]),
            "close_location": float(signal["close_location"]),
            "bar_range_atr": float(signal["bar_range_atr"]),
            "squeeze_count": float(signal["squeeze_count"]),
            "compression_quality": float(compression_quality),
            "bb_width_norm": float(bb_width_norm) if pd.notna(bb_width_norm) else np.nan,
        })
    entries = pd.DataFrame(rows).sort_values("entry_time").reset_index(drop=True)
    return {
        "result": result,
        "signals": signals,
        "entries": entries,
    }


def assign_scheme_weights(entries: pd.DataFrame, scheme: Dict, train_mask: pd.Series) -> Tuple[pd.DataFrame, Dict]:
    assigned = entries.copy()
    score = pd.Series(0.0, index=assigned.index, dtype=float)
    for feature, weight in scheme["features"].items():
        ranks = rank_against_train(assigned.loc[train_mask, feature], assigned[feature])
        score = score + weight * ranks
    score_train = score.loc[train_mask]
    q1 = float(score_train.quantile(1.0 / 3.0)) if not score_train.empty else 0.33
    q2 = float(score_train.quantile(2.0 / 3.0)) if not score_train.empty else 0.67

    def label_one(value: float) -> str:
        if value <= q1:
            return "weak"
        if value <= q2:
            return "base"
        return "strong"

    assigned["grade_score"] = score
    assigned["grade_label"] = score.apply(label_one)
    assigned["addon_weight"] = assigned["grade_label"].map(GRADE_WEIGHTS).astype(float)
    thresholds = {
        "score_q1": q1,
        "score_q2": q2,
        "train_trade_count": int(train_mask.sum()),
        "feature_weights": scheme["features"],
    }
    return assigned, thresholds


def constant_weight_plan(entries: pd.DataFrame, weight: float) -> pd.DataFrame:
    out = entries.copy()
    out["grade_score"] = 0.5
    out["grade_label"] = "base"
    out["addon_weight"] = float(weight)
    return out


def simulate_sleeve(df_4h: pd.DataFrame, plan: pd.DataFrame, commission_pct: float) -> Dict:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    plan = plan.copy()
    plan["entry_bar"] = plan["entry_time"].dt.floor("4h")
    plan["exit_bar"] = plan["exit_time"].dt.floor("4h")
    events: Dict[pd.Timestamp, List[Tuple[pd.Timestamp, str, Dict]]] = {}
    for rec in plan.to_dict("records"):
        events.setdefault(rec["entry_bar"], []).append((rec["entry_time"], "entry", rec))
        events.setdefault(rec["exit_bar"], []).append((rec["exit_time"], "exit", rec))

    commission = commission_pct / 100.0
    cash = INIT_EQUITY
    qty = 0.0
    current_weight = 0.0
    current_grade = "off"
    current_trade_id = None
    grade_counts = {"weak": 0, "base": 0, "strong": 0}
    rows = []
    state_changes = 0
    notional_turnover = 0.0
    causality_violations = 0

    for ts, row in d4.iterrows():
        for event_time, action, rec in sorted(events.get(ts, []), key=lambda x: x[0]):
            if rec["signal_time"] >= rec["entry_time"]:
                causality_violations += 1
            if action == "exit" and current_trade_id == rec["trade_id"] and qty > 0.0:
                price = float(rec["exit_price"])
                trade_notional = qty * price
                cash += trade_notional * (1.0 - commission)
                notional_turnover += trade_notional
                qty = 0.0
                current_weight = 0.0
                current_grade = "off"
                current_trade_id = None
                state_changes += 1
            elif action == "entry" and qty <= 0.0:
                price = float(rec["entry_price"])
                weight = float(rec["addon_weight"])
                if price > 0.0 and weight > 0.0:
                    equity = cash
                    target_qty = (weight * equity) / max(price * (1.0 + commission), 1e-12)
                    cost = target_qty * price * (1.0 + commission)
                    cash -= cost
                    qty = target_qty
                    current_weight = weight
                    current_grade = str(rec["grade_label"])
                    current_trade_id = rec["trade_id"]
                    grade_counts[current_grade] = grade_counts.get(current_grade, 0) + 1
                    notional_turnover += target_qty * price
                    state_changes += 1
        close_price = float(row["close"])
        equity = cash + qty * close_price
        rows.append({
            "time": ts,
            "equity": equity,
            "weight": current_weight if qty > 0.0 else 0.0,
            "grade": current_grade if qty > 0.0 else "off",
        })

    out = pd.DataFrame(rows).set_index("time")
    return {
        "equity": out["equity"].astype(float),
        "weight": out["weight"].astype(float),
        "grade": out["grade"],
        "state_changes": int(state_changes),
        "turnover_notional": float(notional_turnover),
        "grade_counts": {k: int(v) for k, v in grade_counts.items()},
        "active_ratio_pct": float((out["weight"] > 0.0).mean() * 100.0),
        "avg_weight_when_active": float(out.loc[out["weight"] > 0.0, "weight"].mean()) if (out["weight"] > 0.0).any() else 0.0,
        "causality_violations": int(causality_violations),
    }


def simulate_combo_from_plan(df_4h: pd.DataFrame, plan: pd.DataFrame, commission_pct: float) -> Dict:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    bh = bh_equity(d4["close"].astype(float))
    sleeve = simulate_sleeve(df_4h.reset_index(), plan, commission_pct)
    combo_equity = bh + (sleeve["equity"] - INIT_EQUITY)
    combo_exposure = pd.Series(1.0, index=combo_equity.index, dtype=float) + sleeve["weight"].reindex(combo_equity.index).fillna(0.0)
    metrics = compute_metrics(combo_equity, combo_exposure)
    return {
        "combo_equity": combo_equity,
        "combo_exposure": combo_exposure,
        "combo_metrics": metrics,
        "sleeve": sleeve,
        "yearly_returns": yearly_returns(combo_equity),
    }


def slice_range(series: pd.Series, start: str, end: str) -> pd.Series:
    return series[(series.index >= pd.Timestamp(start, tz="UTC")) & (series.index < pd.Timestamp(end, tz="UTC"))]


def time_slice_rows(results: Dict[str, Dict], baseline_key: str) -> List[Dict]:
    rows = []
    for sl in TIME_SLICES:
        row = {"slice": sl["name"], "window": {"start": sl["start"], "end": sl["end"]}}
        baseline = results[baseline_key]
        base_metrics = compute_slice_metrics(
            slice_range(baseline["combo_equity"], sl["start"], sl["end"]),
            slice_range(baseline["combo_exposure"], sl["start"], sl["end"]),
        )
        row[baseline_key] = base_metrics
        for key, item in results.items():
            metrics = compute_slice_metrics(
                slice_range(item["combo_equity"], sl["start"], sl["end"]),
                slice_range(item["combo_exposure"], sl["start"], sl["end"]),
            )
            row[key] = metrics
            row[f"{key}_delta_vs_baseline"] = delta_metrics(metrics, base_metrics)
        rows.append(row)
    return rows


def stress_compare(default_results: Dict[str, Dict], stress_results: Dict[str, Dict]) -> Dict[str, Dict]:
    out = {}
    for key in default_results:
        out[key] = {
            "delta_vs_default_same_scheme": delta_metrics(
                stress_results[key]["combo_metrics"],
                default_results[key]["combo_metrics"],
            )
        }
    return out


def walk_forward_analysis(
    df_4h: pd.DataFrame,
    entries_default: pd.DataFrame,
    entries_stress: pd.DataFrame,
    scheme: Dict,
    commission_pct: float,
) -> Dict:
    windows = []
    strict_flags = []
    d_returns = []
    d_sharpes = []
    d_calmars = []
    d4 = ensure_datetime(df_4h)
    for test_year in WF_TEST_YEARS:
        train_start = pd.Timestamp(f"{test_year - 3}-01-01", tz="UTC")
        test_start = pd.Timestamp(f"{test_year}-01-01", tz="UTC")
        test_end = pd.Timestamp(f"{test_year + 1}-01-01", tz="UTC")
        train_mask = (entries_default["signal_time"] >= train_start) & (entries_default["signal_time"] < test_start)
        sim_mask = (entries_default["signal_time"] >= train_start) & (entries_default["signal_time"] < test_end)
        if int(train_mask.sum()) < 3:
            continue
        sim_entries = entries_default.loc[sim_mask].reset_index(drop=True)
        sim_train_mask = train_mask.loc[sim_mask].reset_index(drop=True)
        assigned, thresholds = assign_scheme_weights(sim_entries, scheme, sim_train_mask)
        base_plan = constant_weight_plan(sim_entries, GRADE_WEIGHTS["base"])
        date_mask = (d4["timestamp"] >= train_start) & (d4["timestamp"] < test_end)
        slice_4h = d4.loc[date_mask].reset_index(drop=True)
        baseline = simulate_combo_from_plan(slice_4h, base_plan, commission_pct)
        candidate = simulate_combo_from_plan(slice_4h, assigned, commission_pct)
        base_metrics = compute_slice_metrics(
            slice_range(baseline["combo_equity"], test_start.isoformat(), test_end.isoformat()),
            slice_range(baseline["combo_exposure"], test_start.isoformat(), test_end.isoformat()),
        )
        cand_metrics = compute_slice_metrics(
            slice_range(candidate["combo_equity"], test_start.isoformat(), test_end.isoformat()),
            slice_range(candidate["combo_exposure"], test_start.isoformat(), test_end.isoformat()),
        )
        delta = delta_metrics(cand_metrics, base_metrics)
        strict = bool(
            cand_metrics["Sharpe"] > base_metrics["Sharpe"]
            and cand_metrics["Calmar"] > base_metrics["Calmar"]
            and cand_metrics["TotalReturn_pct"] > base_metrics["TotalReturn_pct"]
            and abs(cand_metrics["MaxDD_pct"]) <= abs(base_metrics["MaxDD_pct"]) + 1.0
        )
        strict_flags.append(float(strict))
        d_returns.append(delta["Return_pct"])
        d_sharpes.append(delta["Sharpe"])
        d_calmars.append(delta["Calmar"])
        windows.append(
            {
                "train_window": {"start": train_start.date().isoformat(), "end": test_start.date().isoformat()},
                "test_window": {"start": test_start.date().isoformat(), "end": test_end.date().isoformat()},
                "thresholds": thresholds,
                "candidate_metrics": cand_metrics,
                "baseline_metrics": base_metrics,
                "delta_vs_baseline": delta,
                "strict_outperform": strict,
            }
        )
    return {
        "windows": windows,
        "strict_win_ratio": float(np.mean(strict_flags)) if strict_flags else 0.0,
        "avg_delta_return_pct": float(np.mean(d_returns)) if d_returns else 0.0,
        "avg_delta_sharpe": float(np.mean(d_sharpes)) if d_sharpes else 0.0,
        "avg_delta_calmar": float(np.mean(d_calmars)) if d_calmars else 0.0,
        "stress_entry_count": int(len(entries_stress)),
    }


def summarize_scheme(
    name: str,
    title: str,
    description: str,
    full_sample: Dict,
    baseline: Dict,
    bh_metrics: Dict,
    wf: Dict,
    slices: List[Dict],
    stress: Dict,
) -> Dict:
    deltas = delta_metrics(full_sample["combo_metrics"], baseline["combo_metrics"])
    deltas_vs_bh = delta_metrics(full_sample["combo_metrics"], bh_metrics)
    bull = next(row for row in slices if row["slice"] == "bull_expansion")
    recovery = next(row for row in slices if row["slice"] == "recovery_phase")
    draw = next(row for row in slices if row["slice"] == "major_drawdown")
    return {
        "name": name,
        "title": title,
        "description": description,
        "metrics": full_sample["combo_metrics"],
        "yearly_returns": full_sample["yearly_returns"],
        "delta_vs_addon_baseline": deltas,
        "delta_vs_bh": deltas_vs_bh,
        "addon_active_ratio_pct": full_sample["sleeve"]["active_ratio_pct"],
        "avg_addon_weight_when_active": full_sample["sleeve"]["avg_weight_when_active"],
        "state_changes": full_sample["sleeve"]["state_changes"],
        "turnover_notional": full_sample["sleeve"]["turnover_notional"],
        "grade_counts": full_sample["sleeve"]["grade_counts"],
        "walk_forward": wf,
        "time_slice_deltas": {
            "bull_expansion": bull[f"{name}_delta_vs_baseline"],
            "recovery_phase": recovery[f"{name}_delta_vs_baseline"],
            "major_drawdown": draw[f"{name}_delta_vs_baseline"],
        },
        "execution_stress": stress[name]["delta_vs_default_same_scheme"],
        "causality_violations_default": int(full_sample["sleeve"]["causality_violations"]),
    }


def best_scheme_key(report_rows: Dict[str, Dict]) -> str:
    ranked = sorted(
        report_rows.items(),
        key=lambda kv: (
            kv[1]["walk_forward"]["strict_win_ratio"],
            kv[1]["walk_forward"]["avg_delta_calmar"],
            kv[1]["walk_forward"]["avg_delta_sharpe"],
            kv[1]["delta_vs_addon_baseline"]["Return_pct"],
            kv[1]["delta_vs_addon_baseline"]["MaxDD_improvement_pct"],
        ),
        reverse=True,
    )
    return ranked[0][0]


def archive_payload() -> Dict:
    exploratory = json.loads(ASSET_MGMT_REPORT.read_text(encoding="utf-8"))
    aligned = json.loads(ALIGNMENT_REPORT.read_text(encoding="utf-8"))
    core_level = json.loads(CORE_LEVEL_REPORT.read_text(encoding="utf-8"))
    promo1 = json.loads(PROMOTION_V1_REPORT.read_text(encoding="utf-8"))
    promo2 = json.loads(PROMOTION_V2_REPORT.read_text(encoding="utf-8"))
    last_mile = json.loads(LAST_MILE_REPORT.read_text(encoding="utf-8"))
    return {
        "generated_at_local": datetime.now().isoformat(),
        "locked_baseline": {
            "primary_mainline": "BTC long-only squeeze_release_20",
            "research_optimal": "lb20_stop3.2_trail5.0_beoff",
            "default_tuple": DEFAULT_TUPLE,
            "stress_tuple": STRESS_TUPLE,
            "launch_optimal": "LAUNCH_NO_GO",
            "official_baseline_status": "AddOn-only remains the locked baseline",
        },
        "stages": {
            "stage_a_exploratory_asset_allocation": {
                "source_files": [
                    "v90_asset_management_system.py",
                    "BTC_ASSET_MANAGEMENT_SYSTEM_REPORT.md",
                    "btc_asset_management_system_report.json",
                ],
                "why_it_looked_promising": exploratory["recommendation"]["riskoff_detail"],
                "caveat": "The study used simplified allocation simulation plus full-sample candidate ranking, so it could not be treated as a formal baseline result.",
                "one_line_conclusion": "Exploration showed Risk-Off might materially improve the AddOn portfolio, but the result was not execution-aligned enough for formal promotion.",
            },
            "stage_b_aligned_validation": {
                "source_files": [
                    "v90_asset_management_system_aligned.py",
                    "BTC_RISKOFF_ALIGNMENT_REPORT.md",
                    "btc_riskoff_alignment_report.json",
                ],
                "what_changed": aligned["method"]["scope_note"],
                "result": aligned["judgment"]["main_answer"],
                "evidence_level": aligned["judgment"]["evidence_level"],
                "one_line_conclusion": "Risk-Off survived execution alignment and causality audit, but the evidence was only strong enough for aligned-but-preliminary status.",
            },
            "stage_c_core_off_weight_and_with_core_vs_no_core": {
                "source_files": [
                    "v90_core_riskoff_level_study.py",
                    "BTC_CORE_RISKOFF_LEVEL_REPORT.md",
                    "btc_core_riskoff_level_report.json",
                ],
                "recommended_core_off_weight": core_level["judgment"]["recommended_core_off_weight"],
                "with_core_vs_no_core": core_level["judgment"]["with_core_vs_no_core"],
                "one_line_conclusion": "Full flat beat partial residual core, and the with-core framework remained more reasonable than a no-core switching framework.",
            },
            "stage_d_promotion_v1": {
                "source_files": [
                    "v90_riskoff_promotion_validation.py",
                    "BTC_RISKOFF_PROMOTION_REPORT.md",
                    "btc_riskoff_promotion_report.json",
                ],
                "promotion_answer": promo1["judgment"]["promotion_answer"],
                "failure_reason": promo1["judgment"]["answer_1"],
                "one_line_conclusion": "Promotion v1 failed because OOS consistency was too weak and the main blocker was bull/recovery opportunity cost, not EMA instability or causality.",
            },
            "stage_e_promotion_v2": {
                "source_files": [
                    "v90_riskoff_promotion_v2.py",
                    "BTC_RISKOFF_PROMOTION_V2_REPORT.md",
                    "btc_riskoff_promotion_v2_report.json",
                ],
                "best_repair_candidate": promo2["judgment"]["best_repair_candidate"],
                "why_hysteresis_worse": "Hysteresis delayed recovery without fixing the core OOS problem, so it raised opportunity cost instead of reducing it.",
                "why_two_stage_better": promo2["judgment"]["answer_4"],
                "recommendation": promo2["judgment"]["recommendation"],
                "one_line_conclusion": "Two-stage repair was directionally better than flat or hysteresis, but still not good enough to clear the promotion bar.",
            },
            "stage_f_narrow_promotion_and_final_reentry": {
                "source_files": [
                    "v90_riskoff_reentry_final_check.py",
                    "v90_riskoff_reentry_last_mile.py",
                    "BTC_RISKOFF_REENTRY_LAST_MILE_REPORT.md",
                    "btc_riskoff_reentry_last_mile.json",
                ],
                "final_key_issue": "Flat-to-risk-on re-entry timing was the last material blocker after trigger and structure issues had already been narrowed down.",
                "best_candidate": last_mile["judgment"]["best_candidate"],
                "why_still_failed": last_mile["judgment"]["answer_7"],
                "final_action": last_mile["judgment"]["promotion_decision"],
                "one_line_conclusion": "Even the best re-entry repair candidate improved the profile but still did not reach promotion-candidate strength, so promotion was frozen.",
            },
        },
        "final_conclusion": {
            "riskoff_directionally_valid": True,
            "riskoff_entered_baseline": False,
            "official_status": "Frozen aligned-but-preliminary direction. Not part of the locked baseline.",
            "restart_prerequisites": [
                "A clearly scoped new hypothesis that is not just more same-line promotion repair.",
                "Execution-aligned implementation under the locked default tuple.",
                "A reason to expect better bull/recovery opportunity-cost control than the frozen line delivered.",
                "Promotion criteria defined before re-opening the line.",
            ],
            "currently_forbidden_work": [
                "Continuing same-line Risk-Off promotion repair.",
                "Reopening Bear Short as a default extension.",
                "Treating frozen Risk-Off results as active baseline conclusions.",
                "Re-running broad EMA or regime-filter searches.",
            ],
            "active_mainline_statement": "The active mainline is still BTC long-only squeeze_release_20 with AddOn-only overlay semantics under the locked default tuple.",
        },
    }


def write_archive(payload: Dict) -> None:
    ARCHIVE_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Risk-Off Status Archive",
        "",
        "## Final Status",
        "",
        "- Risk-Off direction is valid: yes.",
        "- Risk-Off is part of the locked baseline: no.",
        f"- Official state: {payload['final_conclusion']['official_status']}",
        "- Final action: Freeze Risk-Off promotion.",
        "",
    ]
    stage_titles = [
        ("stage_a_exploratory_asset_allocation", "Stage A: Exploratory Asset-Allocation Study"),
        ("stage_b_aligned_validation", "Stage B: Aligned Validation"),
        ("stage_c_core_off_weight_and_with_core_vs_no_core", "Stage C: Core-Off Weight / With-Core vs No-Core"),
        ("stage_d_promotion_v1", "Stage D: Promotion V1"),
        ("stage_e_promotion_v2", "Stage E: Promotion V2"),
        ("stage_f_narrow_promotion_and_final_reentry", "Stage F: Narrow Promotion / Final Re-Entry Check"),
    ]
    detail_fields = [
        "caveat",
        "result",
        "evidence_level",
        "recommended_core_off_weight",
        "with_core_vs_no_core",
        "promotion_answer",
        "failure_reason",
        "best_repair_candidate",
        "why_hysteresis_worse",
        "why_two_stage_better",
        "recommendation",
        "final_key_issue",
        "best_candidate",
        "why_still_failed",
        "final_action",
    ]
    for key, title in stage_titles:
        stage = payload["stages"][key]
        lines.extend([
            f"## {title}",
            "",
            f"- Source files: {', '.join(stage['source_files'])}",
            f"- Conclusion: {stage['one_line_conclusion']}",
        ])
        for field in detail_fields:
            if field in stage:
                lines.append(f"- {field}: {stage[field]}")
        lines.append("")
    lines.extend([
        "## Archive Conclusion",
        "",
        f"- Risk-Off directionally valid: {'yes' if payload['final_conclusion']['riskoff_directionally_valid'] else 'no'}",
        f"- Entered baseline: {'yes' if payload['final_conclusion']['riskoff_entered_baseline'] else 'no'}",
        f"- Official status: {payload['final_conclusion']['official_status']}",
        f"- Active mainline statement: {payload['final_conclusion']['active_mainline_statement']}",
        "- Future restart prerequisites:",
    ])
    for item in payload["final_conclusion"]["restart_prerequisites"]:
        lines.append(f"  - {item}")
    lines.append("- Currently forbidden Risk-Off work:")
    for item in payload["final_conclusion"]["currently_forbidden_work"]:
        lines.append(f"  - {item}")
    ARCHIVE_MD.write_text("\n".join(lines), encoding="utf-8")
    ARCHIVE_TXT.write_text(
        "\n".join([
            "riskoff_direction=valid_but_frozen",
            "riskoff_baseline_status=not_in_baseline",
            "promotion_status=frozen",
            "active_mainline=addon_only_on_locked_long_only_mother",
        ]),
        encoding="utf-8",
    )


def write_active_mainline_status() -> None:
    ACTIVE_MAINLINE_MD.write_text(
        "\n".join([
            "# Active Mainline Status",
            "",
            "- Locked baseline: BTC long-only `squeeze_release_20 / lb20_stop3.2_trail5.0_beoff`.",
            "- Default tuple: `next_bar_open + legacy_bar_extrema + midpoint + full_model`.",
            "- Locked baseline structure: `Core BTC holding + current AddOn-only overlay`.",
            "- Frozen direction: Risk-Off remains aligned-but-preliminary and is not part of the baseline.",
            "- Retired direction: old `v85` long+short is not an active mainline.",
            "- Active research from this round: AddOn signal grading only.",
        ]),
        encoding="utf-8",
    )


def write_grading_report(payload: Dict) -> None:
    GRADING_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    best = payload["best_candidate"]
    best_row = payload["candidates"][best]
    lines = [
        "# BTC AddOn Grading Report",
        "",
        "## Final Judgment",
        "",
        f"- AddOn-only baseline improved by grading: {'yes' if payload['judgment']['grading_improves_baseline'] else 'no'}",
        f"- Best grading scheme: {best}",
        f"- Main conclusion: {payload['judgment']['main_conclusion']}",
        f"- Worth formal next-round research: {'yes' if payload['judgment']['worth_next_round_formal_research'] else 'no'}",
        "",
        "## Baseline Alignment",
        "",
        f"- Locked baseline: {payload['locked_baseline']['mainline']} / {payload['locked_baseline']['research_optimal']}",
        f"- Default tuple: {payload['locked_baseline']['default_tuple']}",
        f"- Baseline simulator drift vs committed AddOnOverlay artifact: Return {payload['baseline_alignment_check']['delta_return_pct']:+.2f}pp, Sharpe {payload['baseline_alignment_check']['delta_sharpe']:+.3f}, Calmar {payload['baseline_alignment_check']['delta_calmar']:+.3f}, MaxDD improve {payload['baseline_alignment_check']['delta_maxdd_improve_pct']:+.2f}pp",
        "",
        "## Candidate Table",
        "",
        "| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Exposure% | AddOn active% | dRet vs base | dSharpe | dCalmar | dMaxDD | WF strict | WF dRet | WF dSharpe | WF dCalmar |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, row in payload["candidates"].items():
        m = row["metrics"]
        d = row["delta_vs_addon_baseline"]
        wf = row["walk_forward"]
        lines.append(
            f"| {key} | {m['TotalReturn_pct']:.2f} | {m['CAGR_pct']:.2f} | {m['Sharpe']:.3f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | "
            f"{m['Exposure_pct']:.1f} | {row['addon_active_ratio_pct']:.1f} | {d['Return_pct']:+.2f} | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | "
            f"{d['MaxDD_improvement_pct']:+.2f} | {wf['strict_win_ratio']:.2f} | {wf['avg_delta_return_pct']:+.2f} | {wf['avg_delta_sharpe']:+.3f} | {wf['avg_delta_calmar']:+.3f} |"
        )
    lines.extend([
        "",
        "## Time-Slice Deltas Vs AddOn Baseline",
        "",
        "| Scheme | Bull dRet | Recovery dRet | Major Drawdown dRet | Major Drawdown dMaxDD |",
        "| --- | --- | --- | --- | --- |",
    ])
    for key, row in payload["candidates"].items():
        bull = row["time_slice_deltas"]["bull_expansion"]
        recovery = row["time_slice_deltas"]["recovery_phase"]
        draw = row["time_slice_deltas"]["major_drawdown"]
        lines.append(
            f"| {key} | {bull['Return_pct']:+.2f}pp | {recovery['Return_pct']:+.2f}pp | {draw['Return_pct']:+.2f}pp | {draw['MaxDD_improvement_pct']:+.2f}pp |"
        )
    lines.extend([
        "",
        "## Best Candidate Detail",
        "",
        f"- Best scheme description: {best_row['description']}",
        f"- Grade counts: {json.dumps(best_row['grade_counts'], ensure_ascii=False)}",
        f"- Avg AddOn weight when active: {best_row['avg_addon_weight_when_active']:.3f}",
        f"- Execution stress delta: Return {best_row['execution_stress']['Return_pct']:+.2f}pp, Sharpe {best_row['execution_stress']['Sharpe']:+.3f}, Calmar {best_row['execution_stress']['Calmar']:+.3f}",
        "",
        "## Direct Answers",
        "",
        f"- {payload['judgment']['answer_1']}",
        f"- {payload['judgment']['answer_2']}",
        f"- {payload['judgment']['answer_3']}",
        f"- {payload['judgment']['answer_4']}",
        f"- {payload['judgment']['answer_5']}",
        f"- {payload['judgment']['answer_6']}",
        f"- {payload['judgment']['answer_7']}",
    ])
    GRADING_MD.write_text("\n".join(lines), encoding="utf-8")
    GRADING_TXT.write_text(
        "\n".join([
            f"grading_improves_baseline={payload['judgment']['grading_improves_baseline']}",
            f"best_scheme={best}",
            f"worth_next_round_formal_research={payload['judgment']['worth_next_round_formal_research']}",
            "riskoff_status=frozen_not_in_baseline",
        ]),
        encoding="utf-8",
    )


def main() -> None:
    archive = archive_payload()
    write_archive(archive)
    write_active_mainline_status()

    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    overlay = load_overlay_artifact()

    params_default = current_research_optimal(position_pct=100.0)
    params_stress = with_overrides(
        params_default,
        entry_execution_mode="live_runner_next_5m_close",
        intrabar_execution_model="segment_path_same_bar",
        intrabar_path_mode="pessimistic",
    )

    base_default = prepare_base_run(df_5m, df_4h, params_default)
    base_stress = prepare_base_run(df_5m, df_4h, params_stress)

    baseline_default = simulate_combo_from_plan(df_4h, constant_weight_plan(base_default["entries"], GRADE_WEIGHTS["base"]), float(params_default.commission_pct))
    baseline_stress = simulate_combo_from_plan(df_4h, constant_weight_plan(base_stress["entries"], GRADE_WEIGHTS["base"]), float(params_stress.commission_pct))
    baseline_alignment_check = {
        "simulated_metrics": baseline_default["combo_metrics"],
        "artifact_metrics": overlay["addon_metrics"],
        "delta_return_pct": float(baseline_default["combo_metrics"]["TotalReturn_pct"] - float(overlay["addon_metrics"]["TotalReturn_pct"])),
        "delta_sharpe": float(baseline_default["combo_metrics"]["Sharpe"] - float(overlay["addon_metrics"]["Sharpe"])),
        "delta_calmar": float(baseline_default["combo_metrics"]["Calmar"] - float(overlay["addon_metrics"]["Calmar"])),
        "delta_maxdd_improve_pct": float(abs(float(overlay["addon_metrics"]["MaxDD_pct"])) - abs(baseline_default["combo_metrics"]["MaxDD_pct"])),
    }

    full_results: Dict[str, Dict] = {"Core+AddOnOverlay": baseline_default}
    stress_results: Dict[str, Dict] = {"Core+AddOnOverlay": baseline_stress}
    candidate_rows: Dict[str, Dict] = {}

    for scheme in GRADING_SCHEMES:
        assigned_default, thresholds_default = assign_scheme_weights(
            base_default["entries"],
            scheme,
            pd.Series(True, index=base_default["entries"].index),
        )
        assigned_stress, _ = assign_scheme_weights(
            base_stress["entries"],
            scheme,
            pd.Series(True, index=base_stress["entries"].index),
        )
        key = f"Core+GradedAddOn[{scheme['name']}]"
        default_sim = simulate_combo_from_plan(df_4h, assigned_default, float(params_default.commission_pct))
        stress_sim = simulate_combo_from_plan(df_4h, assigned_stress, float(params_stress.commission_pct))
        full_results[key] = default_sim
        stress_results[key] = stress_sim
        wf = walk_forward_analysis(df_4h, base_default["entries"], base_stress["entries"], scheme, float(params_default.commission_pct))
        candidate_rows[key] = {
            "title": scheme["title"],
            "description": scheme["description"],
            "walk_forward": wf,
            "thresholds_full_sample": thresholds_default,
        }

    slices = time_slice_rows(full_results, "Core+AddOnOverlay")
    stress = stress_compare(full_results, stress_results)
    for key in list(candidate_rows):
        candidate_rows[key] = summarize_scheme(
            name=key,
            title=candidate_rows[key]["title"],
            description=candidate_rows[key]["description"],
            full_sample=full_results[key],
            baseline=baseline_default,
            bh_metrics=overlay["bh_metrics"],
            wf=candidate_rows[key]["walk_forward"],
            slices=slices,
            stress=stress,
        ) | {"thresholds_full_sample": candidate_rows[key]["thresholds_full_sample"]}

    best_key = best_scheme_key(candidate_rows)
    best = candidate_rows[best_key]
    grading_improves = bool(
        best["walk_forward"]["strict_win_ratio"] >= 2.0 / 3.0
        and best["delta_vs_addon_baseline"]["Sharpe"] > 0.0
        and best["delta_vs_addon_baseline"]["Calmar"] >= 0.0
    )
    worth_next_round = bool(
        best["walk_forward"]["strict_win_ratio"] >= 2.0 / 3.0
        and best["walk_forward"]["avg_delta_calmar"] >= 0.0
        and best["causality_violations_default"] == 0
    )

    if best["delta_vs_addon_baseline"]["Return_pct"] > 0 and best["delta_vs_addon_baseline"]["Sharpe"] > 0 and best["delta_vs_addon_baseline"]["Calmar"] > 0:
        improvement_driver = "higher absolute return plus better risk-adjusted performance"
    elif best["delta_vs_addon_baseline"]["Sharpe"] > 0 or best["delta_vs_addon_baseline"]["Calmar"] > 0:
        improvement_driver = "risk-adjusted improvement more than raw-return expansion"
    else:
        improvement_driver = "no robust improvement over the binary AddOn baseline"

    payload = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "locked_baseline": {
            "mainline": "BTC long-only squeeze_release_20",
            "research_optimal": "lb20_stop3.2_trail5.0_beoff",
            "default_tuple": DEFAULT_TUPLE,
            "stress_tuple": STRESS_TUPLE,
            "baseline_status": "AddOn-only remains the locked baseline",
            "riskoff_status": "Frozen aligned-but-preliminary direction. Not in baseline.",
        },
        "grading_framework": {
            "tier_weights": GRADE_WEIGHTS,
            "schemes": GRADING_SCHEMES,
            "note": "No change to AddOn entry/exit mother. Only sleeve size is graded from entry-time signal quality.",
        },
        "baseline_alignment_check": baseline_alignment_check,
        "reference_systems": {
            "B&H": overlay["bh_metrics"],
            "Core+AddOnOverlay": baseline_default["combo_metrics"],
        },
        "time_slices": slices,
        "execution_stress": stress,
        "candidates": candidate_rows,
        "best_candidate": best_key,
        "judgment": {
            "grading_improves_baseline": grading_improves,
            "best_scheme": best_key,
            "main_conclusion": (
                f"{best_key} is the most reasonable graded AddOn variant, and it is worth a formal next-round study, but it still does not justify baseline promotion."
                if worth_next_round
                else f"{best_key} is the most reasonable graded AddOn variant, but it still does not justify baseline promotion."
            ),
            "improvement_driver": improvement_driver,
            "worth_next_round_formal_research": worth_next_round,
            "answer_1": (
                f"Yes. The current AddOn-only baseline can be improved by grading, with {best_key} producing the best combined full-sample and OOS profile."
                if grading_improves
                else f"No clear formal upgrade is proven. {best_key} is the best exploratory grading variant, but the improvement is not strong enough to rewrite the binary AddOn baseline."
            ),
            "answer_2": f"The most reasonable grading scheme is {best_key}, because it leads the small candidate set on OOS strict ratio and full-sample risk-adjusted deltas without changing the mother logic.",
            "answer_3": f"The improvement mainly comes from {improvement_driver}.",
            "answer_4": (
                "Yes. The best graded sleeve is worth a next-round formal study."
                if worth_next_round
                else "Not yet. The best graded sleeve is promising, but it should stay at exploratory/aligned-research status for now."
            ),
            "answer_5": "Current Risk-Off status is frozen: directionally valid, execution-aligned, repeatedly failed promotion, and not part of the baseline.",
            "answer_6": "No. The team should not continue Risk-Off promotion on the same frozen line.",
            "answer_7": "The active mainline is the locked BTC long-only mother with AddOn-only baseline semantics; Risk-Off is archived and frozen, while AddOn grading is the active extension line.",
        },
    }
    write_grading_report(payload)
    print(
        json.dumps(
            {
                "archive": "done",
                "best_grading_scheme": best_key,
                "grading_improves_baseline": grading_improves,
                "worth_next_round_formal_research": worth_next_round,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
