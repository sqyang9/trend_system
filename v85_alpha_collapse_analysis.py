#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import math
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from universal_data_updater_5m import DataLoader5m
from v85_backtest_engine_v2 import IntrabarBacktestEngine as V2Engine, V85Params as V2Params
from v85_intrabar_backtest_legacy import IntrabarBacktestEngine as LegacyEngine, V85Params as LegacyParams

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / 'data'
CACHE_PATH = DATA_DIR / 'alpha_collapse_cache.json'
SEED = 42
INIT_EQUITY = 10000.0


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')


def load_cache() -> dict:
    return json.loads(CACHE_PATH.read_text(encoding='utf-8')) if CACHE_PATH.exists() else {}


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')


def key_for(engine: str, params: dict) -> str:
    payload = json.dumps({'engine': engine, 'params': params}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(payload.encode('utf-8')).hexdigest()


def pct(x) -> float:
    return float(0.0 if x is None or pd.isna(x) else x)


def summarize(label: str, engine: str, cfg: dict, result: dict, runtime_s: float) -> dict:
    s = result['stats']
    trades = result.get('trades')
    if trades is None or trades.empty:
        shape = {'unique_entries': 0, 'long_entries': 0, 'short_entries': 0, 'avg_legs_per_entry': 0.0}
    else:
        t = trades.copy()
        t['entry_time'] = pd.to_datetime(t['entry_time'], utc=True)
        g = t.groupby(['entry_time', 'direction', 'entry_price'], dropna=False)['pnl'].sum().reset_index()
        shape = {
            'unique_entries': int(len(g)),
            'long_entries': int((g['direction'] == 'long').sum()),
            'short_entries': int((g['direction'] == 'short').sum()),
            'avg_legs_per_entry': float(len(t) / len(g)) if len(g) else 0.0,
        }
    m = {
        'FinalEquity': pct(s.get('FinalEquity', 0.0)),
        'Return_pct': pct(s.get('TotalReturn_pct', 0.0)),
        'CAGR_pct': pct(s.get('CAGR', 0.0)) * 100.0,
        'Sharpe': pct(s.get('Sharpe', 0.0)),
        'MaxDD_pct': pct(s.get('MaxDD_pct', 0.0)) * 100.0,
        'PF': pct(s.get('ProfitFactor', 0.0)),
        'Trades': int(s.get('Trades', 0)),
        'WinRate_pct': pct(s.get('WinRate_pct', 0.0)),
        'log_equity_return': math.log(max(pct(s.get('FinalEquity', 0.0)), 1e-12) / INIT_EQUITY),
    }
    return {
        'label': label,
        'engine': engine,
        'runtime_seconds': runtime_s,
        'config': cfg,
        'metrics': m,
        'trade_shape': shape,
        'exit_reasons': s.get('ExitReasons', {}),
    }


def run_legacy(df5: pd.DataFrame, df4: pd.DataFrame, p: LegacyParams) -> dict:
    e = LegacyEngine(p, use_intrabar_stop=True)
    with contextlib.redirect_stdout(io.StringIO()):
        return e.run(df5, df4)


def run_v2(df5: pd.DataFrame, df4: pd.DataFrame, p: V2Params) -> dict:
    e = V2Engine(p, use_intrabar_stop=True)
    with contextlib.redirect_stdout(io.StringIO()):
        return e.run(df5, df4)


class Runner:
    def __init__(self, df5: pd.DataFrame, df4: pd.DataFrame):
        self.df5 = df5
        self.df4 = df4
        self.cache = load_cache()

    def _run(self, engine: str, label: str, params, fn):
        cfg = asdict(params)
        k = key_for(engine, cfg)
        if k in self.cache:
            row = self.cache[k]
            row['label'] = label
            return row
        t0 = time.perf_counter()
        result = fn(self.df5, self.df4, params)
        row = summarize(label, engine, cfg, result, time.perf_counter() - t0)
        self.cache[k] = row
        save_cache(self.cache)
        return row

    def legacy(self, label: str, params: LegacyParams) -> dict:
        return self._run('legacy', label, params, run_legacy)

    def v2(self, label: str, params: V2Params) -> dict:
        return self._run('v2', label, params, run_v2)


def legacy_params() -> LegacyParams:
    return LegacyParams(init_equity=INIT_EQUITY, position_pct=60.0, squeeze_threshold=0.85, min_squeeze_candles=4, initial_stop_atr=2.6, trail_start_atr=3.2, trail_offset_atr=2.6, enable_partial_tp=True, tp1_atr=2.4, tp2_atr=4.0, adx_trend_level=24.0, min_long_score=1, min_short_score=3)


def v2_base(position_pct=60.0, enable_partial_tp=True) -> V2Params:
    return V2Params(init_equity=INIT_EQUITY, position_pct=position_pct, squeeze_threshold=0.85, min_squeeze_candles=4, initial_stop_atr=2.6, trail_start_atr=3.2, trail_offset_atr=2.6, enable_partial_tp=enable_partial_tp, tp1_atr=2.4, tp2_atr=4.0, adx_trend_level=24.0, min_long_score=1, min_short_score=3)


def v2_with(base: V2Params, **ov) -> V2Params:
    d = asdict(base)
    d.update(ov)
    return V2Params(**d)


def slip_none():
    return {'slippage_fixed_bps': 0.0, 'slippage_breakout_extra_bps': 0.0, 'slippage_stop_extra_bps': 0.0, 'slippage_range_weight': 0.0, 'slippage_max_bps': 0.0}


def slip_fixed():
    return {'slippage_fixed_bps': 5.0, 'slippage_breakout_extra_bps': 0.0, 'slippage_stop_extra_bps': 0.0, 'slippage_range_weight': 0.0, 'slippage_max_bps': 5.0}


def slip_full():
    return {'slippage_fixed_bps': 5.0, 'slippage_breakout_extra_bps': 5.0, 'slippage_stop_extra_bps': 8.0, 'slippage_range_weight': 0.05, 'slippage_max_bps': 25.0}

def add_deltas(rows: list[dict]) -> list[dict]:
    out = []
    prev = None
    for row in rows:
        cur = row.copy()
        if prev is None:
            cur['delta'] = {'delta_Return_pct': 0.0, 'delta_CAGR_pct': 0.0, 'delta_Sharpe': 0.0, 'delta_MaxDD_pct': 0.0, 'delta_PF': 0.0, 'delta_Trades': 0, 'delta_unique_entries': 0, 'delta_avg_legs_per_entry': 0.0, 'delta_log_equity_return': 0.0}
        else:
            cm, pm = cur['metrics'], prev['metrics']
            ct, pt = cur['trade_shape'], prev['trade_shape']
            cur['delta'] = {
                'delta_Return_pct': cm['Return_pct'] - pm['Return_pct'],
                'delta_CAGR_pct': cm['CAGR_pct'] - pm['CAGR_pct'],
                'delta_Sharpe': cm['Sharpe'] - pm['Sharpe'],
                'delta_MaxDD_pct': cm['MaxDD_pct'] - pm['MaxDD_pct'],
                'delta_PF': cm['PF'] - pm['PF'],
                'delta_Trades': cm['Trades'] - pm['Trades'],
                'delta_unique_entries': ct['unique_entries'] - pt['unique_entries'],
                'delta_avg_legs_per_entry': ct['avg_legs_per_entry'] - pt['avg_legs_per_entry'],
                'delta_log_equity_return': cm['log_equity_return'] - pm['log_equity_return'],
            }
        out.append(cur)
        prev = cur
    return out


def build_waterfall(r: Runner) -> list[dict]:
    rows = [
        r.legacy('Layer 0 | legacy old-style reference', legacy_params()),
        r.v2('Bridge | v2 legacy-proxy (signal_close + optimistic + no_slippage)', v2_with(v2_base(60.0, True), entry_execution_mode='signal_close', intrabar_path_mode='optimistic', close_delay_bps=0.0, **slip_none())),
        r.v2('Layer 1 | + next_bar_open', v2_with(v2_base(60.0, True), entry_execution_mode='next_bar_open', intrabar_path_mode='optimistic', close_delay_bps=0.0, **slip_none())),
        r.v2('Layer 2 | + live_runner_next_5m_close', v2_with(v2_base(60.0, True), entry_execution_mode='live_runner_next_5m_close', intrabar_path_mode='optimistic', close_delay_bps=0.0, **slip_none())),
        r.v2('Layer 3 | + base fixed slippage', v2_with(v2_base(60.0, True), entry_execution_mode='live_runner_next_5m_close', intrabar_path_mode='optimistic', **slip_fixed())),
        r.v2('Layer 4 | + full slippage model', v2_with(v2_base(60.0, True), entry_execution_mode='live_runner_next_5m_close', intrabar_path_mode='optimistic', **slip_full())),
        r.v2('Layer 5 | + intrabar pessimistic', v2_with(v2_base(60.0, True), entry_execution_mode='live_runner_next_5m_close', intrabar_path_mode='pessimistic', **slip_full())),
        r.v2('Layer 6 | + disable_partial_tp', v2_with(v2_base(60.0, False), entry_execution_mode='live_runner_next_5m_close', intrabar_path_mode='pessimistic', **slip_full())),
        r.v2('Layer 7 | + launch assumptions (position_pct=25)', v2_with(v2_base(25.0, False), entry_execution_mode='live_runner_next_5m_close', intrabar_path_mode='pessimistic', **slip_full())),
    ]
    return add_deltas(rows)


def contributions(waterfall: list[dict]) -> dict:
    m = {row['label']: row for row in waterfall}
    total = m['Layer 0 | legacy old-style reference']['metrics']['log_equity_return'] - m['Layer 7 | + launch assumptions (position_pct=25)']['metrics']['log_equity_return']
    total = total if abs(total) > 1e-12 else 1e-12
    rows = [
        ('H. engine_semantic_migration', 'Legacy engine -> V2 bridge intrabar sequencing shift.', m['Bridge | v2 legacy-proxy (signal_close + optimistic + no_slippage)']['delta']['delta_log_equity_return'], m['Bridge | v2 legacy-proxy (signal_close + optimistic + no_slippage)']['delta']['delta_Return_pct']),
        ('A. entry_execution_realism', 'Bridge -> next_bar_open -> live_runner_next_5m_close.', m['Layer 1 | + next_bar_open']['delta']['delta_log_equity_return'] + m['Layer 2 | + live_runner_next_5m_close']['delta']['delta_log_equity_return'], m['Layer 1 | + next_bar_open']['delta']['delta_Return_pct'] + m['Layer 2 | + live_runner_next_5m_close']['delta']['delta_Return_pct']),
        ('B. base_slippage', 'Fixed 5 bps slippage only.', m['Layer 3 | + base fixed slippage']['delta']['delta_log_equity_return'], m['Layer 3 | + base fixed slippage']['delta']['delta_Return_pct']),
        ('C. breakout_stop_range_penalties', 'Full slippage: breakout extra, stop extra, range proxy.', m['Layer 4 | + full slippage model']['delta']['delta_log_equity_return'], m['Layer 4 | + full slippage model']['delta']['delta_Return_pct']),
        ('D. intrabar_pessimistic_path', 'Optimistic -> pessimistic under full slippage.', m['Layer 5 | + intrabar pessimistic']['delta']['delta_log_equity_return'], m['Layer 5 | + intrabar pessimistic']['delta']['delta_Return_pct']),
        ('E. partial_tp_removal', 'Disable partial TP under identical execution.', m['Layer 6 | + disable_partial_tp']['delta']['delta_log_equity_return'], m['Layer 6 | + disable_partial_tp']['delta']['delta_Return_pct']),
        ('F. other_launch_constraints', 'No additional launch-only constraint beyond sizing in current branch.', 0.0, 0.0),
        ('G. position_sizing_effect', 'Position_pct 60 -> 25 under same launch execution.', m['Layer 7 | + launch assumptions (position_pct=25)']['delta']['delta_log_equity_return'], m['Layer 7 | + launch assumptions (position_pct=25)']['delta']['delta_Return_pct']),
    ]
    out = []
    for factor, desc, dlog, dret in rows:
        out.append({'factor': factor, 'description': desc, 'delta_log_equity_return': dlog, 'delta_Return_pct': dret, 'drop_share_of_total_log_change': (-dlog) / total})
    df = pd.DataFrame(out)
    drag = df[df['delta_log_equity_return'] < 0].copy()
    drag['abs_drop'] = drag['delta_log_equity_return'].abs()
    top3 = drag.sort_values('abs_drop', ascending=False).head(3)[['factor', 'description', 'delta_Return_pct', 'drop_share_of_total_log_change']].to_dict(orient='records')
    return {'rows': out, 'top3_drags': top3, 'most_overconservative_candidates': ['H. engine_semantic_migration', 'D. intrabar_pessimistic_path', 'C. breakout_stop_range_penalties']}


def realism_tags() -> list[dict]:
    return [
        {'factor': 'H. engine_semantic_migration', 'label': '待重构', 'reason': 'Legacy 639% -> V2 idealized proxy already collapses hard. Directionally realistic, but magnitude is too large to accept without calibration.'},
        {'factor': 'A. entry_execution_realism', 'label': '保留', 'reason': 'Signal-close fills are not live-tradable enough to remain the default research assumption.'},
        {'factor': 'B. base_slippage', 'label': '保留', 'reason': 'Zero slippage should not be the default research regime.'},
        {'factor': 'C. breakout_stop_range_penalties', 'label': '校准', 'reason': 'Correct directionally, but stop/range penalties should be calibrated against real paper/live logs.'},
        {'factor': 'D. intrabar_pessimistic_path', 'label': '校准', 'reason': 'Valid as stress mode, possibly too heavy as the sole daily default.'},
        {'factor': 'E. partial_tp_removal', 'label': '保留', 'reason': 'This is alpha rescue, not alpha drag. Keep partial TP off by default until a conditional TP design proves better.'},
        {'factor': 'G. position_sizing_effect', 'label': '保留', 'reason': 'This is deployment sizing, not signal-quality decay.'},
    ]


def run_matrix(r: Runner) -> list[dict]:
    base = v2_base(25.0, False)
    execs = {'ideal_close': 'signal_close', 'next_bar_open': 'next_bar_open', 'close_plus_delay_bps': 'close_plus_delay_bps', 'live_runner_next_5m_close': 'live_runner_next_5m_close'}
    paths = ['optimistic', 'midpoint', 'volatility_aware', 'pessimistic']
    slips = {'none': slip_none(), 'fixed_only': slip_fixed(), 'full_model': slip_full()}
    rows = []
    for ek, ev in execs.items():
        for path in paths:
            for sk, sv in slips.items():
                row = r.v2(f'Matrix | exec={ek} | path={path} | slip={sk}', v2_with(base, entry_execution_mode=ev, intrabar_path_mode=path, close_delay_bps=8.0, **sv))
                band = 'not_live_comparable' if ek == 'ideal_close' or sk == 'none' else ('strict_stress' if ek == 'live_runner_next_5m_close' and sk == 'full_model' and path == 'pessimistic' else ('research_reasonable' if ek in {'next_bar_open', 'live_runner_next_5m_close'} and sk == 'full_model' and path in {'midpoint', 'volatility_aware'} else 'intermediate'))
                rows.append({'execution_mode': ek, 'intrabar_mode': path, 'slippage_mode': sk, 'reality_band': band, 'config': row['config'], 'metrics': row['metrics'], 'trade_shape': row['trade_shape']})
    return rows


def matrix_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{'execution_mode': r['execution_mode'], 'intrabar_mode': r['intrabar_mode'], 'slippage_mode': r['slippage_mode'], 'reality_band': r['reality_band'], 'Return_pct': r['metrics']['Return_pct'], 'CAGR_pct': r['metrics']['CAGR_pct'], 'Sharpe': r['metrics']['Sharpe'], 'MaxDD_pct': r['metrics']['MaxDD_pct'], 'PF': r['metrics']['PF'], 'Trades': r['metrics']['Trades'], 'unique_entries': r['trade_shape']['unique_entries'], 'avg_legs_per_entry': r['trade_shape']['avg_legs_per_entry']} for r in rows])


def choose_default(matrix_rows: list[dict]) -> dict:
    df = matrix_df([r for r in matrix_rows if r['reality_band'] in {'research_reasonable', 'strict_stress'}])
    if df.empty:
        return {'recommended_default': {'entry_execution_mode': 'live_runner_next_5m_close', 'intrabar_path_mode': 'pessimistic', 'slippage_mode': 'full_model'}, 'reason': 'Fallback to strict causal/stress default because no candidate rows were available.'}
    df['score'] = df.apply(lambda x: x['Sharpe'] * 1.8 + x['PF'] + x['Return_pct'] / 40.0 + x['MaxDD_pct'] / 30.0, axis=1)
    best = df.sort_values('score', ascending=False).iloc[0]
    return {'recommended_default': {'entry_execution_mode': str(best['execution_mode']), 'intrabar_path_mode': str(best['intrabar_mode']), 'slippage_mode': str(best['slippage_mode'])}, 'reason': 'Chosen from causal, non-zero slippage, paper/live-explainable candidates. Pessimistic full-model stays as stress mode.'}

def trade_attr(waterfall: list[dict]) -> dict:
    m = {row['label']: row for row in waterfall}
    order = ['Layer 0 | legacy old-style reference', 'Bridge | v2 legacy-proxy (signal_close + optimistic + no_slippage)', 'Layer 2 | + live_runner_next_5m_close', 'Layer 5 | + intrabar pessimistic', 'Layer 6 | + disable_partial_tp', 'Layer 7 | + launch assumptions (position_pct=25)']
    rows, prev = [], None
    for label in order:
        row = m[label]
        cur = {'label': label, 'Trades': row['metrics']['Trades'], 'unique_entries': row['trade_shape']['unique_entries'], 'avg_legs_per_entry': row['trade_shape']['avg_legs_per_entry']}
        if prev is None:
            cur.update({'delta_Trades': 0, 'delta_unique_entries': 0, 'delta_avg_legs_per_entry': 0.0})
        else:
            cur.update({'delta_Trades': cur['Trades'] - prev['Trades'], 'delta_unique_entries': cur['unique_entries'] - prev['unique_entries'], 'delta_avg_legs_per_entry': cur['avg_legs_per_entry'] - prev['avg_legs_per_entry']})
        rows.append(cur)
        prev = cur
    findings = [
        'Legacy -> V2 bridge keeps trade legs broadly similar if partial TP is still enabled, so the first collapse is expectancy collapse, not signal disappearance.',
        'Execution realism changes unique entries, but not enough to explain the full trade-leg collapse on its own.',
        'Disabling partial TP compresses trade legs much more than unique entries, so a large part of 791 -> 69 is statistics compression rather than raw signal scarcity.',
        'Position sizing still changes realized entry count because daily-loss gating and compounding alter whether later entries are allowed.',
    ]
    return {'rows': rows, 'findings': findings}


def wf_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([{'label': r['label'], 'engine': r['engine'], 'Return_pct': r['metrics']['Return_pct'], 'CAGR_pct': r['metrics']['CAGR_pct'], 'Sharpe': r['metrics']['Sharpe'], 'MaxDD_pct': r['metrics']['MaxDD_pct'], 'PF': r['metrics']['PF'], 'Trades': r['metrics']['Trades'], 'unique_entries': r['trade_shape']['unique_entries'], 'avg_legs_per_entry': r['trade_shape']['avg_legs_per_entry'], 'delta_Return_pct': r['delta']['delta_Return_pct'], 'delta_CAGR_pct': r['delta']['delta_CAGR_pct'], 'delta_Sharpe': r['delta']['delta_Sharpe'], 'delta_MaxDD_pct': r['delta']['delta_MaxDD_pct'], 'delta_PF': r['delta']['delta_PF'], 'delta_Trades': r['delta']['delta_Trades'], 'delta_unique_entries': r['delta']['delta_unique_entries'], 'delta_log_equity_return': r['delta']['delta_log_equity_return']} for r in rows])


def md_table(df: pd.DataFrame, cols: list[str]) -> str:
    view = df.loc[:, cols].copy()
    for c in view.columns:
        if np.issubdtype(view[c].dtype, np.floating):
            view[c] = view[c].map(lambda x: f'{x:.3f}' if c in {'Sharpe', 'PF', 'avg_legs_per_entry', 'delta_avg_legs_per_entry', 'delta_log_equity_return', 'drop_share_of_total_log_change'} else f'{x:.2f}')
    return view.to_markdown(index=False)


def write_outputs(outdir: Path, waterfall: list[dict], contrib: dict, matrix_rows: list[dict], default_regime: dict, trade_counts: dict, df5: pd.DataFrame, df4: pd.DataFrame) -> None:
    wdf = wf_df(waterfall)
    mdf = matrix_df(matrix_rows)
    cdf = pd.DataFrame(contrib['rows'])
    tdf = pd.DataFrame(trade_counts['rows'])
    tags = pd.DataFrame(realism_tags())
    excerpt = mdf[(mdf['execution_mode'].isin(['next_bar_open', 'live_runner_next_5m_close'])) & (mdf['slippage_mode'].isin(['fixed_only', 'full_model']))].sort_values(['execution_mode', 'slippage_mode', 'intrabar_mode'])
    md = '\n'.join([
        '# Alpha Collapse Waterfall', '',
        '- 是否推荐: 当前结果不支持直接把 launch_optimal 从 launch_no_go 改成 launch_go。',
        '- 相对旧口径: 收益坍塌的主因不是单一滑点，而是 `legacy -> v2` 的 intrabar 语义迁移、因果执行和仓位压缩共同作用。',
        '- 是否适合首发 live: 保护层和执行层更可靠了，但 alpha 层仍偏薄。',
        '- 主要风险: 当前默认 pessimistic + full slippage 可能混入一部分过度保守；但 ideal_close / zero-slip 又明显不真实。',
        '- 下一步主线: 先校准执行模型，再决定是否继续信号优化。', '',
        '## Waterfall Total Table', '', md_table(wdf, ['label', 'engine', 'Return_pct', 'CAGR_pct', 'Sharpe', 'MaxDD_pct', 'PF', 'Trades', 'unique_entries', 'avg_legs_per_entry', 'delta_Return_pct', 'delta_Sharpe', 'delta_MaxDD_pct', 'delta_Trades', 'delta_unique_entries']), '',
        '## Layer-by-Layer Interpretation', '',
        *[f"- {r['label']}: Return {r['delta']['delta_Return_pct']:+.2f}pp, Sharpe {r['delta']['delta_Sharpe']:+.3f}, MaxDD {r['delta']['delta_MaxDD_pct']:+.2f}pp, Trades {r['delta']['delta_Trades']:+d}, UniqueEntries {r['delta']['delta_unique_entries']:+d}, AvgLegs/Entry {r['delta']['delta_avg_legs_per_entry']:+.3f}." for r in waterfall[1:]], '',
        '## Contribution Ranking', '', md_table(cdf, ['factor', 'delta_Return_pct', 'delta_log_equity_return', 'drop_share_of_total_log_change']), '',
        '### Top 3 Drags', '', md_table(pd.DataFrame(contrib['top3_drags']), ['factor', 'delta_Return_pct', 'drop_share_of_total_log_change']), '',
        '## Reasonable De-Biasing vs Possible Over-Conservatism', '', md_table(tags, ['factor', 'label', 'reason']), '',
        '## Execution Matrix', '', 'Matrix scope: launch_optimal signal parameters, same position (`25%`), only execution realism dimensions vary.', '', md_table(excerpt, ['execution_mode', 'intrabar_mode', 'slippage_mode', 'reality_band', 'Return_pct', 'Sharpe', 'MaxDD_pct', 'PF', 'Trades']), '',
        '## Trade Count Collapse Attribution', '', md_table(tdf, ['label', 'Trades', 'unique_entries', 'avg_legs_per_entry', 'delta_Trades', 'delta_unique_entries', 'delta_avg_legs_per_entry']), '', *[f'- {x}' for x in trade_counts['findings']], '',
        '## Recommended Default Regime', '', f"- Recommended: `{default_regime['recommended_default']['entry_execution_mode']}` + `{default_regime['recommended_default']['intrabar_path_mode']}` + `{default_regime['recommended_default']['slippage_mode']}`", f"- Reason: {default_regime['reason']}", '- Stress default should remain: `live_runner_next_5m_close + pessimistic + full_model`', '',
        '## Next Steps', '', '- First, calibrate the V2 intrabar sequencing model against paper/live fills before touching signal parameters again.', '- Second, keep `disable_partial_tp` as an explicit switch in attribution studies, because it changes trade-leg statistics more than raw signal count.', '- Third, keep position sizing out of alpha discussions; treat it as launch deployment policy.'
    ])
    report = {
        'seed': SEED,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'data_range': {'five_min_start': str(df5['timestamp'].min()), 'five_min_end': str(df5['timestamp'].max()), 'four_hour_start': str(df4['timestamp'].min()), 'four_hour_end': str(df4['timestamp'].max())},
        'published_reference_points': {'baseline_60': {'Return_pct': 636.66, 'CAGR_pct': 37.85, 'Sharpe': 1.171, 'MaxDD_pct': -22.01, 'PF': 1.344, 'Trades': 928}, 'opt_signal_60': {'Return_pct': 639.02, 'CAGR_pct': 37.92, 'Sharpe': 1.183, 'MaxDD_pct': -21.16, 'PF': 1.368, 'Trades': 791}, 'launch_optimal': {'Return_pct': 34.63, 'CAGR_pct': 4.89, 'Sharpe': 0.775, 'MaxDD_pct': -4.50, 'PF': 2.84, 'Trades': 69}},
        'waterfall': waterfall, 'contributions': contrib, 'realism_classification': realism_tags(), 'matrix': matrix_rows, 'matrix_summary': mdf.to_dict(orient='records'), 'trade_count_attribution': trade_counts, 'recommended_default_regime': default_regime,
    }
    (outdir / 'waterfall.csv').write_text(wdf.to_csv(index=False), encoding='utf-8')
    (outdir / 'execution_matrix.csv').write_text(mdf.to_csv(index=False), encoding='utf-8')
    (outdir / 'alpha_collapse_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'alpha_collapse_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'ALPHA_COLLAPSE_WATERFALL.md').write_text(md, encoding='utf-8')
    top = list(contrib['top3_drags'])
    while len(top) < 3:
        top.append({'factor': 'n/a', 'delta_Return_pct': 0.0})
    summary = '\n'.join(['alpha collapse summary', f"legacy reference: {waterfall[0]['metrics']['Return_pct']:.2f}% return, {waterfall[0]['metrics']['Trades']} trade legs", f"launch final: {waterfall[-1]['metrics']['Return_pct']:.2f}% return, {waterfall[-1]['metrics']['CAGR_pct']:.2f}% CAGR, {waterfall[-1]['metrics']['Sharpe']:.3f} Sharpe, {waterfall[-1]['metrics']['Trades']} trade legs", f"biggest drag 1: {top[0]['factor']} ({top[0]['delta_Return_pct']:.2f}pp)", f"biggest drag 2: {top[1]['factor']} ({top[1]['delta_Return_pct']:.2f}pp)", f"biggest drag 3: {top[2]['factor']} ({top[2]['delta_Return_pct']:.2f}pp)", 'core conclusion: the first collapse is expectancy collapse from legacy->v2 intrabar semantics, not pure signal loss.', 'trade-count collapse is mostly trade-leg compression from removing partial TP, plus launch sizing changing daily-loss gating.', f"recommended daily research default: {default_regime['recommended_default']['entry_execution_mode']} + {default_regime['recommended_default']['intrabar_path_mode']} + {default_regime['recommended_default']['slippage_mode']}", 'strict stress regime should remain: live_runner_next_5m_close + pessimistic + full_model'])
    (ROOT / 'alpha_collapse_summary.txt').write_text(summary, encoding='utf-8')


def main() -> None:
    np.random.seed(SEED)
    outdir = DATA_DIR / f'alpha_collapse_{now_tag()}'
    outdir.mkdir(parents=True, exist_ok=True)
    loader = DataLoader5m(str(DATA_DIR))
    df5, df4 = loader.load_data()
    r = Runner(df5, df4)
    waterfall = build_waterfall(r)
    contrib = contributions(waterfall)
    matrix_rows = run_matrix(r)
    default_regime = choose_default(matrix_rows)
    trade_counts = trade_attr(waterfall)
    write_outputs(outdir, waterfall, contrib, matrix_rows, default_regime, trade_counts, df5, df4)
    print(json.dumps({'outdir': str(outdir), 'root_md': str(ROOT / 'ALPHA_COLLAPSE_WATERFALL.md'), 'root_json': str(ROOT / 'alpha_collapse_report.json'), 'root_txt': str(ROOT / 'alpha_collapse_summary.txt'), 'recommended_default': default_regime['recommended_default']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
