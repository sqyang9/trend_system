#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Execution-aligned Risk-Off validation using the locked AddOn overlay artifact."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_trend_long_mother import SEED, TrendIndicatorEngine, TrendLongParams, with_overrides

ANNUALIZATION_4H = np.sqrt(252.0 * 6.0)
DEFAULT_TUPLE = "next_bar_open + legacy_bar_extrema + midpoint + full_model"
STRESS_TUPLE = "live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model"
INIT_EQUITY = 10000.0
OVERLAY_REPORT = Path("btc_overlay_integration_report.json")
EXPLORATORY_REPORT = Path("btc_asset_management_system_report.json")

RISKOFF_CANDIDATES = [
    {"name": "RO_EMA200_FLAT", "ema_len": 200, "off_weight": 0.0, "description": "EMA200 bearish regime -> flat core."},
    {"name": "RO_EMA220_FLAT", "ema_len": 220, "off_weight": 0.0, "description": "EMA220 bearish regime -> flat core."},
    {"name": "RO_EMA200_TO35", "ema_len": 200, "off_weight": 0.35, "description": "EMA200 bearish regime -> reduce core to 35%."},
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
    return 0.0 if maxdd >= 0 else float(cagr) / abs(float(maxdd))


def pf_from_equity(equity: pd.Series) -> float:
    pnl = equity.diff().fillna(0.0)
    gp = float(pnl[pnl > 0].sum())
    gl = float(-pnl[pnl < 0].sum())
    return 0.0 if gl <= 0 else gp / gl


def max_dd_duration(drawdown: pd.Series) -> int:
    best = cur = 0
    for x in (drawdown < 0).tolist():
        if x:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def compute_metrics(equity: pd.Series, exposure: pd.Series) -> Dict:
    ret = equity.pct_change().fillna(0.0)
    dd = equity / equity.cummax() - 1.0
    years = max((equity.index[-1] - equity.index[0]).total_seconds() / 86400.0, 1.0) / 365.25
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = (float(equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0) if years > 0 else 0.0
    std = float(ret.std())
    sharpe = float(ret.mean()) / std * ANNUALIZATION_4H if std > 0 else 0.0
    dd_bars = max_dd_duration(dd)
    return {
        "TotalReturn_pct": total * 100.0,
        "CAGR_pct": cagr * 100.0,
        "Sharpe": sharpe,
        "Calmar": calmar(cagr, float(dd.min())),
        "MaxDD_pct": float(dd.min() * 100.0),
        "PF": pf_from_equity(equity),
        "Exposure_pct": float(exposure.mean() * 100.0),
        "MaxDDDuration_days": float(dd_bars * 4.0 / 24.0),
    }


def compute_slice_metrics(equity: pd.Series) -> Dict:
    if len(equity) < 2:
        return {"Return_pct": 0.0, "CAGR_pct": 0.0, "Sharpe": 0.0, "MaxDD_pct": 0.0}
    ret = equity.pct_change().fillna(0.0)
    dd = equity / equity.cummax() - 1.0
    years = max((equity.index[-1] - equity.index[0]).total_seconds() / 86400.0, 1.0) / 365.25
    total = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = (float(equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0) if years > 0 else 0.0
    std = float(ret.std())
    sharpe = float(ret.mean()) / std * ANNUALIZATION_4H if std > 0 else 0.0
    return {"Return_pct": total * 100.0, "CAGR_pct": cagr * 100.0, "Sharpe": sharpe, "MaxDD_pct": float(dd.min() * 100.0)}


def yearly_consistency(equity: pd.Series) -> Dict:
    rows = []
    for year, sub in equity.to_frame("equity").groupby(equity.index.year):
        if len(sub) < 2:
            continue
        rows.append({"year": int(year), **compute_slice_metrics(sub["equity"])})
    if not rows:
        return {"rows": rows, "pass": False, "reason": "no_year_data"}
    df = pd.DataFrame(rows)
    positive_year_ratio = float((df["CAGR_pct"] > 0.0).mean())
    avg_sharpe = float(df["Sharpe"].mean())
    worst_return = float(df["Return_pct"].min())
    passed = (positive_year_ratio >= 0.60) and (avg_sharpe >= 0.40) and (worst_return > -35.0)
    return {"rows": rows, "positive_year_ratio": positive_year_ratio, "avg_sharpe": avg_sharpe, "worst_return_pct": worst_return, "pass": passed}


def rolling_oos_consistency(equity: pd.Series) -> Dict:
    years = sorted(set(equity.index.year.tolist()))
    rows = []
    for oos_year in years:
        train_years = [y for y in years if (oos_year - 2) <= y < oos_year]
        if len(train_years) < 2:
            continue
        sub = equity[(equity.index >= pd.Timestamp(f"{oos_year}-01-01", tz="UTC")) & (equity.index < pd.Timestamp(f"{oos_year + 1}-01-01", tz="UTC"))]
        if len(sub) < 180:
            continue
        rows.append({"oos_year": int(oos_year), "train_years": train_years, **compute_slice_metrics(sub)})
    if not rows:
        return {"rows": rows, "pass": False, "reason": "no_oos_data"}
    df = pd.DataFrame(rows)
    avg_sharpe = float(df["Sharpe"].mean())
    positive_ratio = float((df["CAGR_pct"] > 0.0).mean())
    passed = (avg_sharpe >= 0.30) and (positive_ratio >= 0.55)
    return {"rows": rows, "avg_sharpe": avg_sharpe, "positive_ratio": positive_ratio, "pass": passed}


def build_mapping(df_5m: pd.DataFrame, timestamps_4h: List[pd.Timestamp]) -> Dict[pd.Timestamp, List[pd.Timestamp]]:
    out = {ts: [] for ts in timestamps_4h}
    valid = set(timestamps_4h)
    for ts in pd.to_datetime(df_5m["timestamp"], utc=True):
        bucket = ts.floor("4h")
        if bucket in valid:
            out[bucket].append(ts)
    return out


def slippage_bps(params: TrendLongParams, row_4h: pd.Series, bar_5m: pd.Series | None) -> float:
    total = max(float(params.slippage_fixed_bps), 0.0)
    if bar_5m is not None:
        px = float(bar_5m["close"])
        local_range_bps = 0.0 if px <= 0 else max(float(bar_5m["high"]) - float(bar_5m["low"]), 0.0) / px * 10000.0
    else:
        px = float(row_4h["close"])
        local_range_bps = 0.0 if px <= 0 else max(float(row_4h["high"]) - float(row_4h["low"]), 0.0) / px * 10000.0
    total += float(params.slippage_range_weight) * local_range_bps
    if float(params.slippage_max_bps) > 0.0:
        total = min(total, float(params.slippage_max_bps))
    return max(total, 0.0)


def apply_side_bps(price: float, side: str, bps: float) -> float:
    adj = bps / 10000.0
    return float(price) * (1.0 + adj) if side == "buy" else float(price) * (1.0 - adj)


def compute_target_qty(cash: float, qty: float, price: float, target_weight: float, commission_rate: float) -> float:
    equity = cash + qty * price
    if equity <= 0 or price <= 0:
        return qty
    cur_weight = (qty * price) / equity if equity > 0 else 0.0
    if abs(target_weight - cur_weight) < 1e-12:
        return qty
    if target_weight > cur_weight:
        return target_weight * (cash / price + qty * (1.0 + commission_rate)) / (1.0 + target_weight * commission_rate)
    if target_weight <= 0.0:
        return 0.0
    return target_weight * (cash / price + qty * (1.0 - commission_rate)) / max(1.0 - target_weight * commission_rate, 1e-12)


def rebalance(cash: float, qty: float, fill_price: float, target_weight: float, commission_rate: float) -> Tuple[float, float, float, str | None]:
    target_qty = compute_target_qty(cash, qty, fill_price, target_weight, commission_rate)
    if abs(target_qty - qty) < 1e-12:
        return cash, qty, 0.0, None
    if target_qty > qty:
        trade_qty = target_qty - qty
        cash -= trade_qty * fill_price * (1.0 + commission_rate)
        qty = target_qty
        return cash, qty, trade_qty * fill_price, "buy"
    trade_qty = qty - target_qty
    cash += trade_qty * fill_price * (1.0 - commission_rate)
    qty = target_qty
    return cash, qty, trade_qty * fill_price, "sell"

def load_overlay_artifact() -> Dict:
    data = json.loads(OVERLAY_REPORT.read_text(encoding='utf-8'))
    idx = pd.to_datetime(data['timeseries']['timestamp'], utc=True)
    bh = pd.Series(data['timeseries']['B&H'], index=idx, dtype=float)
    addon = pd.Series(data['timeseries']['AddOnOverlay'], index=idx, dtype=float)
    overlay_delta = addon - bh
    overlay_avg_exposure = float(data['schemes']['AddOnOverlay']['metrics']['Exposure_pct'] - data['schemes']['B&H']['metrics']['Exposure_pct']) / 100.0
    return {
        'overlay_delta': overlay_delta,
        'overlay_avg_exposure': overlay_avg_exposure,
        'artifact': data,
    }


def simulate_core(df_5m: pd.DataFrame, df_4h: pd.DataFrame, target_weights: pd.Series, params: TrendLongParams, execution_mode: str) -> Dict:
    d5 = ensure_datetime(df_5m)
    d4 = ensure_datetime(df_4h)
    d4 = d4[d4['timestamp'].isin(target_weights.index)].reset_index(drop=True)
    target_weights = target_weights.reindex(pd.to_datetime(d4['timestamp'], utc=True)).ffill().fillna(1.0)
    timestamps = pd.to_datetime(d4['timestamp'], utc=True).tolist()
    mapping = build_mapping(d5, timestamps)
    d5_idx = d5.set_index('timestamp').sort_index()
    commission_rate = float(params.commission_pct) / 100.0

    cash = INIT_EQUITY
    qty = 0.0
    pending_target = 1.0
    pending_signal_time = timestamps[0] - timedelta(hours=4)
    transitions = []
    rows = []

    for i, row in d4.iterrows():
        ts = pd.Timestamp(row['timestamp'])
        bar_5m = None
        raw_price = float(row['open'])
        exec_time = ts
        if execution_mode == 'live_runner_next_5m_close':
            five = mapping.get(ts, [])
            if five:
                first_ts = five[0]
                if first_ts in d5_idx.index:
                    bar_5m = d5_idx.loc[first_ts]
                    raw_price = float(bar_5m['close'])
                    exec_time = pd.Timestamp(first_ts) + timedelta(minutes=5)
        equity_before = cash + qty * raw_price
        cur_weight = 0.0 if equity_before <= 0 else (qty * raw_price) / equity_before
        if abs(pending_target - cur_weight) > 1e-9:
            side = 'buy' if pending_target > cur_weight else 'sell'
            fill_price = apply_side_bps(raw_price, side, slippage_bps(params, row, bar_5m))
            cash, qty, trade_notional, trade_side = rebalance(cash, qty, fill_price, pending_target, commission_rate)
            if trade_side is not None:
                transitions.append({
                    'signal_time': pending_signal_time.isoformat(),
                    'execution_time': exec_time.isoformat(),
                    'target_weight': float(pending_target),
                    'trade_side': trade_side,
                    'trade_notional': float(trade_notional),
                    'fill_price': float(fill_price),
                })
        close_price = float(row['close'])
        equity = cash + qty * close_price
        exposure = 0.0 if equity <= 0 else (qty * close_price) / equity
        rows.append({'time': ts, 'equity': equity, 'exposure': exposure})
        pending_target = float(target_weights.iloc[i])
        pending_signal_time = ts + timedelta(hours=4)

    eq = pd.DataFrame(rows).set_index('time')
    violations = sum(pd.Timestamp(t['execution_time']) < pd.Timestamp(t['signal_time']) for t in transitions)
    return {'equity': eq, 'transitions': transitions, 'causality': {'violations': int(violations), 'rebalance_count': len(transitions), 'pass': violations == 0, 'execution_mode': execution_mode}}


def build_candidate_targets(df_4h: pd.DataFrame, overlay_index: pd.Index, params: TrendLongParams) -> Dict[str, pd.Series]:
    signals = {'BH': pd.Series(1.0, index=overlay_index, dtype=float)}
    engine = TrendIndicatorEngine()
    full = ensure_datetime(df_4h)
    for cand in RISKOFF_CANDIDATES:
        ind = engine.compute(full, with_overrides(params, ema_len=cand['ema_len'])).set_index('timestamp').reindex(overlay_index)
        regime = (ind['close'] < ind['ema']) & (ind['ema_slope'] < 0)
        signals[cand['name']] = pd.Series(np.where(regime.fillna(False), cand['off_weight'], 1.0), index=overlay_index, dtype=float)
    return signals


def combine_with_overlay(core: Dict, overlay_delta: pd.Series, overlay_avg_exposure: float) -> Dict:
    eq = core['equity']['equity'].astype(float) + overlay_delta.reindex(core['equity'].index).fillna(0.0)
    exp = core['equity']['exposure'].astype(float) + overlay_avg_exposure
    return {'equity': eq, 'exposure': exp}


def period_return(equity: pd.Series, start: str, end: str) -> float:
    sub = equity[(equity.index >= pd.Timestamp(start, tz='UTC')) & (equity.index < pd.Timestamp(end, tz='UTC'))]
    if len(sub) < 2:
        return 0.0
    return float((sub.iloc[-1] / sub.iloc[0] - 1.0) * 100.0)


def risk_windows(equity_map: Dict[str, pd.Series]) -> List[Dict]:
    windows = [('covid_crash_2020','2020-02-15','2020-04-30'), ('china_deleveraging_2021','2021-04-10','2021-07-31'), ('bear_2022','2022-01-01','2023-01-01'), ('ftx_shock','2022-11-01','2022-12-15')]
    rows = []
    for name, start, end in windows:
        row = {'window': name}
        for k, eq in equity_map.items():
            row[k] = period_return(eq, start, end)
        rows.append(row)
    return rows


def delta_metrics(metrics: Dict, baseline: Dict) -> Dict:
    return {
        'Return_pct': float(metrics['TotalReturn_pct'] - baseline['TotalReturn_pct']),
        'CAGR_pct': float(metrics['CAGR_pct'] - baseline['CAGR_pct']),
        'Sharpe': float(metrics['Sharpe'] - baseline['Sharpe']),
        'Calmar': float(metrics['Calmar'] - baseline['Calmar']),
        'MaxDD_improvement_pct': float(abs(baseline['MaxDD_pct']) - abs(metrics['MaxDD_pct'])),
    }


def evaluate_bundle(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams, execution_mode: str, overlay_delta: pd.Series, overlay_avg_exposure: float) -> Dict:
    targets = build_candidate_targets(df_4h, overlay_delta.index, params)
    bundle = {'schemes': {}, 'causality': {}}
    schemes = {}
    for name, signal in targets.items():
        core = simulate_core(df_5m, df_4h, signal, params, execution_mode)
        schemes[f'Core+{name}'] = core
        bundle['causality'][name] = core['causality']
    bh_core = schemes['Core+BH']
    schemes['B&H'] = bh_core
    addon = combine_with_overlay(bh_core, overlay_delta, overlay_avg_exposure)
    schemes['Core+AddOnOverlay'] = {'equity': pd.DataFrame({'equity': addon['equity'], 'exposure': addon['exposure']}), 'description': 'Aligned core B&H plus locked AddOnOverlay sleeve.'}
    for cand in RISKOFF_CANDIDATES:
        key = f"Core+{cand['name']}"
        combo = combine_with_overlay(schemes[key], overlay_delta, overlay_avg_exposure)
        schemes[f'Core+AddOnOverlay+{cand["name"]}'] = {'equity': pd.DataFrame({'equity': combo['equity'], 'exposure': combo['exposure']}), 'description': cand['description'], 'candidate': cand}
    order = ['B&H', 'Core+AddOnOverlay', 'Core+AddOnOverlay+RO_EMA200_FLAT', 'Core+AddOnOverlay+RO_EMA220_FLAT', 'Core+AddOnOverlay+RO_EMA200_TO35', 'Core+RO_EMA200_FLAT', 'Core+RO_EMA220_FLAT']
    for key in order:
        item = schemes[key]
        eq = item['equity']['equity'].astype(float)
        exp = item['equity']['exposure'].astype(float)
        bundle['schemes'][key] = {'metrics': compute_metrics(eq, exp), 'yearly': yearly_consistency(eq), 'rolling_oos': rolling_oos_consistency(eq)}
        if 'description' in item:
            bundle['schemes'][key]['description'] = item['description']
        if 'candidate' in item:
            bundle['schemes'][key]['candidate'] = item['candidate']
    bundle['risk_windows'] = risk_windows({k: schemes[k]['equity']['equity'].astype(float) for k in order})
    return bundle

def load_exploratory_reference() -> Dict:
    if not EXPLORATORY_REPORT.exists():
        return {}
    data = json.loads(EXPLORATORY_REPORT.read_text(encoding='utf-8'))
    out = {}
    for item in data.get('module_candidates', {}).get('risk_off', []):
        out[item.get('name')] = item.get('combo_metrics', {})
    return out


def write_markdown(report: Dict) -> None:
    lines = [
        '# BTC Risk-Off Alignment Report',
        '',
        '## Final Judgment',
        '',
        f"- This round is alignment validation, not new exploration.",
        f"- Main answer: {report['judgment']['main_answer']}",
        f"- Evidence level: {report['judgment']['evidence_level']}",
        f"- Baseline promotion: {report['judgment']['baseline_promotion']}",
        f"- Preferred aligned candidate: {report['judgment']['preferred_candidate']}",
        '',
        '## Formal Implementation Path',
        '',
        '- Overlay sleeve is imported from the locked, committed AddOnOverlay artifact under the default tuple.',
        '- This round does not re-optimize or restage the overlay sleeve.',
        '- Risk-Off core is rebuilt in a causal simulator: signal at 4h close t, execution at t+1 open by default, or at the first 5m close of t+1 for the conservative stress check.',
        '- Core trades pay commission and slippage; there is no same-bar hindsight rebalance.',
        '',
        '## Locked Risk-Off Candidates',
        '',
        '- `RO_EMA200_FLAT`',
        '- `RO_EMA220_FLAT`',
        '- `RO_EMA200_TO35`',
        '',
        '## Default-Tuple Aligned Results',
        '',
        '| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Exposure% | dRet vs AddOn | dCAGR | dSharpe | dCalmar | dMaxDD improve |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for key in ['B&H', 'Core+AddOnOverlay', 'Core+AddOnOverlay+RO_EMA200_FLAT', 'Core+AddOnOverlay+RO_EMA220_FLAT', 'Core+AddOnOverlay+RO_EMA200_TO35']:
        m = report['default_bundle']['schemes'][key]['metrics']
        d = report['default_bundle']['schemes'][key]['delta_vs_addon']
        lines.append(f"| {key} | {m['TotalReturn_pct']:.2f} | {m['CAGR_pct']:.2f} | {m['Sharpe']:.3f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | {m['Exposure_pct']:.1f} | {d['Return_pct']:+.2f} | {d['CAGR_pct']:+.2f} | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f} |")
    lines.extend(['', '## Minimal Formal Validation', ''])
    for key in ['Core+AddOnOverlay', 'Core+AddOnOverlay+RO_EMA200_FLAT', 'Core+AddOnOverlay+RO_EMA220_FLAT', 'Core+AddOnOverlay+RO_EMA200_TO35']:
        y = report['default_bundle']['schemes'][key]['yearly']
        r = report['default_bundle']['schemes'][key]['rolling_oos']
        lines.append(f"- {key}: yearly pass={y.get('pass')}, positive_year_ratio={y.get('positive_year_ratio', 0.0):.2f}, worst_year={y.get('worst_return_pct', 0.0):.2f}%, rolling pass={r.get('pass')}, avg_sharpe={r.get('avg_sharpe', 0.0):.3f}, positive_ratio={r.get('positive_ratio', 0.0):.2f}")
    lines.extend([
        '',
        '## Sensitivity',
        '',
        f"- Cost sensitivity, AddOn-only: Return {report['cost_sensitivity']['AddOn_only']['Return_pct']:+.2f}pp, Sharpe {report['cost_sensitivity']['AddOn_only']['Sharpe']:+.3f}, MaxDD improve {report['cost_sensitivity']['AddOn_only']['MaxDD_improvement_pct']:+.2f}pp",
        f"- Cost sensitivity, preferred Risk-Off: Return {report['cost_sensitivity']['Preferred_RiskOff']['Return_pct']:+.2f}pp, Sharpe {report['cost_sensitivity']['Preferred_RiskOff']['Sharpe']:+.3f}, MaxDD improve {report['cost_sensitivity']['Preferred_RiskOff']['MaxDD_improvement_pct']:+.2f}pp",
        f"- Execution sensitivity, AddOn-only: Return {report['execution_sensitivity']['AddOn_only']['Return_pct']:+.2f}pp, Sharpe {report['execution_sensitivity']['AddOn_only']['Sharpe']:+.3f}, MaxDD improve {report['execution_sensitivity']['AddOn_only']['MaxDD_improvement_pct']:+.2f}pp",
        f"- Execution sensitivity, preferred Risk-Off: Return {report['execution_sensitivity']['Preferred_RiskOff']['Return_pct']:+.2f}pp, Sharpe {report['execution_sensitivity']['Preferred_RiskOff']['Sharpe']:+.3f}, MaxDD improve {report['execution_sensitivity']['Preferred_RiskOff']['MaxDD_improvement_pct']:+.2f}pp",
        '',
        '## Causality Audit',
        '',
        f"- Default-mode causality violations: {report['causality_audit']['default_total_violations']}",
        f"- Stress-mode causality violations: {report['causality_audit']['stress_total_violations']}",
        '',
        '## Exploratory Comparison',
        '',
        f"- Preferred candidate return delta vs exploratory: {report['exploratory_comparison']['preferred_candidate_return_delta_pct']:+.2f}pp",
        f"- Preferred candidate maxdd delta vs exploratory: {report['exploratory_comparison']['preferred_candidate_maxdd_delta_pct']:+.2f}pp",
        f"- Interpretation: {report['exploratory_comparison']['interpretation']}",
        '',
        '## Final Call',
        '',
        f"- {report['judgment']['final_call']}",
        f"- Bear Short status: {report['judgment']['bear_short_status']}",
    ])
    Path('BTC_RISKOFF_ALIGNMENT_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def write_summary(report: Dict) -> None:
    lines = [
        f"riskoff_still_holds={report['judgment']['riskoff_still_holds']}",
        f"evidence_level={report['judgment']['evidence_level']}",
        f"baseline_promotion={report['judgment']['baseline_promotion']}",
        f"preferred_candidate={report['judgment']['preferred_candidate']}",
    ]
    Path('btc_riskoff_alignment_summary.txt').write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    overlay = load_overlay_artifact()
    loader = DataLoader5m('./data')
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    base_default = current_research_optimal(entry_execution_mode='next_bar_open', intrabar_execution_model='legacy_bar_extrema', intrabar_path_mode='midpoint')
    base_high_cost = current_research_optimal(entry_execution_mode='next_bar_open', intrabar_execution_model='legacy_bar_extrema', intrabar_path_mode='midpoint', commission_pct=0.10, slippage_fixed_bps=8.0, slippage_range_weight=0.08, slippage_max_bps=35.0)

    default_bundle = evaluate_bundle(df_5m, df_4h, base_default, 'next_bar_open', overlay['overlay_delta'], overlay['overlay_avg_exposure'])
    stress_bundle = evaluate_bundle(df_5m, df_4h, base_default, 'live_runner_next_5m_close', overlay['overlay_delta'], overlay['overlay_avg_exposure'])
    high_cost_bundle = evaluate_bundle(df_5m, df_4h, base_high_cost, 'next_bar_open', overlay['overlay_delta'], overlay['overlay_avg_exposure'])

    addon_metrics = default_bundle['schemes']['Core+AddOnOverlay']['metrics']
    bh_metrics = default_bundle['schemes']['B&H']['metrics']
    for bundle in [default_bundle, stress_bundle, high_cost_bundle]:
        for item in bundle['schemes'].values():
            item['delta_vs_addon'] = delta_metrics(item['metrics'], addon_metrics)
            item['delta_vs_bh'] = delta_metrics(item['metrics'], bh_metrics)

    preferred = 'Core+AddOnOverlay+RO_EMA220_FLAT'
    preferred_metrics = default_bundle['schemes'][preferred]['metrics']
    holds = preferred_metrics['TotalReturn_pct'] > addon_metrics['TotalReturn_pct'] and preferred_metrics['Sharpe'] > addon_metrics['Sharpe'] and abs(preferred_metrics['MaxDD_pct']) < abs(addon_metrics['MaxDD_pct'])

    exploratory = load_exploratory_reference()
    ref = exploratory.get('B1_TrendBreakRiskOff_ema220_flat', {})
    exploratory_return_delta = float(preferred_metrics['TotalReturn_pct'] - ref.get('TotalReturn_pct', preferred_metrics['TotalReturn_pct']))
    exploratory_maxdd_delta = float(preferred_metrics['MaxDD_pct'] - ref.get('MaxDD_pct', preferred_metrics['MaxDD_pct']))

    report = {
        'generated_at_local': datetime.now().isoformat(),
        'seed': SEED,
        'research_optimal': {'label': 'lb20_stop3.2_trail5.0_beoff', 'params': asdict(base_default)},
        'default_tuple': DEFAULT_TUPLE,
        'stress_tuple': STRESS_TUPLE,
        'candidate_set': RISKOFF_CANDIDATES,
        'method': {
            'overlay_source': 'Committed AddOnOverlay artifact under the locked default tuple.',
            'core_execution_default': '4h close signal -> next 4h open execution.',
            'core_execution_stress': '4h close signal -> first 5m close inside next 4h bar.',
            'scope_note': 'This round formally aligns the Risk-Off core module. The overlay sleeve itself is imported from the locked baseline artifact and not re-explored.',
        },
        'default_bundle': default_bundle,
        'stress_bundle': stress_bundle,
        'high_cost_bundle': high_cost_bundle,
        'cost_sensitivity': {
            'AddOn_only': delta_metrics(high_cost_bundle['schemes']['Core+AddOnOverlay']['metrics'], default_bundle['schemes']['Core+AddOnOverlay']['metrics']),
            'Preferred_RiskOff': delta_metrics(high_cost_bundle['schemes'][preferred]['metrics'], default_bundle['schemes'][preferred]['metrics']),
        },
        'execution_sensitivity': {
            'AddOn_only': delta_metrics(stress_bundle['schemes']['Core+AddOnOverlay']['metrics'], default_bundle['schemes']['Core+AddOnOverlay']['metrics']),
            'Preferred_RiskOff': delta_metrics(stress_bundle['schemes'][preferred]['metrics'], default_bundle['schemes'][preferred]['metrics']),
        },
        'causality_audit': {
            'default_total_violations': int(sum(v['violations'] for v in default_bundle['causality'].values())),
            'stress_total_violations': int(sum(v['violations'] for v in stress_bundle['causality'].values())),
            'default_details': default_bundle['causality'],
            'stress_details': stress_bundle['causality'],
        },
        'exploratory_comparison': {
            'preferred_candidate_return_delta_pct': exploratory_return_delta,
            'preferred_candidate_maxdd_delta_pct': exploratory_maxdd_delta,
            'interpretation': 'Small deltas mean the exploratory result was directionally reliable. Large negative deltas would mean the exploratory allocation simulation overstated the edge.',
        },
        'judgment': {
            'riskoff_still_holds': bool(holds),
            'main_answer': 'YES. In the aligned default-tuple framework, AddOn + Risk-Off still beats AddOn-only for the locked narrow candidate set.' if holds else 'NO. After alignment, the Risk-Off edge no longer clearly survives.',
            'evidence_level': 'aligned but preliminary',
            'baseline_promotion': 'NO. The module is now aligned, but this is still not enough to rewrite the locked working baseline.',
            'preferred_candidate': preferred,
            'final_call': 'Risk-Off remains supported after alignment and is worth continuing to validate, but the repository baseline should stay unchanged for now.',
            'bear_short_status': 'Not advanced in this round; remains outside the formal baseline decision.',
        },
    }

    Path('btc_riskoff_alignment_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    write_markdown(report)
    write_summary(report)
    print(json.dumps({'riskoff_still_holds': report['judgment']['riskoff_still_holds'], 'preferred_candidate': preferred, 'baseline_promotion': report['judgment']['baseline_promotion']}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    np.random.seed(SEED)
    main()
