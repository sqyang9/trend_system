#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run a disciplined 10-direction low-value core re-entry sweep on top of RO_EMA220_REENTRY_CLOSE_HOLD_3."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import plotly.graph_objects as go

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
from v90_trend_long_mother import SEED


REPORT_MD = Path("RISK_OFF_LOWVALUE_REENTRY_REPORT.md")
REPORT_JSON = Path("risk_off_lowvalue_reentry_report.json")
CURVES_HTML = Path("RISK_OFF_LOWVALUE_REENTRY_EQUITY_CURVES.html")

ARCHIVED_BASELINE = {
    "name": "RO_EMA220_FLAT",
    "kind": "flat_reference",
    "description": "Archived flat Risk-Off baseline.",
}
BEST_ARCHIVED_REPAIR = {
    "name": "RO_EMA220_REENTRY_CLOSE_HOLD_3",
    "kind": "close_hold_3",
    "description": "Archived best re-entry repair: flat exits directly back to 100% after three close>EMA220 bars.",
}

CANDIDATES: List[Dict] = [
    {
        "name": "RO_LOWVALUE_WEEKLY_RSI35_HOLD",
        "kind": "weekly_rsi_hold",
        "description": "Weekly RSI(14) <= 35 triggers early full-core restoration and hold.",
        "timeframe": "W-SUN",
        "period": 14,
        "threshold": 35.0,
    },
    {
        "name": "RO_LOWVALUE_WEEKLY_RSI30_HOLD",
        "kind": "weekly_rsi_hold",
        "description": "Weekly RSI(14) <= 30 triggers deeper-oversold full-core restoration and hold.",
        "timeframe": "W-SUN",
        "period": 14,
        "threshold": 30.0,
    },
    {
        "name": "RO_LOWVALUE_DAILY_RSI15_HOLD",
        "kind": "daily_rsi_hold",
        "description": "Daily RSI(14) <= 15 triggers extreme daily oversold full-core restoration and hold.",
        "timeframe": "1D",
        "period": 14,
        "threshold": 15.0,
    },
    {
        "name": "RO_LOWVALUE_4H_RSI10_HOLD",
        "kind": "h4_rsi_hold",
        "description": "4h RSI(14) <= 10 triggers immediate capitulation-style full-core restoration and hold.",
        "period": 14,
        "threshold": 10.0,
    },
    {
        "name": "RO_LOWVALUE_EMA220_ATR_DISLOCATION",
        "kind": "ema_atr_dislocation",
        "description": "Re-enter when close is more than 4 ATR below EMA220.",
        "distance_atr": -4.0,
    },
    {
        "name": "RO_LOWVALUE_PANIC_RANGE_EXPANSION",
        "kind": "panic_range",
        "description": "Re-enter on panic range expansion with exhaustion-like close location.",
        "bar_range_atr_min": 2.2,
        "close_location_min": 0.55,
    },
    {
        "name": "RO_LOWVALUE_RANGE_BOTTOM_PERCENTILE",
        "kind": "range_bottom",
        "description": "Re-enter when price sits in the bottom 5% of its recent 90-bar range.",
        "lookback": 90,
        "range_pos_max": 0.05,
    },
    {
        "name": "RO_LOWVALUE_BB_ZSCORE",
        "kind": "bb_zscore",
        "description": "Re-enter on deep Bollinger z-score oversold.",
        "window": 20,
        "zscore_max": -2.5,
    },
    {
        "name": "RO_LOWVALUE_FLUSH_REVERSAL",
        "kind": "flush_reversal",
        "description": "Re-enter after a large panic bar with long lower wick and strong close location.",
        "bar_range_atr_min": 1.8,
        "lower_wick_ratio_min": 0.45,
        "close_location_min": 0.65,
    },
    {
        "name": "RO_LOWVALUE_DRAWDOWN_60D",
        "kind": "deep_drawdown",
        "description": "Re-enter when price is 25% below the rolling 60-day high.",
        "drawdown_max": -0.25,
        "lookback_bars": 360,
    },
]


def build_bearish_and_reentry(indicators: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
    bearish = (indicators["close"] < indicators["ema"]) & (indicators["ema_slope"] < 0)
    close_confirm = indicators["close"] > indicators["ema"]
    slope_confirm = close_confirm & (indicators["ema_slope"] > 0)
    return bearish.fillna(False), close_confirm.fillna(False), slope_confirm.fillna(False)


def compute_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def enrich_indicators(indicators: pd.DataFrame) -> pd.DataFrame:
    out = indicators.copy()
    out["ema_fast"] = out["close"].ewm(span=20, adjust=False).mean()
    out["bar_range"] = (out["high"] - out["low"]).clip(lower=0.0)
    out["dist_ema_atr"] = np.where(out["atr"] > 0, (out["close"] - out["ema"]) / out["atr"], 0.0)

    rng_hi = out["high"].rolling(90, min_periods=20).max()
    rng_lo = out["low"].rolling(90, min_periods=20).min()
    rng_w = (rng_hi - rng_lo).replace(0.0, np.nan)
    out["range_pos_90"] = ((out["close"] - rng_lo) / rng_w).fillna(0.5)

    ma20 = out["close"].rolling(20, min_periods=20).mean()
    std20 = out["close"].rolling(20, min_periods=20).std()
    out["bb_zscore_20"] = ((out["close"] - ma20) / std20.replace(0.0, np.nan)).fillna(0.0)

    lower_wick = (np.minimum(out["open"], out["close"]) - out["low"]).clip(lower=0.0)
    out["lower_wick_ratio"] = (lower_wick / out["bar_range"].replace(0.0, np.nan)).fillna(0.0)

    roll_high_60d = out["close"].rolling(360, min_periods=60).max()
    out["drawdown_from_60d_high"] = (out["close"] / roll_high_60d - 1.0).fillna(0.0)

    weekly_close = out["close"].resample("W-SUN").last()
    daily_close = out["close"].resample("1D").last()
    out["weekly_rsi14"] = compute_rsi(weekly_close, 14).reindex(out.index, method="ffill")
    out["daily_rsi14"] = compute_rsi(daily_close, 14).reindex(out.index, method="ffill")
    out["h4_rsi14"] = compute_rsi(out["close"].astype(float), 14)
    return out


def candidate_trigger(indicators: pd.DataFrame, candidate: Dict) -> pd.Series:
    kind = candidate["kind"]
    if kind == "weekly_rsi_hold":
        return (indicators["weekly_rsi14"] <= float(candidate["threshold"])).fillna(False)
    if kind == "daily_rsi_hold":
        return (indicators["daily_rsi14"] <= float(candidate["threshold"])).fillna(False)
    if kind == "h4_rsi_hold":
        return (indicators["h4_rsi14"] <= float(candidate["threshold"])).fillna(False)
    if kind == "ema_atr_dislocation":
        return (indicators["dist_ema_atr"] <= float(candidate["distance_atr"])).fillna(False)
    if kind == "panic_range":
        return (
            (indicators["bar_range_atr"] >= float(candidate["bar_range_atr_min"]))
            & (indicators["close_location"] >= float(candidate["close_location_min"]))
        ).fillna(False)
    if kind == "range_bottom":
        return (indicators["range_pos_90"] <= float(candidate["range_pos_max"])).fillna(False)
    if kind == "bb_zscore":
        return (indicators["bb_zscore_20"] <= float(candidate["zscore_max"])).fillna(False)
    if kind == "flush_reversal":
        return (
            (indicators["bar_range_atr"] >= float(candidate["bar_range_atr_min"]))
            & (indicators["lower_wick_ratio"] >= float(candidate["lower_wick_ratio_min"]))
            & (indicators["close_location"] >= float(candidate["close_location_min"]))
        ).fillna(False)
    if kind == "deep_drawdown":
        return (indicators["drawdown_from_60d_high"] <= float(candidate["drawdown_max"])).fillna(False)
    raise ValueError(f"Unknown candidate kind: {kind}")


def build_target(indicators: pd.DataFrame, candidate: Dict) -> pd.Series:
    bearish, close_confirm, _ = build_bearish_and_reentry(indicators)

    if candidate["kind"] == "flat_reference":
        return pd.Series(np.where(bearish, 0.0, 1.0), index=indicators.index, dtype=float)

    if candidate["kind"] == "close_hold_3":
        weights = []
        state = "normal"
        bear_count = 0
        close_count = 0
        for is_bear, is_close in zip(bearish.tolist(), close_confirm.tolist()):
            bear_count = bear_count + 1 if is_bear else 0
            close_count = close_count + 1 if is_close else 0
            if state == "normal":
                if bear_count >= 2:
                    state = "flat"
                elif bear_count == 1:
                    state = "soft_off"
            elif state == "soft_off":
                if bear_count >= 2:
                    state = "flat"
                elif bear_count == 0:
                    state = "normal"
            elif state == "flat":
                if close_count >= 3:
                    state = "normal"
            weights.append(1.0 if state == "normal" else 0.5 if state == "soft_off" else 0.0)
        return pd.Series(weights, index=indicators.index, dtype=float)

    trigger = candidate_trigger(indicators, candidate)
    weights = []
    state = "normal"
    bear_count = 0
    close_count = 0
    for is_bear, is_close, trig in zip(bearish.tolist(), close_confirm.tolist(), trigger.tolist()):
        bear_count = bear_count + 1 if is_bear else 0
        close_count = close_count + 1 if is_close else 0
        if state == "normal":
            if bear_count >= 2:
                state = "flat"
            elif bear_count == 1:
                state = "soft_off"
        elif state == "soft_off":
            if bear_count >= 2:
                state = "flat"
            elif bear_count == 0:
                state = "normal"
        elif state == "flat":
            if close_count >= 3:
                state = "normal"
            elif trig:
                state = "override_hold"
                bear_count = 0
                close_count = 0
        elif state == "override_hold":
            if close_count >= 3:
                state = "normal"
        weights.append(1.0 if state in {"normal", "override_hold"} else 0.5 if state == "soft_off" else 0.0)
    return pd.Series(weights, index=indicators.index, dtype=float)


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


def pnl_attribution(candidate_core: pd.Series, bh_core: pd.Series, target: pd.Series) -> Dict:
    bh_pnl = bh_core.diff().fillna(0.0)
    cand_pnl = candidate_core.diff().fillna(0.0)
    diff = cand_pnl - bh_pnl
    state = target.reindex(candidate_core.index).ffill().fillna(1.0).round(4)
    return {
        "flat_state_upside_drag": float((-diff[(state == 0.0) & (bh_pnl > 0) & (diff < 0)]).sum()),
    }


def summarize_candidate(bundle: Dict, key: str) -> Dict:
    systems = bundle["systems"]
    addon_key = "Core+AddOnOverlay"
    core_key = "CoreOnly"
    major_draw = next(x for x in TIME_SLICES if x["name"] == "major_drawdown")
    bull = next(x for x in TIME_SLICES if x["name"] == "bull_expansion")
    recovery = next(x for x in TIME_SLICES if x["name"] == "recovery_phase")
    strict_flags: List[float] = []
    dreturns: List[float] = []
    dcalmars: List[float] = []
    dsharpes: List[float] = []
    flat_drags: List[float] = []

    for year in WF_TEST_YEARS:
        start = f"{year}-01-01"
        end = f"{year+1}-01-01"
        addon_eq = slice_series(systems[addon_key]["equity"], start, end)
        cand_eq = slice_series(systems[key]["combo"]["equity"], start, end)
        addon_metrics = compute_slice_metrics(addon_eq)
        cand_metrics = compute_slice_metrics(cand_eq)
        strict = bool(
            (cand_metrics["Calmar"] > addon_metrics["Calmar"])
            and (cand_metrics["Sharpe"] > addon_metrics["Sharpe"])
            and (abs(cand_metrics["MaxDD_pct"]) < abs(addon_metrics["MaxDD_pct"]))
        )
        attribution = pnl_attribution(
            slice_series(systems[key]["core"]["equity"]["equity"].astype(float), start, end),
            slice_series(systems[core_key]["equity"], start, end),
            slice_series(systems[key]["target"], start, end),
        )
        strict_flags.append(float(strict))
        dreturns.append(float(cand_metrics["TotalReturn_pct"] - addon_metrics["TotalReturn_pct"]))
        dsharpes.append(float(cand_metrics["Sharpe"] - addon_metrics["Sharpe"]))
        dcalmars.append(float(cand_metrics["Calmar"] - addon_metrics["Calmar"]))
        flat_drags.append(attribution["flat_state_upside_drag"])

    bull_metrics = compute_slice_metrics(slice_series(systems[key]["combo"]["equity"], bull["start"], bull["end"]))
    bull_base = compute_slice_metrics(slice_series(systems[addon_key]["equity"], bull["start"], bull["end"]))
    recovery_metrics = compute_slice_metrics(slice_series(systems[key]["combo"]["equity"], recovery["start"], recovery["end"]))
    recovery_base = compute_slice_metrics(slice_series(systems[addon_key]["equity"], recovery["start"], recovery["end"]))
    draw_metrics = compute_slice_metrics(slice_series(systems[key]["combo"]["equity"], major_draw["start"], major_draw["end"]))
    draw_base = compute_slice_metrics(slice_series(systems[addon_key]["equity"], major_draw["start"], major_draw["end"]))

    return {
        "metrics": systems[key]["metrics"],
        "avg_core_exposure_pct": systems[key]["avg_core_exposure_pct"],
        "riskoff_active_ratio_pct": systems[key]["riskoff_active_ratio_pct"],
        "state_changes": systems[key]["state_changes"],
        "strict_oos_win_ratio": float(np.mean(strict_flags)) if strict_flags else 0.0,
        "avg_delta_return_pct": float(np.mean(dreturns)) if dreturns else 0.0,
        "avg_delta_sharpe": float(np.mean(dsharpes)) if dsharpes else 0.0,
        "avg_delta_calmar": float(np.mean(dcalmars)) if dcalmars else 0.0,
        "bull_delta_return_pct": float(bull_metrics["TotalReturn_pct"] - bull_base["TotalReturn_pct"]),
        "recovery_delta_return_pct": float(recovery_metrics["TotalReturn_pct"] - recovery_base["TotalReturn_pct"]),
        "major_drawdown_dmaxdd_pct": float(abs(draw_base["MaxDD_pct"]) - abs(draw_metrics["MaxDD_pct"])),
        "avg_flat_state_upside_drag": float(np.mean(flat_drags)) if flat_drags else 0.0,
    }


def trigger_counts(indicators: pd.DataFrame) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for cand in CANDIDATES:
        out[cand["name"]] = int(candidate_trigger(indicators, cand).fillna(False).sum())
    return out


def build_bundle(df_5m: pd.DataFrame, df_4h: pd.DataFrame, overlay: Dict, params, execution_mode: str) -> Dict:
    indicators = enrich_indicators(build_indicator_cache(df_4h, params, [220], overlay["index"])[220])
    systems = {
        "CoreOnly": {
            "equity": overlay["bh_equity"],
            "metrics": compute_metrics(overlay["bh_equity"], pd.Series(1.0, index=overlay["index"], dtype=float)),
            "avg_core_exposure_pct": 100.0,
            "riskoff_active_ratio_pct": 0.0,
            "state_changes": 0,
            "target": pd.Series(1.0, index=overlay["index"], dtype=float),
        },
        "Core+AddOnOverlay": {
            "equity": overlay["addon_equity"],
            "metrics": overlay["artifact"]["schemes"]["AddOnOverlay"]["metrics"],
            "avg_core_exposure_pct": 100.0,
            "riskoff_active_ratio_pct": 0.0,
            "state_changes": 0,
            "target": pd.Series(1.0, index=overlay["index"], dtype=float),
        },
    }
    all_candidates = [ARCHIVED_BASELINE, BEST_ARCHIVED_REPAIR] + CANDIDATES
    causality = {}
    for cand in all_candidates:
        target = build_target(indicators, cand)
        sim = simulate_candidate(df_5m, df_4h, overlay, params, execution_mode, target)
        key = f"Core+AddOnOverlay+{cand['name']}"
        systems[key] = {**sim, "candidate": cand}
        causality[cand["name"]] = sim["core"]["causality"]
    return {"systems": systems, "causality": causality, "indicators": indicators}


def write_report(report: Dict) -> None:
    lines = [
        "# Risk-Off Low-Value Re-Entry Report",
        "",
        "## Scope",
        "",
        "- Base mainline remains `RO_EMA220_REENTRY_CLOSE_HOLD_3`.",
        "- Each candidate only adds a low-value override-hold re-entry after flat.",
        "- Sell-side Risk-Off logic remains unchanged.",
        "",
        "## Candidate Table",
        "",
        "| Candidate | Trigger Count | Strict OOS | Avg dReturn | Avg dCalmar | Bull dReturn | Recovery dReturn | Major Drawdown dMaxDD | Return% | Calmar | MaxDD% | Avg Core Exposure% |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    summary = report["candidate_summary"]
    triggers = report["trigger_counts"]
    order = [BEST_ARCHIVED_REPAIR["name"]] + [cand["name"] for cand in CANDIDATES]
    for name in order:
        key = f"Core+AddOnOverlay+{name}"
        row = summary[key]
        m = report["full_sample"][key]["metrics"]
        lines.append(
            f"| {name} | {triggers.get(name, 0)} | {row['strict_oos_win_ratio']:.2f} | "
            f"{row['avg_delta_return_pct']:+.2f}pp | {row['avg_delta_calmar']:+.3f} | "
            f"{row['bull_delta_return_pct']:+.2f}pp | {row['recovery_delta_return_pct']:+.2f}pp | "
            f"{row['major_drawdown_dmaxdd_pct']:+.2f}pp | {m['TotalReturn_pct']:.2f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | "
            f"{report['full_sample'][key]['avg_core_exposure_pct']:.1f} |"
        )
    lines.extend(
        [
            "",
            "## Equity Curves",
            "",
            f"- HTML: `{CURVES_HTML.name}`",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_equity_html(bundle: Dict) -> None:
    systems = bundle["systems"]
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=systems["CoreOnly"]["equity"].index,
            y=systems["CoreOnly"]["equity"],
            mode="lines",
            name="Buy & Hold",
            line=dict(width=2.2, color="#64748b"),
        )
    )
    base_key = f"Core+AddOnOverlay+{BEST_ARCHIVED_REPAIR['name']}"
    fig.add_trace(
        go.Scatter(
            x=systems[base_key]["combo"]["equity"].index,
            y=systems[base_key]["combo"]["equity"],
            mode="lines",
            name=BEST_ARCHIVED_REPAIR["name"],
            line=dict(width=2.4, color="#111827"),
        )
    )

    palette = ["#2563eb", "#059669", "#dc2626", "#7c3aed", "#ea580c", "#0891b2", "#65a30d", "#db2777", "#0f766e", "#b45309"]
    for color, cand in zip(palette, CANDIDATES):
        key = f"Core+AddOnOverlay+{cand['name']}"
        fig.add_trace(
            go.Scatter(
                x=systems[key]["combo"]["equity"].index,
                y=systems[key]["combo"]["equity"],
                mode="lines",
                name=cand["name"],
                line=dict(width=1.35, color=color),
            )
        )

    latest_x = systems[base_key]["combo"]["equity"].index.max()
    fig.add_vline(x=latest_x, line_width=1, line_dash="dot", line_color="#111827")
    fig.update_layout(
        template="plotly_white",
        height=780,
        hovermode="x unified",
        title="Risk-Off Low-Value Re-Entry Candidates vs Archived Best Mainline",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        margin=dict(l=50, r=30, t=80, b=40),
        xaxis_title="Time",
        yaxis_title="Equity",
    )
    CURVES_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


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
    bundle = build_bundle(df_5m, df_4h, overlay, params, "next_bar_open")
    summary = {}
    for cand in [ARCHIVED_BASELINE, BEST_ARCHIVED_REPAIR] + CANDIDATES:
        key = f"Core+AddOnOverlay+{cand['name']}"
        summary[key] = summarize_candidate(bundle, key)
    full_sample = {}
    for key, item in bundle["systems"].items():
        if key == "CoreOnly":
            full_sample[key] = {
                "metrics": item["metrics"],
                "avg_core_exposure_pct": item["avg_core_exposure_pct"],
                "riskoff_active_ratio_pct": item["riskoff_active_ratio_pct"],
            }
        elif key.startswith("Core+AddOnOverlay"):
            full_sample[key] = {
                "metrics": item["metrics"],
                "avg_core_exposure_pct": item["avg_core_exposure_pct"],
                "riskoff_active_ratio_pct": item["riskoff_active_ratio_pct"],
            }
    report = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "default_tuple": DEFAULT_TUPLE,
        "stress_tuple": STRESS_TUPLE,
        "research_optimal": {"label": "lb20_stop3.2_trail5.0_beoff", "params": asdict(params)},
        "candidate_summary": summary,
        "full_sample": full_sample,
        "trigger_counts": trigger_counts(bundle["indicators"]),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(report)
    write_equity_html(bundle)
    print({"report": REPORT_MD.name, "html": CURVES_HTML.name})


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
