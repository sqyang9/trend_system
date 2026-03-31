#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small-neighborhood parameter audit for full-stack Risk-Off / re-entry."""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_addon_grading_study import (
    constant_weight_plan,
    current_research_optimal as formal_current_research_optimal,
    prepare_base_run,
)
from v90_asset_management_system_aligned import (
    INIT_EQUITY,
    apply_side_bps,
    compute_metrics,
    current_research_optimal as riskoff_current_research_optimal,
    simulate_core,
    slippage_bps,
)
from v90_riskoff_promotion_v2 import build_indicator_cache
from v95_range_rotation_mean_reversion_audit import make_range_rotation_params, run_range_rotation_candidate
from v96_range_rotation_mean_reversion_s3_audit import scenario_systems
from v116_fullstack_riskoff_adoption_audit import SCENARIOS, path_bundle
from v117_fullstack_riskoff_adoption_default_stress import extended_metrics


OUTDIR = ROOT / "riskoff_reentry_param_audit"
REPORT_MD = OUTDIR / "RISKOFF_REENTRY_SIGNAL_PARAM_REPORT.md"
REPORT_JSON = OUTDIR / "riskoff_reentry_signal_param_report.json"
TABLE_CSV = OUTDIR / "RISKOFF_REENTRY_SIGNAL_PARAM_TABLE.csv"
PLOTS_HTML = OUTDIR / "RISKOFF_REENTRY_SIGNAL_PARAM_PLOTS.html"


def compute_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def build_first5_mapping(df_5m: pd.DataFrame, df_4h_index: pd.Index) -> Dict[pd.Timestamp, pd.Series | None]:
    d5 = ensure_datetime(df_5m).set_index("timestamp").sort_index()
    mapping: Dict[pd.Timestamp, pd.Series | None] = {}
    for ts in df_4h_index:
        first = d5[(d5.index >= ts) & (d5.index < ts + timedelta(hours=4))]
        mapping[ts] = first.iloc[0] if len(first) else None
    return mapping


def forced_exit_price(ts: pd.Timestamp, row_4h: pd.Series, first5: pd.Series | None, params) -> float:
    raw = float(row_4h["open"])
    bar_5m = None
    if params.entry_execution_mode == "live_runner_next_5m_close" and first5 is not None:
        raw = float(first5["close"])
        bar_5m = first5
    bps = slippage_bps(params, row_4h, bar_5m)
    return float(apply_side_bps(raw, "sell", bps))


def simulate_trade_events_with_gate_cached(
    df_4h: pd.DataFrame,
    trades: pd.DataFrame,
    core_gate: pd.Series,
    params,
    weight_col: str,
    default_weight: float,
    first5_map: Dict[pd.Timestamp, pd.Series | None],
) -> Dict:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    gate = core_gate.reindex(d4.index).ffill().fillna(1.0).astype(float)

    items = trades.copy()
    items["entry_time"] = pd.to_datetime(items["entry_time"], utc=True)
    items["exit_time"] = pd.to_datetime(items["exit_time"], utc=True)
    items = items.sort_values("entry_time").reset_index(drop=True)

    cash = float(INIT_EQUITY)
    qty = 0.0
    current_weight = 0.0
    active_exit_time = None
    active_exit_price = None
    accepted = 0
    forced_exits = 0
    rows: List[Dict] = []

    entry_ptr = 0
    for ts, row in d4.iterrows():
        gate_on = bool(gate.loc[ts] > 0.9999)

        if qty > 0.0 and not gate_on:
            px = forced_exit_price(ts, row, first5_map.get(ts), params)
            cash += qty * px * (1.0 - float(params.commission_pct) / 100.0)
            qty = 0.0
            current_weight = 0.0
            active_exit_time = None
            active_exit_price = None
            forced_exits += 1

        if qty > 0.0 and active_exit_time is not None and active_exit_time <= ts:
            px = float(active_exit_price)
            cash += qty * px * (1.0 - float(params.commission_pct) / 100.0)
            qty = 0.0
            current_weight = 0.0
            active_exit_time = None
            active_exit_price = None

        while entry_ptr < len(items) and items.loc[entry_ptr, "entry_time"] <= ts:
            rec = items.loc[entry_ptr]
            rec_gate = bool(gate.reindex([rec["entry_time"]], method="ffill").fillna(1.0).iloc[0] > 0.9999)
            if qty <= 0.0 and gate_on and rec_gate:
                weight = float(rec[weight_col]) if weight_col in rec and pd.notna(rec[weight_col]) else float(default_weight)
                entry_price = float(rec["entry_price"])
                if entry_price > 0.0 and weight > 0.0:
                    target_qty = (weight * cash) / max(entry_price * (1.0 + float(params.commission_pct) / 100.0), 1e-12)
                    cost = target_qty * entry_price * (1.0 + float(params.commission_pct) / 100.0)
                    cash -= cost
                    qty = target_qty
                    current_weight = weight
                    active_exit_time = pd.Timestamp(rec["exit_time"])
                    active_exit_price = float(rec["exit_price"])
                    accepted += 1
            entry_ptr += 1

        equity = cash + qty * float(row["close"])
        rows.append({"time": ts, "equity": equity, "weight": current_weight if qty > 0.0 else 0.0})

    out = pd.DataFrame(rows).set_index("time")
    return {
        "equity": out["equity"].astype(float),
        "weight": out["weight"].astype(float),
        "active_ratio_pct": float((out["weight"] > 0.0).mean() * 100.0),
        "accepted_trade_count": int(accepted),
        "forced_exit_count": int(forced_exits),
    }


def fullstack_combo_cached(
    df_5m: pd.DataFrame,
    df_4h: pd.DataFrame,
    formal_payload: Dict,
    plan: pd.DataFrame,
    rr_result: Dict,
    core_target: pd.Series,
    riskoff_params,
    first5_map: Dict[pd.Timestamp, pd.Series | None],
) -> Dict:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    core_sim = simulate_core(df_5m, df_4h, core_target.reindex(d4.index).ffill().fillna(1.0), riskoff_params, riskoff_params.entry_execution_mode)
    core_eq = core_sim["equity"]["equity"].reindex(d4.index).ffill().bfill().astype(float)
    core_exp = core_sim["equity"]["exposure"].reindex(d4.index).ffill().bfill().astype(float)

    s1 = simulate_trade_events_with_gate_cached(df_4h, plan, core_exp, riskoff_params, "addon_weight", 1.0, first5_map)
    s2 = simulate_trade_events_with_gate_cached(df_4h, rr_result["trade_meta"], core_exp, riskoff_params, "__missing__", 1.0, first5_map)

    combo_eq = core_eq + (s1["equity"] - INIT_EQUITY) + (s2["equity"] - INIT_EQUITY)
    combo_exp = core_exp + s1["weight"] + s2["weight"]
    metrics = extended_metrics({"combo_equity": combo_eq, "combo_metrics": compute_metrics(combo_eq, combo_exp)})
    return {
        "combo_equity": combo_eq.astype(float),
        "combo_exposure": combo_exp.astype(float),
        "metrics": metrics,
        "path": path_bundle(combo_eq),
        "avg_total_exposure_pct": float(combo_exp.mean() * 100.0),
        "peak_total_exposure_pct": float(combo_exp.max() * 100.0),
        "avg_core_exposure_pct": float(core_exp.mean() * 100.0),
        "riskoff_active_ratio_pct": float((core_exp < 0.9999).mean() * 100.0),
        "sleeve1_active_ratio_pct": float(s1["active_ratio_pct"]),
        "sleeve2_active_ratio_pct": float(s2["active_ratio_pct"]),
        "sleeve1_accepted_trades": int(s1["accepted_trade_count"]),
        "sleeve2_accepted_trades": int(s2["accepted_trade_count"]),
        "sleeve1_forced_exits": int(s1["forced_exit_count"]),
        "sleeve2_forced_exits": int(s2["forced_exit_count"]),
        "causality": core_sim["causality"],
    }


def build_indicators(df_4h: pd.DataFrame, params, ema_len: int) -> pd.DataFrame:
    base = build_indicator_cache(df_4h, params, [ema_len], ensure_datetime(df_4h)["timestamp"])[ema_len].copy()
    out = base.copy()
    out["weekly_close"] = out["close"].resample("W-SUN").last().reindex(out.index, method="ffill")
    return out


def add_rsi_columns(indicators: pd.DataFrame, weekly_periods: List[int], h4_periods: List[int]) -> pd.DataFrame:
    out = indicators.copy()
    weekly_close = out["close"].resample("W-SUN").last()
    for weekly_period in sorted(set(weekly_periods)):
        out[f"weekly_rsi_{weekly_period}"] = compute_rsi(weekly_close, weekly_period).reindex(out.index, method="ffill")
    for h4_period in sorted(set(h4_periods)):
        out[f"h4_rsi_{h4_period}"] = compute_rsi(out["close"].astype(float), h4_period)
    return out


def build_target(indicators: pd.DataFrame, spec: Dict) -> pd.Series:
    bearish = (indicators["close"] < indicators["ema"]) & (indicators["ema_slope"] < 0)
    close_confirm = indicators["close"] > indicators["ema"]

    if spec["reentry_family"] == "weekly_rsi_hold":
        trigger = (indicators[f"weekly_rsi_{spec['rsi_period']}"] <= float(spec["threshold"])).fillna(False)
    elif spec["reentry_family"] == "h4_rsi_hold":
        trigger = (indicators[f"h4_rsi_{spec['rsi_period']}"] <= float(spec["threshold"])).fillna(False)
    else:
        raise ValueError(f"Unknown re-entry family: {spec['reentry_family']}")

    weights: List[float] = []
    state = "normal"
    bear_count = 0
    close_count = 0
    for is_bear, is_close, trig in zip(bearish.fillna(False).tolist(), close_confirm.fillna(False).tolist(), trigger.tolist()):
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


def candidate_specs() -> List[Dict]:
    specs: List[Dict] = []
    specs.extend([
        {"group": "weekly_threshold", "label": "WRSI14_35_EMA220", "reentry_family": "weekly_rsi_hold", "rsi_period": 14, "threshold": 35.0, "ema_len": 220},
        {"group": "weekly_threshold", "label": "WRSI14_30_EMA220", "reentry_family": "weekly_rsi_hold", "rsi_period": 14, "threshold": 30.0, "ema_len": 220},
        {"group": "weekly_threshold", "label": "WRSI14_25_EMA220", "reentry_family": "weekly_rsi_hold", "rsi_period": 14, "threshold": 25.0, "ema_len": 220},
        {"group": "weekly_threshold", "label": "WRSI14_20_EMA220", "reentry_family": "weekly_rsi_hold", "rsi_period": 14, "threshold": 20.0, "ema_len": 220},
    ])
    specs.extend([
        {"group": "weekly_length", "label": "WRSI10_30_EMA220", "reentry_family": "weekly_rsi_hold", "rsi_period": 10, "threshold": 30.0, "ema_len": 220},
        {"group": "weekly_length", "label": "WRSI14_30_EMA220", "reentry_family": "weekly_rsi_hold", "rsi_period": 14, "threshold": 30.0, "ema_len": 220},
        {"group": "weekly_length", "label": "WRSI18_30_EMA220", "reentry_family": "weekly_rsi_hold", "rsi_period": 18, "threshold": 30.0, "ema_len": 220},
    ])
    specs.extend([
        {"group": "h4_threshold", "label": "H4RSI14_12_EMA220", "reentry_family": "h4_rsi_hold", "rsi_period": 14, "threshold": 12.0, "ema_len": 220},
        {"group": "h4_threshold", "label": "H4RSI14_10_EMA220", "reentry_family": "h4_rsi_hold", "rsi_period": 14, "threshold": 10.0, "ema_len": 220},
        {"group": "h4_threshold", "label": "H4RSI14_8_EMA220", "reentry_family": "h4_rsi_hold", "rsi_period": 14, "threshold": 8.0, "ema_len": 220},
        {"group": "h4_threshold", "label": "H4RSI14_6_EMA220", "reentry_family": "h4_rsi_hold", "rsi_period": 14, "threshold": 6.0, "ema_len": 220},
    ])
    specs.extend([
        {"group": "h4_length", "label": "H4RSI10_10_EMA220", "reentry_family": "h4_rsi_hold", "rsi_period": 10, "threshold": 10.0, "ema_len": 220},
        {"group": "h4_length", "label": "H4RSI14_10_EMA220", "reentry_family": "h4_rsi_hold", "rsi_period": 14, "threshold": 10.0, "ema_len": 220},
        {"group": "h4_length", "label": "H4RSI18_10_EMA220", "reentry_family": "h4_rsi_hold", "rsi_period": 18, "threshold": 10.0, "ema_len": 220},
    ])
    for ema_len in [120, 200, 220, 250]:
        specs.append(
            {"group": "sell_ema_weekly30", "label": f"WRSI14_30_EMA{ema_len}", "reentry_family": "weekly_rsi_hold", "rsi_period": 14, "threshold": 30.0, "ema_len": ema_len}
        )
        specs.append(
            {"group": "sell_ema_h4_10", "label": f"H4RSI14_10_EMA{ema_len}", "reentry_family": "h4_rsi_hold", "rsi_period": 14, "threshold": 10.0, "ema_len": ema_len}
        )
    for spec in specs:
        spec["name"] = f"{spec['group']}__{spec['label']}"
    return specs


def score_row(row: Dict) -> tuple:
    return (
        float(row["metrics"]["Calmar"]),
        float(abs(row["metrics"]["MaxDD_pct"])) * -1.0,
        float(row["metrics"]["TotalReturn_pct"]),
    )


def evaluate_specs(df_5m: pd.DataFrame, df_4h: pd.DataFrame, scenario: Dict, specs: List[Dict]) -> Dict[str, Dict]:
    formal_params = formal_current_research_optimal(**scenario["formal_overrides"])
    range_params = make_range_rotation_params(**scenario["formal_overrides"])
    formal_payload = scenario_systems(formal_params, range_params, df_5m, df_4h)
    base = prepare_base_run(df_5m, df_4h, formal_params)
    plan = constant_weight_plan(base["entries"], 1.0)
    rr_result = run_range_rotation_candidate(df_5m, df_4h, range_params)
    first5_map = build_first5_mapping(df_5m, formal_sys_index := formal_payload["systems"]["Core+ConstAddOn[1.00x]+RangeRotation"]["combo_equity"].index)

    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    formal_sys = formal_payload["systems"]["Core+ConstAddOn[1.00x]+RangeRotation"]
    results: Dict[str, Dict] = {
        "FormalPortfolio": {
            "combo_equity": formal_sys["combo_equity"].astype(float),
            "combo_exposure": formal_sys["combo_exposure"].astype(float),
            "metrics": extended_metrics({"combo_equity": formal_sys["combo_equity"], "combo_metrics": formal_sys["combo_metrics"]}),
            "path": path_bundle(formal_sys["combo_equity"]),
            "avg_total_exposure_pct": float(formal_sys["combo_exposure"].mean() * 100.0),
            "avg_core_exposure_pct": 100.0,
            "riskoff_active_ratio_pct": 0.0,
            "sleeve1_active_ratio_pct": float((formal_payload["systems"]["Core+ConstAddOn[1.00x]"]["sleeve"]["weight"] > 0).mean() * 100.0),
            "sleeve2_active_ratio_pct": float((formal_payload["candidate_sleeve"]["weight"] > 0).mean() * 100.0),
            "spec": None,
        }
    }

    indicator_cache: Dict[int, pd.DataFrame] = {}
    weekly_periods = [spec["rsi_period"] for spec in specs if spec["reentry_family"] == "weekly_rsi_hold"]
    h4_periods = [spec["rsi_period"] for spec in specs if spec["reentry_family"] == "h4_rsi_hold"]
    for ema_len in sorted({spec["ema_len"] for spec in specs}):
        ind = build_indicators(df_4h, riskoff_params, ema_len)
        ind = add_rsi_columns(ind, weekly_periods=weekly_periods, h4_periods=h4_periods)
        indicator_cache[ema_len] = ind

    for spec in specs:
        ind = indicator_cache[spec["ema_len"]]
        target = build_target(ind, spec)
        core_target = (target.reindex(formal_sys["combo_equity"].index).ffill().fillna(1.0).astype(float) >= 0.9999).astype(float)
        row = fullstack_combo_cached(df_5m, df_4h, formal_payload, plan, rr_result, core_target, riskoff_params, first5_map)
        row["spec"] = spec
        row["trigger_count"] = int(
            ((ind[f"weekly_rsi_{spec['rsi_period']}"] <= float(spec["threshold"])) if spec["reentry_family"] == "weekly_rsi_hold" else (ind[f"h4_rsi_{spec['rsi_period']}"] <= float(spec["threshold"]))).fillna(False).sum()
        )
        results[spec["name"]] = row
    return results


def shortlist(default_rows: Dict[str, Dict], specs: List[Dict]) -> Dict[str, str]:
    winners: Dict[str, str] = {}
    groups = sorted({spec["group"] for spec in specs})
    for group in groups:
        names = [spec["name"] for spec in specs if spec["group"] == group]
        winners[group] = max(names, key=lambda name: score_row(default_rows[name]))
    return winners


def flatten_table(rows: Dict[str, Dict], formal_key: str = "FormalPortfolio") -> pd.DataFrame:
    formal = rows[formal_key]
    records: List[Dict] = []
    for name, row in rows.items():
        if name == formal_key:
            continue
        spec = row["spec"]
        records.append({
            "group": spec["group"],
            "name": name,
            "label": spec["label"],
            "family": spec["reentry_family"],
            "rsi_period": spec["rsi_period"],
            "threshold": spec["threshold"],
            "ema_len": spec["ema_len"],
            "trigger_count": row["trigger_count"],
            "return_pct": row["metrics"]["TotalReturn_pct"],
            "cagr_pct": row["metrics"]["CAGR_pct"],
            "sharpe": row["metrics"]["Sharpe"],
            "calmar": row["metrics"]["Calmar"],
            "maxdd_pct": row["metrics"]["MaxDD_pct"],
            "recovery_days": row["metrics"]["recovery_days_from_maxdd"],
            "worst_3m_pct": row["path"]["worst_3m_cluster_return_pct"],
            "worst_6m_pct": row["path"]["worst_6m_cluster_return_pct"],
            "avg_total_exposure_pct": row["avg_total_exposure_pct"],
            "avg_core_exposure_pct": row["avg_core_exposure_pct"],
            "riskoff_active_ratio_pct": row["riskoff_active_ratio_pct"],
            "sleeve1_active_ratio_pct": row["sleeve1_active_ratio_pct"],
            "sleeve2_active_ratio_pct": row["sleeve2_active_ratio_pct"],
            "dreturn_vs_formal_pp": row["metrics"]["TotalReturn_pct"] - formal["metrics"]["TotalReturn_pct"],
            "dcalmar_vs_formal": row["metrics"]["Calmar"] - formal["metrics"]["Calmar"],
            "dmaxdd_vs_formal_pp": row["metrics"]["MaxDD_pct"] - formal["metrics"]["MaxDD_pct"],
        })
    return pd.DataFrame(records).sort_values(["group", "calmar", "return_pct"], ascending=[True, False, False])


def write_report(default_rows: Dict[str, Dict], stress_rows: Dict[str, Dict], winners: Dict[str, str], table: pd.DataFrame) -> None:
    formal = default_rows["FormalPortfolio"]
    lines = [
        "# Risk-Off Re-Entry Signal Parameter Audit",
        "",
        "- Scope: first-layer signal parameter audit only.",
        "- Architecture locked: `Formal Portfolio = Core + ConstAddOn[1.00x] + RangeRotation`.",
        "- Semantics locked: full-stack cash-like Risk-Off; when Risk-Off is active, `Core + Sleeve #1 + Sleeve #2` all flatten.",
        "- This audit isolates three dimensions rather than moving sell-side and re-entry together.",
        "",
        "## Formal Baseline",
        "",
        f"- Return `{formal['metrics']['TotalReturn_pct']:.2f}%`",
        f"- Calmar `{formal['metrics']['Calmar']:.3f}`",
        f"- MaxDD `{formal['metrics']['MaxDD_pct']:.2f}%`",
        "",
        "## Default Ranking By Family",
        "",
    ]

    for group in sorted(table["group"].unique()):
        lines.extend([
            f"### {group}",
            "",
            "| Name | Return% | Calmar | MaxDD% | Worst3m | Worst6m | AvgTotalExp% | RiskOffActive% | dReturn vs Formal | dCalmar | dMaxDD |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ])
        sub = table[table["group"] == group].sort_values(["calmar", "return_pct"], ascending=[False, False])
        for _, row in sub.iterrows():
            lines.append(
                f"| {row['label']} | {row['return_pct']:.2f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
                f"{row['worst_3m_pct']:.2f} | {row['worst_6m_pct']:.2f} | {row['avg_total_exposure_pct']:.2f} | "
                f"{row['riskoff_active_ratio_pct']:.2f} | {row['dreturn_vs_formal_pp']:+.2f}pp | "
                f"{row['dcalmar_vs_formal']:+.3f} | {row['dmaxdd_vs_formal_pp']:+.2f}pp |"
            )
        winner = winners[group]
        lines.extend(["", f"- Winner: `{table.loc[table['name'] == winner, 'label'].iloc[0]}`", ""])

    lines.extend([
        "## Stress Check On Family Winners",
        "",
        "| Winner | Stress dReturn vs Formal | Stress dCalmar vs Formal | Stress dMaxDD vs Formal |",
        "| --- | --- | --- | --- |",
    ])
    formal_stress = stress_rows["FormalPortfolio"]
    for group, name in winners.items():
        row = stress_rows[name]
        label = row["spec"]["label"]
        lines.append(
            f"| {label} | {row['metrics']['TotalReturn_pct'] - formal_stress['metrics']['TotalReturn_pct']:+.2f}pp | "
            f"{row['metrics']['Calmar'] - formal_stress['metrics']['Calmar']:+.3f} | "
            f"{row['metrics']['MaxDD_pct'] - formal_stress['metrics']['MaxDD_pct']:+.2f}pp |"
        )

    lines.extend([
        "",
        "## Conclusion",
        "",
        f"- Weekly threshold winner: `{default_rows[winners['weekly_threshold']]['spec']['label']}`",
        f"- Weekly length winner: `{default_rows[winners['weekly_length']]['spec']['label']}`",
        f"- 4h threshold winner: `{default_rows[winners['h4_threshold']]['spec']['label']}`",
        f"- 4h length winner: `{default_rows[winners['h4_length']]['spec']['label']}`",
        f"- Sell-side EMA winner with Weekly30 re-entry fixed: `{default_rows[winners['sell_ema_weekly30']]['spec']['label']}`",
        f"- Sell-side EMA winner with 4H10 re-entry fixed: `{default_rows[winners['sell_ema_h4_10']]['spec']['label']}`",
        "",
        "- Parameter interpretation should stay layered:",
        "  - first judge re-entry threshold and period",
        "  - then judge sell-side EMA separately with re-entry fixed",
        "  - do not cross-search these dimensions together",
    ])
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_plot(default_rows: Dict[str, Dict], winners: Dict[str, str]) -> None:
    show = ["FormalPortfolio", "weekly_threshold__WRSI14_30_EMA220", "h4_threshold__H4RSI14_10_EMA220"]
    for name in winners.values():
        if name not in show:
            show.append(name)
    labels = {
        "FormalPortfolio": "Formal Portfolio",
        "weekly_threshold__WRSI14_30_EMA220": "Incumbent Weekly30",
        "h4_threshold__H4RSI14_10_EMA220": "Incumbent 4H10",
    }
    colors = ["#0f172a", "#059669", "#dc2626", "#7c3aed", "#ea580c", "#0891b2", "#be123c", "#4d7c0f"]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, row_heights=[0.62, 0.38], subplot_titles=("Equity", "Underwater"))
    for idx, key in enumerate(show):
        series = default_rows[key]["combo_equity"]
        uw = (series / series.cummax() - 1.0) * 100.0
        name = labels[key] if key in labels else default_rows[key]["spec"]["label"]
        color = colors[idx % len(colors)]
        fig.add_trace(go.Scatter(x=series.index, y=series, mode="lines", name=name, line=dict(color=color, width=2.0)), row=1, col=1)
        fig.add_trace(go.Scatter(x=uw.index, y=uw, mode="lines", name=f"{name} UW", line=dict(color=color, width=1.1), showlegend=False), row=2, col=1)
    fig.update_layout(template="plotly_white", hovermode="x unified", height=980, title="Risk-Off Re-Entry Signal Parameter Audit")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Underwater %", row=2, col=1)
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    specs = candidate_specs()

    default_rows = evaluate_specs(df_5m, df_4h, SCENARIOS[0], specs)
    winners = shortlist(default_rows, specs)
    stress_names = sorted(set(winners.values()) | {"weekly_threshold__WRSI14_30_EMA220", "h4_threshold__H4RSI14_10_EMA220"})
    stress_specs = [spec for spec in specs if spec["name"] in stress_names]
    stress_rows = evaluate_specs(df_5m, df_4h, SCENARIOS[1], stress_specs)

    table = flatten_table(default_rows)
    table.to_csv(TABLE_CSV, index=False)
    write_report(default_rows, stress_rows, winners, table)
    write_plot(default_rows, winners)

    payload = {
        "default": {
            key: {
                **{k: v for k, v in row.items() if k not in {"combo_equity", "combo_exposure"}},
                "combo_equity_last": float(row["combo_equity"].iloc[-1]),
            }
            for key, row in default_rows.items()
        },
        "stress": {
            key: {
                **{k: v for k, v in row.items() if k not in {"combo_equity", "combo_exposure"}},
                "combo_equity_last": float(row["combo_equity"].iloc[-1]),
            }
            for key, row in stress_rows.items()
        },
        "winners": {group: default_rows[name]["spec"]["label"] for group, name in winners.items()},
    }
    REPORT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_MD), "table": str(TABLE_CSV), "plots": str(PLOTS_HTML)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
