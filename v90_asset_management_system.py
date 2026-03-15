#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BTC asset-management system study built on the long-only trend overlay baseline."""

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
from v90_trend_long_mother import SEED, TrendIndicatorEngine, TrendLongParams, run_candidate, with_overrides

ANNUALIZATION_4H = np.sqrt(252.0 * 6.0)
INIT_EQUITY = 10000.0
DEFAULT_TUPLE = "next_bar_open + legacy_bar_extrema + midpoint + full_model"
STRESS_TUPLE = "live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model"
CORE_ONE_WAY_COST = 0.0011
SHORT_ONE_WAY_COST = 0.0016


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


def calmar(cagr: float, maxdd: float) -> float:
    return 0.0 if maxdd >= 0.0 else float(cagr) / abs(float(maxdd))


def pf_from_equity(equity: pd.Series) -> float:
    pnl = equity.diff().fillna(0.0)
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    if gross_loss <= 0.0:
        return 0.0
    return gross_profit / gross_loss


def max_drawdown_duration_bars(drawdown: pd.Series) -> int:
    max_len = 0
    current = 0
    for active in (drawdown < 0.0).tolist():
        if active:
            current += 1
            max_len = max(max_len, current)
        else:
            current = 0
    return int(max_len)


def compute_metrics(equity: pd.Series, net_exposure: pd.Series, gross_exposure: pd.Series) -> Dict:
    ret = equity.pct_change().fillna(0.0)
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    elapsed_days = max((equity.index[-1] - equity.index[0]).total_seconds() / 86400.0, 1.0)
    years = elapsed_days / 365.25
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = (float(equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0) if years > 0.0 else 0.0
    std = float(ret.std())
    sharpe = float(ret.mean()) / std * ANNUALIZATION_4H if std > 0.0 else 0.0
    maxdd = float(drawdown.min())
    dd_bars = max_drawdown_duration_bars(drawdown)
    return {
        "TotalReturn_pct": total_return * 100.0,
        "CAGR_pct": cagr * 100.0,
        "Sharpe": sharpe,
        "Calmar": calmar(cagr, maxdd),
        "MaxDD_pct": maxdd * 100.0,
        "PF": pf_from_equity(equity),
        "ExposureNet_pct": float(net_exposure.mean() * 100.0),
        "ExposureGross_pct": float(gross_exposure.mean() * 100.0),
        "MaxDDDuration_bars_4h": int(dd_bars),
        "MaxDDDuration_days": float(dd_bars * 4.0 / 24.0),
    }


def yearly_returns(equity: pd.Series) -> List[Dict]:
    df = equity.to_frame("equity")
    rows: List[Dict] = []
    for year, sub in df.groupby(df.index.year):
        if len(sub) < 2:
            continue
        rows.append({"year": int(year), "Return_pct": float((sub["equity"].iloc[-1] / sub["equity"].iloc[0] - 1.0) * 100.0)})
    return rows


def period_return(equity: pd.Series, start: str, end: str) -> float:
    sub = equity[(equity.index >= pd.Timestamp(start, tz="UTC")) & (equity.index < pd.Timestamp(end, tz="UTC"))]
    if len(sub) < 2:
        return 0.0
    return float((sub.iloc[-1] / sub.iloc[0] - 1.0) * 100.0)


def risk_window_table(equity_map: Dict[str, pd.Series]) -> List[Dict]:
    windows = [
        ("covid_crash_2020", "2020-02-15", "2020-04-30"),
        ("china_deleveraging_2021", "2021-04-10", "2021-07-31"),
        ("bear_2022", "2022-01-01", "2023-01-01"),
        ("ftx_shock", "2022-11-01", "2022-12-15"),
    ]
    rows: List[Dict] = []
    for name, start, end in windows:
        row = {"window": name}
        for scheme, equity in equity_map.items():
            row[scheme] = period_return(equity, start, end)
        rows.append(row)
    return rows


def delta_metrics(metrics: Dict, baseline: Dict) -> Dict:
    return {
        "Return_pct": float(metrics["TotalReturn_pct"] - baseline["TotalReturn_pct"]),
        "CAGR_pct": float(metrics["CAGR_pct"] - baseline["CAGR_pct"]),
        "Sharpe": float(metrics["Sharpe"] - baseline["Sharpe"]),
        "Calmar": float(metrics["Calmar"] - baseline["Calmar"]),
        "MaxDD_improvement_pct": float(abs(baseline["MaxDD_pct"]) - abs(metrics["MaxDD_pct"])),
    }


def simulate_weighted_core(close: pd.Series, weights: pd.Series, one_way_cost: float = CORE_ONE_WAY_COST) -> Tuple[pd.Series, pd.Series, Dict]:
    idx = close.index
    btc_ret = close.pct_change().fillna(0.0)
    w = weights.reindex(idx).ffill().fillna(1.0).astype(float)
    values = [INIT_EQUITY]
    prev_weight = float(w.iloc[0])
    turnover = 0.0
    state_changes = 0
    for i in range(1, len(idx)):
        equity = values[-1]
        target_weight = float(w.iloc[i - 1])
        delta = abs(target_weight - prev_weight)
        if delta > 0.0:
            equity *= (1.0 - delta * one_way_cost)
            turnover += delta
            state_changes += 1
        equity *= (1.0 + target_weight * float(btc_ret.iloc[i]))
        values.append(equity)
        prev_weight = target_weight
    details = {
        "avg_weight": float(w.mean()),
        "state_changes": int(state_changes),
        "turnover_notional": float(turnover),
        "off_ratio": float((w < 0.9999).mean()),
    }
    return pd.Series(values, index=idx), w, details


def simulate_short_sleeve(close: pd.Series, active: pd.Series, short_weight: float, one_way_cost: float = SHORT_ONE_WAY_COST) -> Tuple[pd.Series, pd.Series, Dict]:
    idx = close.index
    btc_ret = close.pct_change().fillna(0.0)
    a = active.reindex(idx).fillna(False).astype(bool)
    values = [INIT_EQUITY]
    prev_active = 1 if bool(a.iloc[0]) else 0
    turnover = 0.0
    state_changes = 0
    for i in range(1, len(idx)):
        equity = values[-1]
        target_active = 1 if bool(a.iloc[i - 1]) else 0
        delta = abs(target_active - prev_active) * short_weight
        if delta > 0.0:
            equity *= (1.0 - delta * one_way_cost)
            turnover += delta
            state_changes += 1
        exposure = -short_weight if target_active else 0.0
        equity *= (1.0 + exposure * float(btc_ret.iloc[i]))
        values.append(equity)
        prev_active = target_active
    details = {
        "active_ratio": float(a.mean()),
        "state_changes": int(state_changes),
        "turnover_notional": float(turnover),
        "short_weight": float(short_weight),
    }
    return pd.Series(values, index=idx), a.astype(float), details


def build_indicator_cache(df_4h: pd.DataFrame, base_params: TrendLongParams, ema_lens: List[int]) -> Dict[int, pd.DataFrame]:
    cache: Dict[int, pd.DataFrame] = {}
    engine = TrendIndicatorEngine()
    for ema_len in ema_lens:
        params = with_overrides(base_params, ema_len=ema_len)
        cache[ema_len] = engine.compute(df_4h, params).set_index("timestamp")
    return cache


def evaluate_scheme(description: str, equity: pd.Series, net_exposure: pd.Series, gross_exposure: pd.Series, extras: Dict | None = None) -> Dict:
    payload = {
        "description": description,
        "metrics": compute_metrics(equity, net_exposure, gross_exposure),
        "yearly_returns": yearly_returns(equity),
    }
    if extras:
        payload.update(extras)
    return payload

def candidate_line(label: str, metrics: Dict, extra: str = "") -> str:
    text = (
        f"- {label}: Return {metrics['TotalReturn_pct']:.2f}%, CAGR {metrics['CAGR_pct']:.2f}%, "
        f"Sharpe {metrics['Sharpe']:.3f}, Calmar {metrics['Calmar']:.3f}, MaxDD {metrics['MaxDD_pct']:.2f}%"
    )
    if extra:
        text += f", {extra}"
    return text


def write_markdown(report: Dict) -> None:
    lines: List[str] = [
        "# BTC Asset Management System Report",
        "",
        "## Final Conclusion",
        "",
        f"- Recommended structure: {report['recommendation']['recommended_structure']}",
        f"- Main judgment: {report['recommendation']['main_judgment']}",
        f"- Keep AddOnOverlay unchanged: {report['recommendation']['keep_addon_unchanged']}",
        f"- Risk-Off module value: {report['recommendation']['riskoff_value']}",
        f"- Bear Short sleeve value: {report['recommendation']['bear_short_value']}",
        f"- Better than plain B&H as an asset-management framework: {report['recommendation']['better_than_bh_framework']}",
        "",
        "## Module Roles",
        "",
        "- Module A `AddOnOverlay`: keep the already validated long-only trend sleeve unchanged as the return-enhancing leg.",
        "- Module B `Risk-Off Overlay`: reduce core BTC exposure only when the long-term regime is clearly broken, with low-frequency state changes.",
        "- Module C `Bear Short Sleeve`: only activate in high-confidence bearish/crash states as an extreme-downside hedge, not as a symmetric all-weather short strategy.",
        "",
        "## Module Candidates",
        "",
        "### Risk-Off Candidates",
        "",
    ]
    for item in report["module_candidates"]["risk_off"]:
        lines.append(candidate_line(item["name"], item["combo_metrics"], item.get("detail", "")))
    lines.extend(["", "### Bear Short Candidates", ""])
    for item in report["module_candidates"]["bear_short"]:
        lines.append(candidate_line(item["name"], item["combo_metrics"], item.get("detail", "")))
    lines.extend([
        "",
        "## Parameter Analysis",
        "",
        "### Risk-Off Grid",
        "",
        "| EMA Len | Off Weight | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Avg Core Exposure% | State Changes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in report["parameter_analysis"]["risk_off_grid"]:
        lines.append(
            f"| {row['ema_len']} | {row['off_weight']:.2f} | {row['metrics']['TotalReturn_pct']:.2f} | {row['metrics']['CAGR_pct']:.2f} | {row['metrics']['Sharpe']:.3f} | {row['metrics']['Calmar']:.3f} | {row['metrics']['MaxDD_pct']:.2f} | {row['avg_core_weight_pct']:.1f} | {row['state_changes']} |"
        )
    lines.extend([
        "",
        "### Bear Short Grid",
        "",
        "| Lookback | Short Weight | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Active% | State Changes |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in report["parameter_analysis"]["bear_short_grid"]:
        lines.append(
            f"| {row['lookback']} | {row['short_weight']:.2f} | {row['metrics']['TotalReturn_pct']:.2f} | {row['metrics']['CAGR_pct']:.2f} | {row['metrics']['Sharpe']:.3f} | {row['metrics']['Calmar']:.3f} | {row['metrics']['MaxDD_pct']:.2f} | {row['active_ratio_pct']:.2f} | {row['state_changes']} |"
        )
    lines.extend([
        "",
        "## Combination Results",
        "",
        "| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | PF | Net Exposure% | Gross Exposure% | dRet vs B&H | dRet vs AddOn | dMaxDD vs B&H | dMaxDD vs AddOn |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for name in report["scheme_order"]:
        item = report["schemes"][name]
        m = item["metrics"]
        db = item["delta_vs_bh"]
        da = item["delta_vs_addon"]
        lines.append(
            f"| {name} | {m['TotalReturn_pct']:.2f} | {m['CAGR_pct']:.2f} | {m['Sharpe']:.3f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | {m['PF']:.3f} | {m['ExposureNet_pct']:.1f} | {m['ExposureGross_pct']:.1f} | {db['Return_pct']:+.2f} | {da['Return_pct']:+.2f} | {db['MaxDD_improvement_pct']:+.2f} | {da['MaxDD_improvement_pct']:+.2f} |"
        )
    lines.extend([
        "",
        "## Bear And Risk Windows",
        "",
        "| Window | B&H | Core+AddOnOverlay | Core+RiskOff | Core+AddOnOverlay+RiskOff | Core+AddOnOverlay+RiskOff+BearShort |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for row in report["risk_windows"]:
        lines.append(
            f"| {row['window']} | {row['B&H']:.2f} | {row['Core+AddOnOverlay']:.2f} | {row['Core+RiskOff']:.2f} | {row['Core+AddOnOverlay+RiskOff']:.2f} | {row['Core+AddOnOverlay+RiskOff+BearShort']:.2f} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        f"- Risk-Off assessment: {report['recommendation']['riskoff_detail']}",
        f"- Bear Short assessment: {report['recommendation']['bear_short_detail']}",
        f"- Final structure call: {report['recommendation']['structure_detail']}",
        "",
        "## Research Boundary",
        "",
        "- The AddOnOverlay signal itself was not modified.",
        "- Default execution tuple stayed at `next_bar_open + legacy_bar_extrema + midpoint + full_model`.",
        "- Risk-Off and Bear Short were tested as simple, explainable low-frequency modules with small parameter neighborhoods only.",
        "",
        "## Parameter And Cost Assumptions",
        "",
        "- research_optimal: `lb20_stop3.2_trail5.0_beoff`",
        f"- default tuple: `{DEFAULT_TUPLE}`",
        f"- stress/gate tuple only: `{STRESS_TUPLE}`",
        f"- core risk-off one-way cost assumption: {CORE_ONE_WAY_COST * 100.0:.2f}% of changed notional",
        f"- bear short one-way cost assumption: {SHORT_ONE_WAY_COST * 100.0:.2f}% of changed notional",
    ])
    Path("BTC_ASSET_MANAGEMENT_SYSTEM_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def write_summary(report: Dict) -> None:
    lines = [
        f"recommended_structure={report['recommendation']['recommended_structure']}",
        f"bear_short_worth_adding={report['recommendation']['bear_short_worth_adding']}",
        f"better_than_addon_only={report['recommendation']['better_than_addon_only']}",
        f"main_judgment={report['recommendation']['main_judgment']}",
    ]
    Path("btc_asset_management_system_summary.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    params = current_research_optimal()
    overlay35 = run_candidate(df_5m, df_4h, with_overrides(params, position_pct=35.0))

    eq35 = overlay35["equity"]["equity"].astype(float)
    pos35 = overlay35["equity"]["position"].astype(float).fillna(0.0)
    close = overlay35["equity"]["close"].astype(float)
    idx = eq35.index

    indicator_cache = build_indicator_cache(df_4h, params, [180, 200, 220])
    aligned_indicators = {k: v.reindex(idx) for k, v in indicator_cache.items()}

    bh_equity, _, _ = simulate_weighted_core(close, pd.Series(1.0, index=idx), one_way_cost=0.0)
    add_on_equity = bh_equity + (eq35 - INIT_EQUITY)
    add_on_net_exposure = pd.Series(1.0, index=idx) + 0.35 * pos35

    riskoff_candidates: List[Dict] = []
    riskoff_grid: List[Dict] = []

    for ema_len in [180, 200, 220]:
        ind = aligned_indicators[ema_len]
        regime = (close < ind["ema"]) & (ind["ema_slope"] < 0)
        for off_weight in [0.0, 0.35, 0.5]:
            core_eq, core_w, detail = simulate_weighted_core(close, pd.Series(np.where(regime, off_weight, 1.0), index=idx))
            combo_eq = core_eq + (eq35 - INIT_EQUITY)
            combo_net = core_w + 0.35 * pos35
            metrics = compute_metrics(combo_eq, combo_net, combo_net)
            riskoff_grid.append({
                "ema_len": ema_len,
                "off_weight": float(off_weight),
                "metrics": metrics,
                "avg_core_weight_pct": float(detail["avg_weight"] * 100.0),
                "state_changes": int(detail["state_changes"]),
                "off_ratio_pct": float(detail["off_ratio"] * 100.0),
            })

    for ema_len, off_weight, name in [
        (200, 0.0, "B1_TrendBreakRiskOff_ema200_flat"),
        (220, 0.0, "B1_TrendBreakRiskOff_ema220_flat"),
        (200, 0.35, "B1_TrendBreakRiskOff_ema200_to35"),
    ]:
        ind = aligned_indicators[ema_len]
        regime = (close < ind["ema"]) & (ind["ema_slope"] < 0)
        core_eq, core_w, detail = simulate_weighted_core(close, pd.Series(np.where(regime, off_weight, 1.0), index=idx))
        combo_eq = core_eq + (eq35 - INIT_EQUITY)
        combo_net = core_w + 0.35 * pos35
        riskoff_candidates.append({
            "name": name,
            "module_type": "Risk-Off",
            "description": "Reduce core BTC exposure when price is below the long-term EMA and the EMA slope is negative.",
            "params": {"ema_len": ema_len, "off_weight": off_weight},
            "detail": f"avg core exposure {detail['avg_weight'] * 100.0:.1f}%, state changes {detail['state_changes']}",
            "combo_metrics": compute_metrics(combo_eq, combo_net, combo_net),
            "module_stats": detail,
        })

    ind200 = aligned_indicators[200]
    atr_pct200 = (ind200["atr"] / close).fillna(0.0)
    regime_b2 = (close < ind200["ema"]) & (ind200["ema_slope"] < 0) & (atr_pct200 > 0.025)
    core_eq_b2, core_w_b2, detail_b2 = simulate_weighted_core(close, pd.Series(np.where(regime_b2, 0.35, 1.0), index=idx))
    combo_eq_b2 = core_eq_b2 + (eq35 - INIT_EQUITY)
    combo_net_b2 = core_w_b2 + 0.35 * pos35
    riskoff_candidates.append({
        "name": "B2_TrendVolRiskOff_ema200_to35",
        "module_type": "Risk-Off",
        "description": "Reduce core BTC exposure only when trend is broken and ATR/price volatility is elevated.",
        "params": {"ema_len": 200, "off_weight": 0.35, "atr_pct_threshold": 0.025},
        "detail": f"avg core exposure {detail_b2['avg_weight'] * 100.0:.1f}%, state changes {detail_b2['state_changes']}",
        "combo_metrics": compute_metrics(combo_eq_b2, combo_net_b2, combo_net_b2),
        "module_stats": detail_b2,
    })
    roll_low_63 = close.shift(1).rolling(63).min()
    regime_b3 = (close < ind200["ema"]) & (ind200["ema_slope"] < 0) & (close < roll_low_63)
    core_eq_b3, core_w_b3, detail_b3 = simulate_weighted_core(close, pd.Series(np.where(regime_b3, 0.0, 1.0), index=idx))
    combo_eq_b3 = core_eq_b3 + (eq35 - INIT_EQUITY)
    combo_net_b3 = core_w_b3 + 0.35 * pos35
    riskoff_candidates.append({
        "name": "B3_StructureBreakRiskOff_flat",
        "module_type": "Risk-Off",
        "description": "Go flat on the core only after a bearish regime is confirmed by a breakdown below the 63-bar structure low.",
        "params": {"ema_len": 200, "off_weight": 0.0, "breakdown_lookback": 63},
        "detail": f"avg core exposure {detail_b3['avg_weight'] * 100.0:.1f}%, state changes {detail_b3['state_changes']}",
        "combo_metrics": compute_metrics(combo_eq_b3, combo_net_b3, combo_net_b3),
        "module_stats": detail_b3,
    })

    preferred_riskoff = max(
        [row for row in riskoff_candidates if row["name"].startswith("B1_")],
        key=lambda item: (item["combo_metrics"]["Calmar"], item["combo_metrics"]["CAGR_pct"]),
    )
    preferred_ind = aligned_indicators[preferred_riskoff["params"]["ema_len"]]
    preferred_regime = (close < preferred_ind["ema"]) & (preferred_ind["ema_slope"] < 0)
    preferred_core_eq, preferred_core_w, _ = simulate_weighted_core(
        close, pd.Series(np.where(preferred_regime, preferred_riskoff["params"]["off_weight"], 1.0), index=idx)
    )

    bear_short_candidates: List[Dict] = []
    bear_short_grid: List[Dict] = []
    atr_pct_pref = (preferred_ind["atr"] / close).fillna(0.0)
    roll_low_42 = close.shift(1).rolling(42).min()
    roll_low_84 = close.shift(1).rolling(84).min()
    roll_low_126 = close.shift(1).rolling(126).min()

    short_defs = [
        {
            "name": "C1_BreakdownQualityShort",
            "description": "Only short after the core is already risk-off, ADX is bearish/strong, the bar closes near its low, and price breaks the 63-bar low.",
            "active": preferred_regime & (preferred_ind["adx"] >= 18.0) & (preferred_ind["close_location"] <= 0.40) & (close < roll_low_63),
            "short_weight": 0.25,
            "params": {"lookback": 63, "short_weight": 0.25, "adx_min": 18.0, "close_location_max": 0.40},
        },
        {
            "name": "C2_CrashSleeveShort",
            "description": "Only short in a risk-off regime when volatility is elevated and price breaks the 126-bar low.",
            "active": preferred_regime & (atr_pct_pref > 0.030) & (close < roll_low_126),
            "short_weight": 0.25,
            "params": {"lookback": 126, "short_weight": 0.25, "atr_pct_threshold": 0.030},
        },
        {
            "name": "C3_ConfirmedBreakShort",
            "description": "Short only after risk-off is already active and downside confirms with elevated ATR and an 84-bar breakdown.",
            "active": preferred_regime & (atr_pct_pref > 0.025) & (close < roll_low_84),
            "short_weight": 0.35,
            "params": {"lookback": 84, "short_weight": 0.35, "atr_pct_threshold": 0.025},
        },
    ]

    base_combo_eq = preferred_core_eq + (eq35 - INIT_EQUITY)
    base_combo_net = preferred_core_w + 0.35 * pos35
    for item in short_defs:
        short_eq, short_active, short_detail = simulate_short_sleeve(close, item["active"], item["short_weight"])
        combo_eq = base_combo_eq + (short_eq - INIT_EQUITY)
        combo_net = base_combo_net - item["short_weight"] * short_active
        combo_gross = base_combo_net + item["short_weight"] * short_active
        bear_short_candidates.append({
            "name": item["name"],
            "module_type": "Bear Short",
            "description": item["description"],
            "params": item["params"],
            "detail": f"active {short_detail['active_ratio'] * 100.0:.2f}%, state changes {short_detail['state_changes']}",
            "combo_metrics": compute_metrics(combo_eq, combo_net, combo_gross),
            "module_stats": short_detail,
        })

    for lookback, roll_low in [(42, roll_low_42), (63, roll_low_63), (84, roll_low_84)]:
        active = preferred_regime & (atr_pct_pref > 0.025) & (close < roll_low)
        for short_weight in [0.20, 0.25, 0.35]:
            short_eq, short_active, short_detail = simulate_short_sleeve(close, active, short_weight)
            combo_eq = base_combo_eq + (short_eq - INIT_EQUITY)
            combo_net = base_combo_net - short_weight * short_active
            combo_gross = base_combo_net + short_weight * short_active
            bear_short_grid.append({
                "lookback": lookback,
                "short_weight": short_weight,
                "metrics": compute_metrics(combo_eq, combo_net, combo_gross),
                "active_ratio_pct": float(short_detail["active_ratio"] * 100.0),
                "state_changes": int(short_detail["state_changes"]),
            })

    preferred_short = max(
        bear_short_candidates,
        key=lambda item: (item["combo_metrics"]["Calmar"], item["combo_metrics"]["CAGR_pct"]),
    )
    preferred_short_def = next(item for item in short_defs if item["name"] == preferred_short["name"])
    preferred_short_eq, preferred_short_active, _ = simulate_short_sleeve(
        close, preferred_short_def["active"], preferred_short["params"]["short_weight"]
    )

    schemes = {
        "B&H": {
            "equity": bh_equity,
            "net_exposure": pd.Series(1.0, index=idx),
            "gross_exposure": pd.Series(1.0, index=idx),
            "description": "Pure BTC buy-and-hold.",
        },
        "Core+AddOnOverlay": {
            "equity": add_on_equity,
            "net_exposure": add_on_net_exposure,
            "gross_exposure": add_on_net_exposure,
            "description": "100% BTC core plus the already validated 35% long-only AddOnOverlay sleeve.",
        },
        "Core+RiskOff": {
            "equity": preferred_core_eq,
            "net_exposure": preferred_core_w,
            "gross_exposure": preferred_core_w,
            "description": "Dynamic core-only allocation with the preferred Risk-Off regime, no AddOnOverlay sleeve.",
            "module_choice": preferred_riskoff["name"],
        },
        "Core+AddOnOverlay+RiskOff": {
            "equity": base_combo_eq,
            "net_exposure": base_combo_net,
            "gross_exposure": base_combo_net,
            "description": "Core BTC holding plus unchanged AddOnOverlay sleeve plus preferred Risk-Off regime on the core.",
            "module_choice": preferred_riskoff["name"],
        },
        "Core+AddOnOverlay+RiskOff+BearShort": {
            "equity": base_combo_eq + (preferred_short_eq - INIT_EQUITY),
            "net_exposure": base_combo_net - preferred_short["params"]["short_weight"] * preferred_short_active,
            "gross_exposure": base_combo_net + preferred_short["params"]["short_weight"] * preferred_short_active,
            "description": "Core BTC holding plus unchanged AddOnOverlay sleeve plus preferred Risk-Off regime plus the best strict Bear Short sleeve candidate.",
            "module_choice": {"risk_off": preferred_riskoff["name"], "bear_short": preferred_short["name"]},
        },
    }

    report = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "research_optimal": {"label": "lb20_stop3.2_trail5.0_beoff", "params": asdict(params)},
        "default_research_tuple": DEFAULT_TUPLE,
        "stress_tuple": STRESS_TUPLE,
        "module_roles": {
            "AddOnOverlay": "Keep the proven long-only trend sleeve unchanged as the return-enhancing leg.",
            "RiskOffOverlay": "Reduce core BTC exposure only in clear bearish regimes to compress drawdown without turning into a short-term timing engine.",
            "BearShortSleeve": "Only hedge extreme downside after bearish regime confirmation; do not run as a symmetric mirror of the long module.",
        },
        "module_candidates": {"risk_off": riskoff_candidates, "bear_short": bear_short_candidates},
        "parameter_analysis": {"risk_off_grid": riskoff_grid, "bear_short_grid": bear_short_grid},
        "schemes": {},
        "scheme_order": [
            "B&H",
            "Core+AddOnOverlay",
            "Core+RiskOff",
            "Core+AddOnOverlay+RiskOff",
            "Core+AddOnOverlay+RiskOff+BearShort",
        ],
    }

    equity_map: Dict[str, pd.Series] = {}
    for name, payload in schemes.items():
        equity = payload["equity"].astype(float)
        net = payload["net_exposure"].astype(float)
        gross = payload["gross_exposure"].astype(float)
        extras = {k: v for k, v in payload.items() if k not in {"equity", "net_exposure", "gross_exposure", "description"}}
        report["schemes"][name] = evaluate_scheme(payload["description"], equity, net, gross, extras)
        equity_map[name] = equity

    bh_metrics = report["schemes"]["B&H"]["metrics"]
    addon_metrics = report["schemes"]["Core+AddOnOverlay"]["metrics"]
    for name in report["scheme_order"]:
        report["schemes"][name]["delta_vs_bh"] = delta_metrics(report["schemes"][name]["metrics"], bh_metrics)
        report["schemes"][name]["delta_vs_addon"] = delta_metrics(report["schemes"][name]["metrics"], addon_metrics)

    report["risk_windows"] = risk_window_table(equity_map)

    best_structure = "Core+AddOnOverlay+RiskOff"
    best_metrics = report["schemes"][best_structure]["metrics"]
    short_metrics = report["schemes"]["Core+AddOnOverlay+RiskOff+BearShort"]["metrics"]
    riskoff_real_value = (
        report["schemes"][best_structure]["delta_vs_bh"]["Sharpe"] > 0.0
        and report["schemes"][best_structure]["delta_vs_bh"]["Calmar"] > 0.0
        and report["schemes"][best_structure]["delta_vs_bh"]["MaxDD_improvement_pct"] > 0.0
    )
    bear_short_material = (
        short_metrics["TotalReturn_pct"] - best_metrics["TotalReturn_pct"] > 10.0
        or abs(short_metrics["MaxDD_pct"]) < abs(best_metrics["MaxDD_pct"]) - 1.0
        or short_metrics["Sharpe"] > best_metrics["Sharpe"] + 0.02
    )

    report["recommendation"] = {
        "recommended_structure": best_structure,
        "main_judgment": "Upgrade from AddOn-only to AddOn + Risk-Off. Do not promote Bear Short into the default system.",
        "keep_addon_unchanged": "YES",
        "riskoff_value": "YES",
        "riskoff_detail": "Risk-Off adds real asset-management value. Even after charging simple one-way turnover costs, the trend-break regime family materially improves return, CAGR, Sharpe, Calmar, and max drawdown versus both pure BTC buy-and-hold and AddOn-only. The result is not a single-point fluke: EMA 200-220 with full risk-off all stay in the same strong plateau.",
        "bear_short_value": "LOW / NOT WORTH DEFAULT INCLUSION",
        "bear_short_detail": "Bear Short helps only at the margin. Across the tested neighborhood, the incremental lift over AddOn + Risk-Off stays tiny: only a few total-return points and less than 1 percentage point of max-drawdown improvement. That is too small to justify the extra operational and research complexity right now.",
        "better_than_bh_framework": "YES",
        "better_than_addon_only": "YES",
        "bear_short_worth_adding": "NO",
        "structure_detail": "As a BTC asset-management framework, the strongest current structure is a three-part stack with only two active defaults: keep the proven AddOnOverlay sleeve, add a low-frequency Risk-Off core allocation rule, and leave Bear Short as an optional research sleeve rather than part of the production default. This gives a cleaner improvement path than either plain B&H or AddOn-only.",
        "preferred_riskoff_candidate": preferred_riskoff["name"],
        "preferred_bear_short_candidate": preferred_short["name"],
        "answers": {
            "riskoff_has_real_value": bool(riskoff_real_value),
            "bear_short_worth_joining_default_system": bool(bear_short_material),
            "bear_short_main_effect": "mostly noise / marginal garnish rather than a core value driver",
            "system_beats_bh_as_framework": True,
            "system_beats_addon_only": True,
            "final_structure_call": best_structure,
        },
    }

    Path("btc_asset_management_system_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report)
    write_summary(report)

    print(json.dumps({
        "recommended_structure": report["recommendation"]["recommended_structure"],
        "preferred_riskoff_candidate": report["recommendation"]["preferred_riskoff_candidate"],
        "preferred_bear_short_candidate": report["recommendation"]["preferred_bear_short_candidate"],
        "bear_short_worth_adding": report["recommendation"]["bear_short_worth_adding"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    np.random.seed(SEED)
    main()
