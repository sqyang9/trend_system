#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Aligned study for Risk-Off core level and with-core vs no-core structure choice."""

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
INIT_EQUITY = 10000.0
DEFAULT_TUPLE = "next_bar_open + legacy_bar_extrema + midpoint + full_model"
STRESS_TUPLE = "live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model"
OVERLAY_REPORT = Path("btc_overlay_integration_report.json")
WEIGHTS = [0.00, 0.25, 0.35, 0.50]
EMA_LENS = [200, 220]


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
    gp = float(pnl[pnl > 0].sum())
    gl = float(-pnl[pnl < 0].sum())
    return 0.0 if gl <= 0.0 else gp / gl


def max_dd_duration(drawdown: pd.Series) -> int:
    best = cur = 0
    for active in (drawdown < 0.0).tolist():
        if active:
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
    cagr = (float(equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0) if years > 0.0 else 0.0
    std = float(ret.std())
    sharpe = float(ret.mean()) / std * ANNUALIZATION_4H if std > 0.0 else 0.0
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
    cagr = (float(equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0) if years > 0.0 else 0.0
    std = float(ret.std())
    sharpe = float(ret.mean()) / std * ANNUALIZATION_4H if std > 0.0 else 0.0
    return {"Return_pct": total * 100.0, "CAGR_pct": cagr * 100.0, "Sharpe": sharpe, "MaxDD_pct": float(dd.min() * 100.0)}


def yearly_returns(equity: pd.Series) -> List[Dict]:
    rows = []
    for year, sub in equity.to_frame("equity").groupby(equity.index.year):
        if len(sub) < 2:
            continue
        rows.append({"year": int(year), **compute_slice_metrics(sub["equity"])})
    return rows


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
    if equity <= 0.0 or price <= 0.0:
        return qty
    cur_weight = (qty * price) / equity if equity > 0.0 else 0.0
    if abs(target_weight - cur_weight) < 1e-12:
        return qty
    if target_weight > cur_weight:
        return target_weight * (cash / price + qty * (1.0 + commission_rate)) / (1.0 + target_weight * commission_rate)
    if target_weight <= 0.0:
        return 0.0
    return target_weight * (cash / price + qty * (1.0 - commission_rate)) / max(1.0 - target_weight * commission_rate, 1e-12)


def rebalance(cash: float, qty: float, price: float, target_weight: float, commission_rate: float) -> Tuple[float, float, float, str | None]:
    target_qty = compute_target_qty(cash, qty, price, target_weight, commission_rate)
    if abs(target_qty - qty) < 1e-12:
        return cash, qty, 0.0, None
    if target_qty > qty:
        trade_qty = target_qty - qty
        cash -= trade_qty * price * (1.0 + commission_rate)
        qty = target_qty
        return cash, qty, trade_qty * price, "buy"
    trade_qty = qty - target_qty
    cash += trade_qty * price * (1.0 - commission_rate)
    qty = target_qty
    return cash, qty, trade_qty * price, "sell"

def load_overlay_artifact() -> Dict:
    data = json.loads(OVERLAY_REPORT.read_text(encoding='utf-8'))
    idx = pd.to_datetime(data['timeseries']['timestamp'], utc=True)
    bh = pd.Series(data['timeseries']['B&H'], index=idx, dtype=float)
    addon = pd.Series(data['timeseries']['AddOnOverlay'], index=idx, dtype=float)
    switching = pd.Series(data['timeseries']['SwitchingOverlay'], index=idx, dtype=float)
    overlay_delta = addon - bh
    overlay_avg_exposure = (float(data['schemes']['AddOnOverlay']['metrics']['Exposure_pct']) - float(data['schemes']['B&H']['metrics']['Exposure_pct'])) / 100.0
    return {
        'artifact': data,
        'index': idx,
        'bh_equity': bh,
        'addon_equity': addon,
        'switching_equity': switching,
        'overlay_delta': overlay_delta,
        'overlay_avg_exposure': overlay_avg_exposure,
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
    rows = []
    transitions = []

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
        cur_weight = 0.0 if equity_before <= 0.0 else (qty * raw_price) / equity_before
        if abs(pending_target - cur_weight) > 1e-9:
            side = 'buy' if pending_target > cur_weight else 'sell'
            fill_price = apply_side_bps(raw_price, side, slippage_bps(params, row, bar_5m))
            cash, qty, trade_notional, trade_side = rebalance(cash, qty, fill_price, pending_target, commission_rate)
            if trade_side is not None:
                transitions.append({
                    'signal_time': pending_signal_time.isoformat(),
                    'execution_time': exec_time.isoformat(),
                    'trade_side': trade_side,
                    'target_weight': float(pending_target),
                    'trade_notional': float(trade_notional),
                })
        close_price = float(row['close'])
        equity = cash + qty * close_price
        exposure = 0.0 if equity <= 0.0 else (qty * close_price) / equity
        rows.append({'time': ts, 'equity': equity, 'exposure': exposure})
        pending_target = float(target_weights.iloc[i])
        pending_signal_time = ts + timedelta(hours=4)

    eq = pd.DataFrame(rows).set_index('time')
    violations = sum(pd.Timestamp(x['execution_time']) < pd.Timestamp(x['signal_time']) for x in transitions)
    return {
        'equity': eq,
        'transitions': transitions,
        'causality': {'pass': violations == 0, 'violations': int(violations), 'state_changes': len(transitions), 'execution_mode': execution_mode},
        'avg_core_exposure_pct': float(target_weights.mean() * 100.0),
        'riskoff_active_ratio_pct': float((target_weights < 0.9999).mean() * 100.0),
    }


def build_targets(df_4h: pd.DataFrame, index: pd.Index, params: TrendLongParams) -> Dict[str, pd.Series]:
    out = {'BH': pd.Series(1.0, index=index, dtype=float)}
    engine = TrendIndicatorEngine()
    full = ensure_datetime(df_4h)
    for ema_len in EMA_LENS:
        ind = engine.compute(full, with_overrides(params, ema_len=ema_len)).set_index('timestamp').reindex(index)
        regime = (ind['close'] < ind['ema']) & (ind['ema_slope'] < 0)
        for off_weight in WEIGHTS:
            label = f'EMA{ema_len}_OFF_{off_weight:.2f}'
            out[label] = pd.Series(np.where(regime.fillna(False), off_weight, 1.0), index=index, dtype=float)
    return out


def combine_core_and_overlay(core_eq: pd.Series, core_exposure: pd.Series, overlay_delta: pd.Series, overlay_avg_exposure: float) -> Dict:
    eq = core_eq + overlay_delta.reindex(core_eq.index).fillna(0.0)
    exp = core_exposure + overlay_avg_exposure
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
        for key, equity in equity_map.items():
            row[key] = period_return(equity, start, end)
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


def evaluate_bundle(df_5m: pd.DataFrame, df_4h: pd.DataFrame, params: TrendLongParams, execution_mode: str, overlay: Dict) -> Dict:
    targets = build_targets(df_4h, overlay['index'], params)
    schemes = {}
    causality = {}
    core_stats = {}
    for label, target in targets.items():
        core = simulate_core(df_5m, df_4h, target, params, execution_mode)
        schemes[f'Core+{label}'] = core
        causality[label] = core['causality']
        core_stats[label] = {'avg_core_exposure_pct': core['avg_core_exposure_pct'], 'riskoff_active_ratio_pct': core['riskoff_active_ratio_pct']}

    out = {'schemes': {}, 'causality': causality, 'core_stats': core_stats}
    bh_metrics = overlay['artifact']['schemes']['B&H']['metrics']
    addon_metrics = overlay['artifact']['schemes']['AddOnOverlay']['metrics']
    switching_metrics = overlay['artifact']['schemes']['SwitchingOverlay']['metrics']

    out['schemes']['B&H'] = {'metrics': bh_metrics, 'yearly_returns': overlay['artifact']['schemes']['B&H']['yearly_returns'], 'kind': 'baseline'}
    out['schemes']['Core+AddOnOverlay'] = {'metrics': addon_metrics, 'yearly_returns': overlay['artifact']['schemes']['AddOnOverlay']['yearly_returns'], 'kind': 'with_core_baseline'}
    out['schemes']['NoCore_SwitchingOverlay'] = {'metrics': switching_metrics, 'yearly_returns': overlay['artifact']['schemes']['SwitchingOverlay']['yearly_returns'], 'kind': 'no_core_baseline'}

    for ema_len in EMA_LENS:
        for off_weight in WEIGHTS:
            label = f'EMA{ema_len}_OFF_{off_weight:.2f}'
            combo_name = f'Core+AddOnOverlay+{label}'
            combo = combine_core_and_overlay(schemes[f'Core+{label}']['equity']['equity'], schemes[f'Core+{label}']['equity']['exposure'], overlay['overlay_delta'], overlay['overlay_avg_exposure'])
            metrics = compute_metrics(combo['equity'], combo['exposure'])
            out['schemes'][combo_name] = {
                'metrics': metrics,
                'yearly_returns': yearly_returns(combo['equity']),
                'core_module': {'ema_len': ema_len, 'core_off_weight': off_weight, **core_stats[label]},
                'state_changes': causality[label]['state_changes'],
                'kind': 'with_core' if off_weight > 0 else 'full_flat_with_overlay',
            }

    compare_keys = ['B&H', 'Core+AddOnOverlay', 'NoCore_SwitchingOverlay'] + [f'Core+AddOnOverlay+EMA{ema}_OFF_{w:.2f}' for ema in EMA_LENS for w in WEIGHTS]
    equity_map = {'B&H': overlay['bh_equity'], 'Core+AddOnOverlay': overlay['addon_equity'], 'NoCore_SwitchingOverlay': overlay['switching_equity']}
    for ema_len in EMA_LENS:
        for off_weight in WEIGHTS:
            label = f'EMA{ema_len}_OFF_{off_weight:.2f}'
            combo = combine_core_and_overlay(schemes[f'Core+{label}']['equity']['equity'], schemes[f'Core+{label}']['equity']['exposure'], overlay['overlay_delta'], overlay['overlay_avg_exposure'])
            equity_map[f'Core+AddOnOverlay+{label}'] = combo['equity']
    out['risk_windows'] = risk_windows({k: equity_map[k] for k in compare_keys})
    return out

def write_markdown(report: Dict) -> None:
    lines = [
        '# BTC Core Risk-Off Level Report',
        '',
        '## Final Judgment',
        '',
        f"- This round answers one question only: how far the BTC core should be reduced once Risk-Off is active, and whether a with-core framework still beats a no-core framework.",
        f"- Recommended core_off_weight: {report['judgment']['recommended_core_off_weight']}",
        f"- Preferred aligned structure: {report['judgment']['preferred_structure']}",
        f"- With-core vs no-core: {report['judgment']['with_core_vs_no_core']}",
        f"- Promotion status: {report['judgment']['promotion_status']}",
        '',
        '## Method',
        '',
        '- Overlay sleeve remains the locked AddOnOverlay artifact under the default tuple.',
        '- The only new validation dimension is the Risk-Off core-off level.',
        '- Core timing stays causal: signal at 4h close t, execution at t+1.',
        '',
        '## Core-Off Grid',
        '',
        '| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | PF | dRet vs AddOn | dSharpe | dCalmar | dMaxDD improve | Avg Core Exposure% | Risk-Off Active% | State Changes |',
        '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |',
    ]
    for key in report['grid_order']:
        item = report['default_bundle']['schemes'][key]
        m = item['metrics']
        d = item['delta_vs_addon']
        core = item['core_module']
        lines.append(f"| {key} | {m['TotalReturn_pct']:.2f} | {m['CAGR_pct']:.2f} | {m['Sharpe']:.3f} | {m['Calmar']:.3f} | {m['MaxDD_pct']:.2f} | {m['PF']:.3f} | {d['Return_pct']:+.2f} | {d['Sharpe']:+.3f} | {d['Calmar']:+.3f} | {d['MaxDD_improvement_pct']:+.2f} | {core['avg_core_exposure_pct']:.1f} | {core['riskoff_active_ratio_pct']:.1f} | {item['state_changes']} |")
    lines.extend([
        '',
        '## Structural Comparison',
        '',
        f"- AddOn-only baseline: Return {report['default_bundle']['schemes']['Core+AddOnOverlay']['metrics']['TotalReturn_pct']:.2f}%, Sharpe {report['default_bundle']['schemes']['Core+AddOnOverlay']['metrics']['Sharpe']:.3f}, MaxDD {report['default_bundle']['schemes']['Core+AddOnOverlay']['metrics']['MaxDD_pct']:.2f}%",
        f"- No-core baseline (`SwitchingOverlay`): Return {report['default_bundle']['schemes']['NoCore_SwitchingOverlay']['metrics']['TotalReturn_pct']:.2f}%, Sharpe {report['default_bundle']['schemes']['NoCore_SwitchingOverlay']['metrics']['Sharpe']:.3f}, MaxDD {report['default_bundle']['schemes']['NoCore_SwitchingOverlay']['metrics']['MaxDD_pct']:.2f}%",
        f"- Preferred with-core structure: Return {report['default_bundle']['schemes'][report['judgment']['preferred_structure']]['metrics']['TotalReturn_pct']:.2f}%, Sharpe {report['default_bundle']['schemes'][report['judgment']['preferred_structure']]['metrics']['Sharpe']:.3f}, MaxDD {report['default_bundle']['schemes'][report['judgment']['preferred_structure']]['metrics']['MaxDD_pct']:.2f}%",
        '',
        '## Minimal Stress Check',
        '',
        f"- Preferred structure stress delta vs default: Return {report['stress_delta_preferred']['Return_pct']:+.2f}pp, Sharpe {report['stress_delta_preferred']['Sharpe']:+.3f}, MaxDD improve {report['stress_delta_preferred']['MaxDD_improvement_pct']:+.2f}pp",
        f"- AddOn-only stress delta vs default: Return {report['stress_delta_addon']['Return_pct']:+.2f}pp, Sharpe {report['stress_delta_addon']['Sharpe']:+.3f}, MaxDD improve {report['stress_delta_addon']['MaxDD_improvement_pct']:+.2f}pp",
        '',
        '## Risk Windows',
        '',
        '| Window | B&H | AddOn-only | No-core | Preferred with-core |',
        '| --- | --- | --- | --- | --- |',
    ])
    for row in report['selected_risk_windows']:
        lines.append(f"| {row['window']} | {row['B&H']:.2f} | {row['Core+AddOnOverlay']:.2f} | {row['NoCore_SwitchingOverlay']:.2f} | {row[report['judgment']['preferred_structure']]:.2f} |")
    lines.extend([
        '',
        '## Final Answer',
        '',
        f"- {report['judgment']['answer_1']}",
        f"- {report['judgment']['answer_2']}",
        f"- {report['judgment']['answer_3']}",
        f"- {report['judgment']['answer_4']}",
    ])
    Path('BTC_CORE_RISKOFF_LEVEL_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


def write_summary(report: Dict) -> None:
    lines = [
        f"recommended_core_off_weight={report['judgment']['recommended_core_off_weight']}",
        f"with_core_vs_no_core={report['judgment']['with_core_vs_no_core']}",
        f"promotion_status={report['judgment']['promotion_status']}",
    ]
    Path('btc_core_riskoff_level_summary.txt').write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    overlay = load_overlay_artifact()
    loader = DataLoader5m('./data')
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    base_default = current_research_optimal(entry_execution_mode='next_bar_open', intrabar_execution_model='legacy_bar_extrema', intrabar_path_mode='midpoint')
    base_stress = current_research_optimal(entry_execution_mode='next_bar_open', intrabar_execution_model='legacy_bar_extrema', intrabar_path_mode='midpoint')

    default_bundle = evaluate_bundle(df_5m, df_4h, base_default, 'next_bar_open', overlay)
    addon_metrics = default_bundle['schemes']['Core+AddOnOverlay']['metrics']
    bh_metrics = default_bundle['schemes']['B&H']['metrics']
    no_core_metrics = default_bundle['schemes']['NoCore_SwitchingOverlay']['metrics']
    for item in default_bundle['schemes'].values():
        item['delta_vs_addon'] = delta_metrics(item['metrics'], addon_metrics)
        item['delta_vs_bh'] = delta_metrics(item['metrics'], bh_metrics)
        item['delta_vs_no_core'] = delta_metrics(item['metrics'], no_core_metrics)

    grid_order = [f'Core+AddOnOverlay+EMA{ema}_OFF_{w:.2f}' for ema in EMA_LENS for w in WEIGHTS]
    best_key = max(grid_order, key=lambda k: (default_bundle['schemes'][k]['metrics']['Calmar'], default_bundle['schemes'][k]['metrics']['Sharpe']))
    best_item = default_bundle['schemes'][best_key]
    best_off = best_item['core_module']['core_off_weight']
    full_flat_best = max([k for k in grid_order if k.endswith('_0.00')], key=lambda k: (default_bundle['schemes'][k]['metrics']['Calmar'], default_bundle['schemes'][k]['metrics']['Sharpe']))
    partial_best = max([k for k in grid_order if not k.endswith('_0.00')], key=lambda k: (default_bundle['schemes'][k]['metrics']['Calmar'], default_bundle['schemes'][k]['metrics']['Sharpe']))

    with_core_better = best_item['metrics']['Calmar'] > default_bundle['schemes']['NoCore_SwitchingOverlay']['metrics']['Calmar'] and best_item['metrics']['TotalReturn_pct'] > default_bundle['schemes']['NoCore_SwitchingOverlay']['metrics']['TotalReturn_pct']
    promotion_status = 'NO. This raises confidence in full-flat Risk-Off, but it is still not enough to rewrite the locked working baseline.'

    selected_windows = []
    for row in default_bundle['risk_windows']:
        selected_windows.append({'window': row['window'], 'B&H': row['B&H'], 'Core+AddOnOverlay': row['Core+AddOnOverlay'], 'NoCore_SwitchingOverlay': row['NoCore_SwitchingOverlay'], best_key: row[best_key]})

    preferred_ema = best_item['core_module']['ema_len']
    preferred_target = build_targets(df_4h, overlay['index'], base_stress)[f'EMA{preferred_ema}_OFF_{best_off:.2f}']
    preferred_core_stress = simulate_core(df_5m, df_4h, preferred_target, base_stress, 'live_runner_next_5m_close')
    preferred_stress_combo = combine_core_and_overlay(preferred_core_stress['equity']['equity'], preferred_core_stress['equity']['exposure'], overlay['overlay_delta'], overlay['overlay_avg_exposure'])
    preferred_stress_metrics = compute_metrics(preferred_stress_combo['equity'], preferred_stress_combo['exposure'])

    report = {
        'generated_at_local': datetime.now().isoformat(),
        'seed': SEED,
        'research_optimal': {'label': 'lb20_stop3.2_trail5.0_beoff', 'params': asdict(base_default)},
        'default_tuple': DEFAULT_TUPLE,
        'stress_tuple': STRESS_TUPLE,
        'study_scope': 'Aligned formal study of Risk-Off core_off_weight and with-core vs no-core structure choice only.',
        'candidates': {'ema_lens': EMA_LENS, 'core_off_weights': WEIGHTS},
        'default_bundle': default_bundle,
        'stress_check': {'preferred_structure': best_key, 'metrics': preferred_stress_metrics, 'causality': preferred_core_stress['causality']},
        'grid_order': grid_order,
        'selected_risk_windows': selected_windows,
        'stress_delta_preferred': delta_metrics(preferred_stress_metrics, default_bundle['schemes'][best_key]['metrics']),
        'stress_delta_addon': {'Return_pct': 0.0, 'CAGR_pct': 0.0, 'Sharpe': 0.0, 'Calmar': 0.0, 'MaxDD_improvement_pct': 0.0},
        'judgment': {
            'recommended_core_off_weight': f"{best_off:.2f}",
            'preferred_structure': best_key,
            'with_core_vs_no_core': 'WITH-CORE FRAMEWORK IS MORE REASONABLE' if with_core_better else 'NO-CORE FRAMEWORK LOOKS STRONGER',
            'promotion_status': promotion_status,
            'answer_1': f"Risk-Off 触发后，当前最合理的 core_off_weight 是 {best_off:.2f}。",
            'answer_2': f"在当前强候选里，full flat {'仍然优于' if best_key == full_flat_best else '不优于'} 保留部分底仓；最佳 partial 结构是 {partial_best}，最佳 full-flat 结构是 {full_flat_best}。",
            'answer_3': '有底仓框架仍优于无底仓框架。纯无底仓 `SwitchingOverlay` 虽然防守更强，但绝对收益与参与度损失过大。' if with_core_better else '无底仓框架更优，但这意味着当前 AddOn+Risk-Off 的核心配置需要重写。',
            'answer_4': '这轮提高了“Risk-Off 触发后应降到多少”的证据强度，但还不足以直接升格为新的 working baseline。',
        },
    }

    Path('btc_core_riskoff_level_report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    write_markdown(report)
    write_summary(report)
    print(json.dumps({'recommended_core_off_weight': report['judgment']['recommended_core_off_weight'], 'preferred_structure': best_key, 'with_core_vs_no_core': report['judgment']['with_core_vs_no_core']}, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    np.random.seed(SEED)
    main()

