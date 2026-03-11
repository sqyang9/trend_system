#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import contextlib
import io
import json
from dataclasses import asdict
from datetime import timezone
from pathlib import Path

import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_intrabar_backtest_legacy import Direction as LDir, ExitReason as LExit, IntrabarBacktestEngine as LE, PositionManager as LPM, V85Params as LP
from v85_backtest_engine_v2 import Direction as VDir, ExitReason as VExit, IntrabarBacktestEngine as VE, PositionManager as VPM, V85Params as VP

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'


def ts(text: str) -> pd.Timestamp:
    return pd.Timestamp(text, tz='UTC')


def legacy_params() -> LP:
    return LP(init_equity=10000.0, position_pct=60.0, squeeze_threshold=0.85, min_squeeze_candles=4, initial_stop_atr=2.6, trail_start_atr=3.2, trail_offset_atr=2.6, enable_partial_tp=True, tp1_atr=2.4, tp2_atr=4.0, adx_trend_level=24.0, min_long_score=1, min_short_score=3)


def v2_params() -> VP:
    return VP(init_equity=10000.0, position_pct=60.0, squeeze_threshold=0.85, min_squeeze_candles=4, initial_stop_atr=2.6, trail_start_atr=3.2, trail_offset_atr=2.6, enable_partial_tp=True, tp1_atr=2.4, tp2_atr=4.0, adx_trend_level=24.0, min_long_score=1, min_short_score=3, entry_execution_mode='signal_close', intrabar_path_mode='optimistic')


def snap_legacy(pm: LPM) -> dict:
    if pm.is_flat():
        return {'flat': True}
    p = pm.position
    return {'flat': False, 'qty': float(p.current_qty), 'stop': float(p.stop_loss_price), 'tp1_filled': bool(p.tp1_filled), 'tp2_filled': bool(p.tp2_filled), 'be': bool(p.be_activated), 'trail': bool(p.trailing_active)}


def snap_v2(pm: VPM) -> dict:
    if pm.is_flat():
        return {'flat': True}
    p = pm.position
    return {'flat': False, 'qty': float(p.current_qty), 'stop': float(p.stop_loss_price), 'tp1_filled': bool(p.tp1_filled), 'tp2_filled': bool(p.tp2_filled), 'be': bool(p.be_activated), 'trail': bool(p.trailing_active)}


def run_legacy_case(name: str, side: str, bar: dict, atr: float = 10.0) -> dict:
    pm = LPM(legacy_params())
    t0 = ts('2026-01-01 00:00:00')
    price = 1000.0
    pm.open_position(LDir.LONG if side == 'long' else LDir.SHORT, price, 1.0, atr, t0, t0)
    before = snap_legacy(pm)
    triggers = pm.check_intrabar_triggers(bar['high'], bar['low'], atr, t0 + pd.Timedelta(minutes=5))
    executed = []
    for reason, px, qty in triggers:
        pm.execute_exit(reason, px, qty, t0 + pd.Timedelta(minutes=5))
        executed.append({'reason': reason.value, 'price': float(px), 'qty': float(qty)})
    return {'scenario': name, 'engine': 'legacy', 'side': side, 'bar': bar, 'before': before, 'triggers': executed, 'after': snap_legacy(pm)}


def run_v2_case(name: str, side: str, bar: dict, path_mode: str, atr: float = 10.0) -> dict:
    pm = VPM(v2_params())
    t0 = ts('2026-01-01 00:00:00')
    price = 1000.0
    pm.open_position(VDir.LONG if side == 'long' else VDir.SHORT, price, 1.0, atr, t0, t0)
    before = snap_v2(pm)
    row = pd.Series(bar)
    triggers = pm.process_intrabar_bar(row, atr, t0 + pd.Timedelta(minutes=5), path_mode)
    executed = []
    for reason, px, qty, when in triggers:
        pm.execute_exit(reason, px, qty, when)
        executed.append({'reason': reason.value, 'price': float(px), 'qty': float(qty)})
    return {'scenario': name, 'engine': f'v2_{path_mode}', 'side': side, 'bar': bar, 'before': before, 'triggers': executed, 'after': snap_v2(pm)}


def synthetic_audit() -> list[dict]:
    cases = [
        ('long_be_same_bar_pullback', 'long', {'open': 1000.0, 'high': 1020.0, 'low': 999.0, 'close': 1005.0, 'volume': 1.0}),
        ('long_tp_trail_same_bar_pullback', 'long', {'open': 1000.0, 'high': 1040.0, 'low': 1008.0, 'close': 1010.0, 'volume': 1.0}),
        ('short_be_same_bar_rebound', 'short', {'open': 1000.0, 'high': 1002.0, 'low': 982.0, 'close': 995.0, 'volume': 1.0}),
        ('short_tp_trail_same_bar_rebound', 'short', {'open': 1000.0, 'high': 992.0, 'low': 960.0, 'close': 990.0, 'volume': 1.0}),
    ]
    out = []
    for name, side, bar in cases:
        out.append(run_legacy_case(name, side, bar))
        for mode in ['optimistic', 'midpoint', 'volatility_aware', 'pessimistic']:
            out.append(run_v2_case(name, side, bar, mode))
    return out


def run_backtest(engine, df5, df4):
    with contextlib.redirect_stdout(io.StringIO()):
        return engine.run(df5, df4)


def real_bridge_audit() -> dict:
    loader = DataLoader5m(str(DATA_DIR))
    df5, df4 = loader.load_data()
    legacy = run_backtest(LE(legacy_params(), use_intrabar_stop=True), df5, df4)
    bridge = run_backtest(VE(v2_params(), use_intrabar_stop=True), df5, df4)

    def summarize(result: dict, name: str) -> dict:
        trades = result['trades'].copy()
        trades['entry_time'] = pd.to_datetime(trades['entry_time'], utc=True)
        trades['exit_time'] = pd.to_datetime(trades['exit_time'], utc=True)
        hold_min = (trades['exit_time'] - trades['entry_time']).dt.total_seconds() / 60.0
        return {
            'name': name,
            'stats': result['stats'],
            'exit_reason_counts': trades['exit_reason'].value_counts().to_dict(),
            'median_hold_min': float(hold_min.median()) if len(hold_min) else 0.0,
            'mean_hold_min': float(hold_min.mean()) if len(hold_min) else 0.0,
            'same_timestamp_exits': int((hold_min <= 0.0).sum()),
            'within_5m_exits': int((hold_min <= 5.0).sum()),
            'within_60m_exits': int((hold_min <= 60.0).sum()),
        }
    return {'legacy_reference': summarize(legacy, 'legacy_reference'), 'v2_bridge': summarize(bridge, 'v2_bridge')}


def write_report(synth: list[dict], real: dict) -> None:
    outdir = DATA_DIR / 'intrabar_semantic_audit'
    outdir.mkdir(parents=True, exist_ok=True)
    report = {'synthetic': synth, 'real_bridge_audit': real}
    (outdir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    ROOT.joinpath('intrabar_semantic_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# Intrabar Semantic Audit',
        '',
        '- 结论: `legacy -> v2` 的主断层来自同一根 5m 内对 `BE / trail / TP / stop` 的处理语义变化。',
        '- 核心区别: legacy 会在 bar 内先看旧 stop，再根据整根 bar 的极值更新 BE/trail，但不会在同一根 bar 再次检验新 stop。',
        '- v2 会按 path 分段推进，因此可能在同一根 5m 内先激活 BE/trail，再被同 bar 回撤打掉。',
        '- 这类“同 bar 激活、同 bar 退出”在趋势系统里会显著压缩盈亏比与持仓持续性。',
        '- 所以当前最该做的不是继续调参，而是校准同 bar 保护语义。',
        '',
        '## Real Backtest Audit',
        '',
        f"- legacy reference: Return {real['legacy_reference']['stats']['TotalReturn_pct']:.2f}% | Trades {real['legacy_reference']['stats']['Trades']} | median hold {real['legacy_reference']['median_hold_min']:.1f} min | exits<=5m {real['legacy_reference']['within_5m_exits']}",
        f"- v2 bridge: Return {real['v2_bridge']['stats']['TotalReturn_pct']:.2f}% | Trades {real['v2_bridge']['stats']['Trades']} | median hold {real['v2_bridge']['median_hold_min']:.1f} min | exits<=5m {real['v2_bridge']['within_5m_exits']}",
        f"- v2 bridge exit reasons: {real['v2_bridge']['exit_reason_counts']}",
        '',
        '## Synthetic Cases',
        '',
    ]
    for name in sorted({x['scenario'] for x in synth}):
        lines.append(f'### {name}')
        subset = [x for x in synth if x['scenario'] == name]
        for row in subset:
            lines.append(f"- {row['engine']}: triggers={row['triggers']} | before={row['before']} | after={row['after']}")
        lines.append('')
    ROOT.joinpath('INTRABAR_SEMANTIC_AUDIT.md').write_text('\n'.join(lines), encoding='utf-8')


def main() -> None:
    synth = synthetic_audit()
    real = real_bridge_audit()
    write_report(synth, real)
    print(json.dumps({'md': str(ROOT / 'INTRABAR_SEMANTIC_AUDIT.md'), 'json': str(ROOT / 'intrabar_semantic_audit.json')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
