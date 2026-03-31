#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S2 audit for the range_rotation_mean_reversion second-sleeve family."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_addon_exposure_repair_audit import enrich_entries
from v90_addon_grading_promotion_validation import DEFAULT_TUPLE, STRESS_TUPLE, TIME_SLICES
from v90_addon_grading_study import (
    GRADE_WEIGHTS,
    SEED,
    compute_metrics,
    compute_slice_metrics,
    constant_weight_plan,
    current_research_optimal,
    delta_metrics,
    prepare_base_run,
    simulate_combo_from_plan,
    slice_range,
    stress_compare,
    with_overrides,
)
from v90_trend_long_mother import TrendIndicatorEngine, TrendLongMotherEngine, TrendLongParams, behavior_stats
from v91_exposure_engine_e1_constant_mapping import archived_repair_plan, extended_metrics


STANDALONE_MD = Path("RANGE_ROTATION_MEAN_REVERSION_STANDALONE_AUDIT.md")
COMPLEMENT_MD = Path("RANGE_ROTATION_MEAN_REVERSION_COMPLEMENTARITY_AUDIT.md")
DECISION_MD = Path("RANGE_ROTATION_MEAN_REVERSION_DECISION.md")
REPORT_JSON = Path("range_rotation_mean_reversion_audit.json")

BINARY_WEIGHT = GRADE_WEIGHTS["base"]
CONST_WEIGHT = 1.00
INIT_EQUITY = 10000.0


def make_range_rotation_params(**overrides) -> TrendLongParams:
    params = TrendLongParams(
        candidate_name="range_rotation_mean_reversion",
        description="Capture BTC lower-range rotation back toward the range midpoint inside a still-bullish higher-timeframe backdrop, without relying on fresh breakout expansion.",
        breakout_mode="range_rotation_mean_reversion",
        donchian_entry_len=18,
        adx_min=0.0,
        use_adx_filter=False,
        use_ema_slope=False,
        close_location_min=0.55,
        range_atr_min=0.35,
        initial_stop_atr=2.2,
        trail_atr_mult=3.6,
        trail_activate_atr=1.4,
        use_swing_trail=True,
        swing_trail_lookback=8,
        break_even_after_atr=1e9,
    )
    return with_overrides(params, **overrides)


class RangeRotationMeanReversionEngine(TrendLongMotherEngine):
    def _prepare(self, df_4h: pd.DataFrame) -> pd.DataFrame:
        out = TrendIndicatorEngine().compute(df_4h, self.tp)
        out["ema_fast"] = TrendIndicatorEngine.calc_ema(out["close"], 20)
        out["ema_mid"] = TrendIndicatorEngine.calc_ema(out["close"], 50)
        out["ema_slope_atr"] = np.where(out["atr"] > 0, out["ema_slope"] / out["atr"], 0.0)
        out["range_high_20"] = out["high"].shift(1).rolling(20).max()
        out["range_low_20"] = out["low"].shift(1).rolling(20).min()
        out["range_mid_20"] = (out["range_high_20"] + out["range_low_20"]) / 2.0
        out["range_width"] = out["range_high_20"] - out["range_low_20"]
        out["range_width_atr"] = np.where(out["atr"] > 0, out["range_width"] / out["atr"], 0.0)
        out["range_position"] = np.where(out["range_width"] > 0, (out["close"] - out["range_low_20"]) / out["range_width"], 0.5)
        out["lower_rotation_zone"] = out["range_low_20"] + out["range_width"] * 0.35
        out["upper_rotation_cap"] = out["range_low_20"] + out["range_width"] * 0.85
        out["reclaim_high_2"] = out["high"].shift(1).rolling(2).max()
        out["rotation_pivot_low_5"] = out["low"].shift(1).rolling(5).min()
        out["touch_lower_rotation"] = (
            (out["low"] <= out["lower_rotation_zone"])
            & (out["range_position"] <= 0.45)
            & (out["close"] > out["range_low_20"])
        )
        out["recent_lower_rotation_touch"] = out["touch_lower_rotation"].shift(1).rolling(6).max().fillna(0).astype(bool)
        out["rotation_reclaim_ok"] = (
            (out["close"] > out["reclaim_high_2"])
            & (out["close"] > out["ema_fast"])
            & (out["close"] >= out["range_mid_20"])
            & (out["close_location"] >= 0.55)
            & (out["close"] <= out["upper_rotation_cap"])
        )
        out["bullish_backdrop_ok"] = (
            (out["close"] > out["ema"])
            & (out["ema_mid"] >= out["ema"])
            & (out["ema_slope_atr"] > -0.08)
        )
        out["rotation_context_ok"] = (
            (out["range_width_atr"] >= 2.5)
            & (out["range_width_atr"] <= 7.5)
            & (out["adx"] <= 28.0)
            & (out["bb_width_norm"] <= 1.15)
        )
        out["range_rotation_entry"] = (
            out["recent_lower_rotation_touch"]
            & out["rotation_reclaim_ok"]
            & out["bullish_backdrop_ok"]
            & out["rotation_context_ok"]
        )
        return out

    def _entry_signal(self, row: pd.Series, prev_row: pd.Series) -> bool:
        return bool(row["range_rotation_entry"])

    def _entry_stop(self, signal_row: pd.Series, entry_reference_price: float) -> float:
        atr_stop = float(entry_reference_price) - self.tp.initial_stop_atr * float(signal_row["atr"])
        pivot_low = float(signal_row["rotation_pivot_low_5"]) if pd.notna(signal_row["rotation_pivot_low_5"]) else atr_stop
        return max(atr_stop, pivot_low)


def run_range_rotation_candidate(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams) -> Dict:
    engine = RangeRotationMeanReversionEngine(params, use_intrabar_stop=True)
    return engine.run(df_5m, df_4h)


def normalize_candidate_sleeve(result: Dict, df_4h: pd.DataFrame, weight: float = 1.0) -> Dict:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    eq = result["equity"].copy()
    if eq.empty:
        series = pd.DataFrame(index=d4.index, data={"equity": INIT_EQUITY, "position": 0.0})
    else:
        series = eq.reindex(d4.index)
        series["equity"] = series["equity"].ffill().fillna(INIT_EQUITY)
        series["position"] = series["position"].ffill().fillna(0.0)
    sleeve_equity = series["equity"].astype(float)
    sleeve_weight = series["position"].astype(float) * float(weight)
    return {
        "equity": sleeve_equity,
        "weight": sleeve_weight,
        "active_ratio_pct": float((sleeve_weight > 0.0).mean() * 100.0),
        "avg_weight_when_active": float(sleeve_weight[sleeve_weight > 0.0].mean()) if (sleeve_weight > 0.0).any() else 0.0,
    }


def combine_with_const1x(df_4h: pd.DataFrame, const_sim: Dict, candidate_sleeve: Dict) -> Dict:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    bh = const_sim["combo_equity"] - (const_sim["sleeve"]["equity"] - INIT_EQUITY)
    combo_equity = bh + (const_sim["sleeve"]["equity"] - INIT_EQUITY) + (candidate_sleeve["equity"] - INIT_EQUITY)
    combo_exposure = 1.0 + const_sim["sleeve"]["weight"].reindex(d4.index).fillna(0.0) + candidate_sleeve["weight"].reindex(d4.index).fillna(0.0)
    return {
        "combo_equity": combo_equity.astype(float),
        "combo_exposure": combo_exposure.astype(float),
        "combo_metrics": compute_metrics(combo_equity.astype(float), combo_exposure.astype(float)),
    }


def extended_portfolio_metrics(portfolio: Dict) -> Dict:
    return extended_metrics({"combo_metrics": portfolio["combo_metrics"], "combo_equity": portfolio["combo_equity"]})


def normalize_standalone_metrics(stats: Dict) -> Dict:
    cagr_raw = float(stats.get("CAGR", 0.0))
    maxdd_raw = float(stats.get("MaxDD_pct", 0.0))
    cagr_pct = cagr_raw * 100.0 if abs(cagr_raw) <= 5.0 else cagr_raw
    maxdd_pct = maxdd_raw * 100.0 if abs(maxdd_raw) <= 5.0 else maxdd_raw
    calmar = float(cagr_pct / abs(maxdd_pct)) if maxdd_pct < 0.0 else 0.0
    return {
        "TotalReturn_pct": float(stats.get("TotalReturn_pct", 0.0)),
        "CAGR_pct": float(cagr_pct),
        "Sharpe": float(stats.get("Sharpe", 0.0)),
        "Calmar": float(calmar),
        "MaxDD_pct": float(maxdd_pct),
        "Trades": int(stats.get("Trades", 0)),
    }


def yearly_metrics_from_equity(equity: pd.Series, exposure: pd.Series) -> List[Dict]:
    rows: List[Dict] = []
    years = sorted(equity.index.year.unique().tolist())
    for year in years:
        start = pd.Timestamp(f"{year}-01-01", tz="UTC")
        end = pd.Timestamp(f"{year + 1}-01-01", tz="UTC")
        sub_eq = slice_range(equity, start.isoformat(), end.isoformat())
        sub_ex = slice_range(exposure, start.isoformat(), end.isoformat())
        if len(sub_eq) < 2:
            continue
        metrics = compute_slice_metrics(sub_eq, sub_ex)
        rows.append({"year": int(year), **metrics})
    return rows


def trade_clustering(meta: pd.DataFrame) -> Dict:
    if meta is None or meta.empty:
        return {
            "trade_count": 0,
            "entries_per_year": {},
            "entries_per_month_top3_share_pct": 0.0,
            "longest_gap_days": 0.0,
        }
    tmp = meta.copy()
    tmp["entry_time"] = pd.to_datetime(tmp["entry_time"], utc=True)
    year_counts = tmp["entry_time"].dt.year.value_counts().sort_index().to_dict()
    month_counts = tmp["entry_time"].dt.tz_localize(None).dt.to_period("M").value_counts().sort_values(ascending=False)
    top3_share = float(month_counts.head(3).sum() / len(tmp) * 100.0) if len(tmp) else 0.0
    gaps = tmp["entry_time"].sort_values().diff().dropna().dt.total_seconds() / 86400.0
    return {
        "trade_count": int(len(tmp)),
        "entries_per_year": {str(int(k)): int(v) for k, v in year_counts.items()},
        "entries_per_month_top3_share_pct": top3_share,
        "longest_gap_days": float(gaps.max()) if not gaps.empty else 0.0,
    }


def overlap_diagnostics(current_sleeve: Dict, candidate_sleeve: Dict, candidate_meta: pd.DataFrame) -> Dict:
    cur_active = current_sleeve["weight"] > 0.0
    cand_active = candidate_sleeve["weight"] > 0.0
    overlap = cur_active & cand_active
    cand_only = cand_active & ~cur_active
    cur_only = cur_active & ~cand_active

    entry_overlap_pct = 0.0
    entries_when_current_flat_pct = 0.0
    if candidate_meta is not None and not candidate_meta.empty:
        tmp = candidate_meta.copy()
        tmp["entry_time"] = pd.to_datetime(tmp["entry_time"], utc=True)
        entry_bars = tmp["entry_time"].dt.floor("4h")
        states = cur_active.reindex(entry_bars).fillna(False).astype(bool)
        entry_overlap_pct = float(states.mean() * 100.0)
        entries_when_current_flat_pct = float((~states).mean() * 100.0)

    ret_cur = current_sleeve["equity"].pct_change().fillna(0.0)
    ret_cand = candidate_sleeve["equity"].pct_change().fillna(0.0)
    either_active = (cur_active | cand_active)
    corr = float(ret_cur[either_active].corr(ret_cand[either_active])) if either_active.any() else 0.0

    cand_pnl = candidate_sleeve["equity"].diff().fillna(0.0)
    pnl_share = 0.0
    gross_abs = float(cand_pnl.abs().sum())
    if gross_abs > 1e-12:
        pnl_share = float(cand_pnl[~cur_active].abs().sum() / gross_abs * 100.0)
    return {
        "current_active_ratio_pct": float(cur_active.mean() * 100.0),
        "candidate_active_ratio_pct": float(cand_active.mean() * 100.0),
        "active_overlap_ratio_pct": float(overlap.mean() * 100.0),
        "candidate_only_active_ratio_pct": float(cand_only.mean() * 100.0),
        "current_only_active_ratio_pct": float(cur_only.mean() * 100.0),
        "candidate_entry_overlap_with_current_pct": entry_overlap_pct,
        "candidate_entries_when_current_flat_pct": entries_when_current_flat_pct,
        "active_return_correlation": corr,
        "candidate_abs_pnl_when_current_flat_pct_of_total_abs": pnl_share,
    }


def slice_table(systems: Dict[str, Dict]) -> List[Dict]:
    rows = []
    for sl in TIME_SLICES:
        row = {"slice": sl["name"], "window": {"start": sl["start"], "end": sl["end"]}}
        for key, item in systems.items():
            row[key] = compute_slice_metrics(
                slice_range(item["equity"], sl["start"], sl["end"]),
                slice_range(item["exposure"], sl["start"], sl["end"]),
            )
        row["plus_range_rotation_vs_const1x"] = delta_metrics(
            row["Core+ConstAddOn[1.00x]+RangeRotation"], row["Core+ConstAddOn[1.00x]"]
        )
        rows.append(row)
    return rows


def early_recovery_window(current_sleeve: Dict) -> Dict:
    dd = current_sleeve["equity"] / current_sleeve["equity"].cummax() - 1.0
    trough = dd.idxmin()
    end = trough + timedelta(days=180)
    return {"start": trough.isoformat(), "end": end.isoformat()}


def window_metrics(system: Dict, start: str, end: str) -> Dict:
    return compute_slice_metrics(slice_range(system["equity"], start, end), slice_range(system["exposure"], start, end))


def write_reports(payload: Dict) -> None:
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    st = payload["standalone"]
    lines = [
        "# Range Rotation Mean Reversion Standalone Audit",
        "",
        "## Summary",
        "",
        f"- Candidate: `{payload['candidate_name']}`",
        f"- Default TotalReturn / MaxDD / Sharpe: {st['default']['metrics']['TotalReturn_pct']:.2f}% / {st['default']['metrics']['MaxDD_pct']:.2f}% / {st['default']['metrics']['Sharpe']:.3f}",
        f"- Stress delta: Return {st['stress_vs_default']['Return_pct']:+.2f}pp, MaxDD {st['stress_vs_default']['MaxDD_improvement_pct']:+.2f}pp",
        "",
        "## Trade Behavior",
        "",
        f"- Trade count: {st['trade_clustering']['trade_count']}",
        f"- Avg hold 4H bars: {st['behavior']['avg_hold_4h_bars']:.1f}",
        f"- Median hold 4H bars: {st['behavior']['median_hold_4h_bars']:.1f}",
        f"- Win rate: {st['trade_stats']['win_rate_pct']:.1f}%",
        f"- Avg trade pnl: {st['trade_stats']['avg_trade_pnl_pct']:+.2f}%",
        f"- Top 3 entry-month concentration: {st['trade_clustering']['entries_per_month_top3_share_pct']:.1f}%",
        "",
        "## Yearly Standalone Metrics",
        "",
        "| Year | Return | Sharpe | MaxDD | Trades |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in st["yearly"]:
        lines.append(
            f"| {row['year']} | {row['TotalReturn_pct']:.2f}% | {row['Sharpe']:.3f} | {row['MaxDD_pct']:.2f}% | {row.get('Trades', 0)} |"
        )
    STANDALONE_MD.write_text("\n".join(lines), encoding="utf-8")

    comp = payload["complementarity"]
    lines = [
        "# Range Rotation Mean Reversion Complementarity Audit",
        "",
        "## Full-Sample Comparison",
        "",
        "| System | TotalReturn | MaxDD | Calmar | Ulcer | AvgExposure |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key in ["CoreOnly", "Core+BinaryAddOn", "Core+ConstAddOn[1.00x]", "Core+ConstAddOn[1.00x]+RangeRotation"]:
        row = comp["systems"][key]["metrics"]
        lines.append(
            f"| {key} | {row['TotalReturn_pct']:.2f}% | {row['MaxDD_pct']:.2f}% | {row['Calmar']:.3f} | {row['UlcerIndex']:.2f} | {row['Exposure_pct']:.2f}% |"
        )
    lines.extend([
        "",
        "## Incremental Effect Vs Const1x",
        "",
        f"- dReturn: {comp['delta_vs_const1x']['Return_pct']:+.2f}pp",
        f"- dMaxDD: {comp['delta_vs_const1x']['MaxDD_improvement_pct']:+.2f}pp",
        f"- dCalmar: {comp['delta_vs_const1x']['Calmar']:+.3f}",
        f"- dSharpe: {comp['delta_vs_const1x']['Sharpe']:+.3f}",
        "",
        "## Orthogonality",
        "",
        f"- Active overlap ratio: {comp['orthogonality']['active_overlap_ratio_pct']:.2f}%",
        f"- Candidate-only active ratio: {comp['orthogonality']['candidate_only_active_ratio_pct']:.2f}%",
        f"- Candidate entries when current sleeve is flat: {comp['orthogonality']['candidate_entries_when_current_flat_pct']:.1f}%",
        f"- Active return correlation: {comp['orthogonality']['active_return_correlation']:.3f}",
        "",
        "## Major Slices",
        "",
        "| Slice | dReturn vs Const1x | dMaxDD vs Const1x |",
        "| --- | --- | --- |",
    ])
    for row in comp["time_slices"]:
        d = row["plus_range_rotation_vs_const1x"]
        lines.append(f"| {row['slice']} | {d['Return_pct']:+.2f}pp | {d['MaxDD_improvement_pct']:+.2f}pp |")
    lines.extend([
        "",
        "## Early Recovery Window",
        "",
        f"- Window: {comp['early_recovery_window']['start'][:10]} -> {comp['early_recovery_window']['end'][:10]}",
        f"- dReturn vs Const1x: {comp['early_recovery_delta_vs_const1x']['Return_pct']:+.2f}pp",
        f"- dMaxDD vs Const1x: {comp['early_recovery_delta_vs_const1x']['MaxDD_improvement_pct']:+.2f}pp",
    ])
    COMPLEMENT_MD.write_text("\n".join(lines), encoding="utf-8")

    dec = payload["decision"]
    lines = [
        "# Range Rotation Mean Reversion Decision",
        "",
        "## Final Judgment",
        "",
        f"- Candidate status: {dec['status']}",
        f"- Decision: {dec['action']}",
        "",
        "## Direct Answers",
        "",
        f"1. Is range_rotation_mean_reversion a real Sleeve #2 candidate? {dec['answer_1']}",
        f"2. Where exactly does it help or fail? {dec['answer_2']}",
        f"3. Is the edge complementary or mostly redundant? {dec['answer_3']}",
        f"4. Should S3 advance this family, reject it, or hold it as secondary priority? {dec['answer_4']}",
    ]
    DECISION_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    params_default = make_range_rotation_params()
    params_stress = with_overrides(
        params_default,
        entry_execution_mode="live_runner_next_5m_close",
        intrabar_execution_model="segment_path_same_bar",
        intrabar_path_mode="pessimistic",
    )

    range_default = run_range_rotation_candidate(df_5m, df_4h, params_default)
    range_stress = run_range_rotation_candidate(df_5m, df_4h, params_stress)
    range_default_sleeve = normalize_candidate_sleeve(range_default, df_4h, weight=1.0)
    range_stress_sleeve = normalize_candidate_sleeve(range_stress, df_4h, weight=1.0)

    core_base = prepare_base_run(df_5m, df_4h, current_research_optimal(position_pct=100.0))
    current_entries = core_base["entries"]
    current_enriched = enrich_entries(core_base, df_4h)
    core_only = simulate_combo_from_plan(df_4h, constant_weight_plan(current_entries, 0.0), float(current_research_optimal().commission_pct))
    binary = simulate_combo_from_plan(df_4h, constant_weight_plan(current_entries, BINARY_WEIGHT), float(current_research_optimal().commission_pct))
    const1x = simulate_combo_from_plan(df_4h, constant_weight_plan(current_entries, CONST_WEIGHT), float(current_research_optimal().commission_pct))
    archived = simulate_combo_from_plan(df_4h, archived_repair_plan(current_enriched, pd.Series(True, index=current_enriched.index)), float(current_research_optimal().commission_pct))
    plus_range_rotation = combine_with_const1x(df_4h, const1x, range_default_sleeve)

    systems = {
        "CoreOnly": {"equity": core_only["combo_equity"], "exposure": core_only["combo_exposure"], "metrics": extended_metrics(core_only)},
        "Core+BinaryAddOn": {"equity": binary["combo_equity"], "exposure": binary["combo_exposure"], "metrics": extended_metrics(binary)},
        "Core+ConstAddOn[1.00x]": {"equity": const1x["combo_equity"], "exposure": const1x["combo_exposure"], "metrics": extended_metrics(const1x)},
        "Core+ConstAddOn[1.00x]+RangeRotation": {
            "equity": plus_range_rotation["combo_equity"],
            "exposure": plus_range_rotation["combo_exposure"],
            "metrics": extended_portfolio_metrics(plus_range_rotation),
        },
    }

    current_sleeve = {"equity": const1x["sleeve"]["equity"], "weight": const1x["sleeve"]["weight"]}
    orth = overlap_diagnostics(current_sleeve, range_default_sleeve, range_default.get("trade_meta"))
    slices = slice_table(systems)
    early_window = early_recovery_window(systems["Core+ConstAddOn[1.00x]"])
    early_const = window_metrics(systems["Core+ConstAddOn[1.00x]"], early_window["start"], early_window["end"])
    early_plus = window_metrics(systems["Core+ConstAddOn[1.00x]+RangeRotation"], early_window["start"], early_window["end"])

    trades = range_default["trades"].copy()
    trade_meta = range_default.get("trade_meta")
    avg_trade_move_pct = 0.0
    if trade_meta is not None and not trade_meta.empty:
        tmp_meta = trade_meta.copy()
        avg_trade_move_pct = float((tmp_meta["exit_price"].astype(float) / tmp_meta["entry_price"].astype(float) - 1.0).mean() * 100.0)
    trade_stats = {
        "trade_count": int(len(trades)) if not trades.empty else 0,
        "win_rate_pct": float((trades["pnl"] > 0).mean() * 100.0) if not trades.empty else 0.0,
        "avg_trade_pnl_pct": avg_trade_move_pct,
    }
    behavior = behavior_stats(range_default, df_5m)
    standalone_default_metrics = normalize_standalone_metrics(range_default["stats"])
    standalone_stress_metrics = normalize_standalone_metrics(range_stress["stats"])
    standalone_yearly = []
    for row in yearly_metrics_from_equity(range_default_sleeve["equity"], range_default_sleeve["weight"]):
        year = row["year"]
        year_trades = 0
        if range_default.get("trade_meta") is not None and not range_default["trade_meta"].empty:
            tmp = range_default["trade_meta"].copy()
            tmp["entry_time"] = pd.to_datetime(tmp["entry_time"], utc=True)
            year_trades = int((tmp["entry_time"].dt.year == year).sum())
        standalone_yearly.append({**row, "Trades": year_trades})

    standalone_directionally_valid = bool(
        standalone_default_metrics["Trades"] >= 20
        and standalone_default_metrics["Sharpe"] > 0.15
        and float(standalone_default_metrics["TotalReturn_pct"]) > 0.0
    )
    complement_useful = bool(
        delta_metrics(plus_range_rotation["combo_metrics"], const1x["combo_metrics"])["Calmar"] > 0.0
        or delta_metrics(plus_range_rotation["combo_metrics"], const1x["combo_metrics"])["MaxDD_improvement_pct"] > 0.0
        or delta_metrics(early_plus, early_const)["MaxDD_improvement_pct"] > 0.0
    )
    sufficiently_orthogonal = bool(
        orth["active_overlap_ratio_pct"] < 12.0
        and orth["candidate_entries_when_current_flat_pct"] >= 50.0
    )

    if standalone_directionally_valid and complement_useful and sufficiently_orthogonal:
        status = "real Sleeve #2 candidate"
        action = "advance to S3 shortlist"
    elif standalone_directionally_valid and sufficiently_orthogonal:
        status = "secondary-priority candidate"
        action = "hold as secondary priority"
    else:
        status = "not a real Sleeve #2 candidate"
        action = "reject for S3"

    payload = {
        "generated_at_local": datetime.now().isoformat(),
        "candidate_name": "range_rotation_mean_reversion",
        "locked_context": {
            "baseline": "Core BTC holding + ConstAddOn[1.00x]",
            "current_sleeve": "squeeze_release_20 / lb20_stop3.2_trail5.0_beoff",
            "default_tuple": DEFAULT_TUPLE,
            "stress_tuple": STRESS_TUPLE,
        },
        "standalone": {
            "default": {"metrics": standalone_default_metrics, "params": asdict(params_default)},
            "stress": {"metrics": standalone_stress_metrics, "params": asdict(params_stress)},
            "stress_vs_default": delta_metrics(standalone_stress_metrics, standalone_default_metrics),
            "behavior": behavior,
            "trade_clustering": trade_clustering(range_default.get("trade_meta")),
            "trade_stats": trade_stats,
            "yearly": standalone_yearly,
        },
        "complementarity": {
            "systems": systems,
            "delta_vs_const1x": delta_metrics(plus_range_rotation["combo_metrics"], const1x["combo_metrics"]),
            "delta_vs_binary": delta_metrics(plus_range_rotation["combo_metrics"], binary["combo_metrics"]),
            "delta_vs_archived": delta_metrics(plus_range_rotation["combo_metrics"], archived["combo_metrics"]),
            "orthogonality": orth,
            "time_slices": slices,
            "early_recovery_window": early_window,
            "early_recovery_delta_vs_const1x": delta_metrics(early_plus, early_const),
        },
        "decision": {
            "status": status,
            "action": action,
            "answer_1": "Yes." if status == "real Sleeve #2 candidate" else "No." if status == "not a real Sleeve #2 candidate" else "Not yet, but it remains directionally interesting.",
            "answer_2": (
                f"It helps most where the current sleeve is absent or late. Candidate entries occur with the current sleeve flat {orth['candidate_entries_when_current_flat_pct']:.1f}% of the time. "
                f"Portfolio effect vs Const1x is dReturn {delta_metrics(plus_range_rotation['combo_metrics'], const1x['combo_metrics'])['Return_pct']:+.2f}pp and "
                f"dMaxDD {delta_metrics(plus_range_rotation['combo_metrics'], const1x['combo_metrics'])['MaxDD_improvement_pct']:+.2f}pp, while early-recovery delta is "
                f"dReturn {delta_metrics(early_plus, early_const)['Return_pct']:+.2f}pp and dMaxDD {delta_metrics(early_plus, early_const)['MaxDD_improvement_pct']:+.2f}pp."
            ),
            "answer_3": (
                "Complementary."
                if sufficiently_orthogonal and complement_useful
                else "Mostly redundant."
                if orth["active_overlap_ratio_pct"] >= 12.0
                else "Orthogonal in timing, but not useful enough yet."
            ),
            "answer_4": (
                "Advance this family to S3."
                if action == "advance to S3 shortlist"
                else "Reject it."
                if action == "reject for S3"
                else "Hold it as secondary priority."
            ),
        },
    }
    write_reports(payload)
    print(
        json.dumps(
            {
                "status": status,
                "action": action,
                "standalone_return": standalone_default_metrics["TotalReturn_pct"],
                "standalone_maxdd": standalone_default_metrics["MaxDD_pct"],
                "delta_vs_const1x": payload["complementarity"]["delta_vs_const1x"],
                "orthogonality": orth,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
