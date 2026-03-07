#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v85_full_validation.py
======================
V8.5策略完整验证流程

执行:
1. 基础回测
2. 逐年评估
3. WFO验证
4. 蒙特卡洛模拟

V8.5主要更新:
- 新增 useIntrabarStop 参数，支持保护止损模式
- 调整各项止损和止盈参数
- minSqueezeCandles: 2 → 4

Usage:
  python v85_full_validation.py --csv ./data/btc_usdt_swap_4h.csv
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

from v85_intrabar_backtest import V85Params, IntrabarBacktestEngine, plot_results


def parse_args():
    ap = argparse.ArgumentParser(description='V8.5 Full Validation')
    ap.add_argument('--data_dir', default='./data', help='数据目录')
    ap.add_argument('--outdir', default=None)
    ap.add_argument('--mc_n', type=int, default=5000, help='蒙特卡洛模拟次数')
    ap.add_argument('--verbose', action='store_true')
    return ap.parse_args()


def load_data(csv_path: str) -> pd.DataFrame:
    """加载4H数据"""
    df = pd.read_csv(csv_path)
    
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
        df = df.set_index('timestamp')
    
    return df.sort_index()


def run_basic_backtest(df_5m: pd.DataFrame, df_4h: pd.DataFrame, outdir: Path, verbose: bool) -> dict:
    """基础回测"""
    print("\n" + "=" * 60)
    print("1. 基础回测")
    print("=" * 60)

    p = V85Params()
    engine = IntrabarBacktestEngine(p, use_intrabar_stop=True)
    result = engine.run(df_5m, df_4h)
    
    # 保存
    bt_dir = outdir / '1_backtest'
    bt_dir.mkdir(parents=True, exist_ok=True)
    
    result['trades'].to_csv(bt_dir / 'trades.csv', index=False)
    result['equity'].to_csv(bt_dir / 'equity.csv')
    
    with open(bt_dir / 'stats.json', 'w') as f:
        json.dump(result['stats'], f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else x)
    
    plot_results(result, bt_dir)
    
    stats = result['stats']
    print(f"\n结果:")
    print(f"  总收益: {stats['TotalReturn_pct']:.1f}%")
    print(f"  CAGR: {stats['CAGR']*100:.1f}%")
    print(f"  Sharpe: {stats['Sharpe']:.3f}")
    print(f"  MaxDD: {stats['MaxDD_pct']*100:.1f}%")
    print(f"  PF: {stats['ProfitFactor']:.2f}")
    print(f"  交易: {stats['Trades']} (胜率: {stats['WinRate_pct']:.1f}%)")
    print(f"  多单: {stats['LongTrades']}, 空单: {stats['ShortTrades']}")
    
    return result


def run_per_year_eval(df_5m: pd.DataFrame, df_4h: pd.DataFrame, outdir: Path) -> dict:
    """逐年评估"""
    print("\n" + "=" * 60)
    print("2. 逐年评估")
    print("=" * 60)

    p = V85Params()
    years = sorted(set(df_4h.index.year.tolist()))

    pye_dir = outdir / '2_per_year_eval'
    pye_dir.mkdir(parents=True, exist_ok=True)

    rows = []

    for year in years:
        start = pd.Timestamp(f"{year}-01-01", tz="UTC")
        end = pd.Timestamp(f"{year+1}-01-01", tz="UTC")

        sub_4h = df_4h.loc[(df_4h.index >= start) & (df_4h.index < end)].copy()

        if len(sub_4h) < 180:  # 至少30天数据
            print(f"  {year}: 数据不足")
            continue

        engine = IntrabarBacktestEngine(p, use_intrabar_stop=True)
        result = engine.run(df_5m, sub_4h)
        stats = result['stats']
        
        rows.append({
            'year': year,
            'CAGR': stats['CAGR'],
            'Sharpe': stats['Sharpe'],
            'MaxDD_pct': stats['MaxDD_pct'],
            'ProfitFactor': stats['ProfitFactor'],
            'Trades': stats['Trades'],
            'WinRate_pct': stats['WinRate_pct']
        })
        
        print(f"  {year}: Sharpe={stats['Sharpe']:.3f}, CAGR={stats['CAGR']*100:.1f}%, "
              f"MaxDD={stats['MaxDD_pct']*100:.1f}%, Trades={stats['Trades']}")
    
    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(pye_dir / 'summary.csv', index=False)
    
    # 汇总统计
    avg_sharpe = summary_df['Sharpe'].mean()
    avg_cagr = summary_df['CAGR'].mean()
    positive_years = (summary_df['CAGR'] > 0).sum()
    
    print(f"\n汇总:")
    print(f"  平均Sharpe: {avg_sharpe:.3f}")
    print(f"  平均CAGR: {avg_cagr*100:.1f}%")
    print(f"  盈利年份: {positive_years}/{len(summary_df)}")
    
    return {
        'avg_sharpe': avg_sharpe,
        'avg_cagr': avg_cagr,
        'positive_years': positive_years,
        'total_years': len(summary_df)
    }


def run_monte_carlo(df_5m: pd.DataFrame, df_4h: pd.DataFrame, outdir: Path, n_sims: int = 1000) -> dict:
    """蒙特卡洛模拟"""
    print("\n" + "=" * 60)
    print("3. 蒙特卡洛模拟")
    print("=" * 60)

    mc_dir = outdir / '3_monte_carlo'
    mc_dir.mkdir(parents=True, exist_ok=True)

    # 运行基础回测获取交易数据
    p = V85Params()
    engine = IntrabarBacktestEngine(p, use_intrabar_stop=True)
    base_result = engine.run(df_5m, df_4h)
    trades_df = base_result['trades']

    if len(trades_df) == 0:
        print("  无交易数据")
        return {}

    # 计算收益率序列
    init_equity = 10000.0
    pnl = trades_df['pnl'].values

    equity = init_equity
    returns = []
    for p in pnl:
        if equity > 0:
            r = p / equity
            returns.append(r)
            equity += p

    returns = np.array(returns)

    # 计算时间跨度
    try:
        t0 = pd.to_datetime(trades_df['entry_time'].iloc[0])
        t1 = pd.to_datetime(trades_df['exit_time'].iloc[-1])
        span_years = max((t1 - t0).total_seconds() / (365.25 * 24 * 3600), 1e-6)
    except:
        span_years = 1.0

    print(f"  交易数: {len(returns)}")
    print(f"  时间跨度: {span_years:.2f}年")
    print(f"  模拟次数: {n_sims}")
    
    # Block Bootstrap
    np.random.seed(42)
    block_size = 3
    m = len(returns)
    
    cagrs = np.empty(n_sims)
    maxdds = np.empty(n_sims)
    
    for i in range(n_sims):
        # 重采样
        seq = []
        while len(seq) < m:
            start = np.random.randint(0, max(1, m - block_size + 1))
            seq.extend(returns[start:start + block_size])
        seq = np.array(seq[:m])
        
        # 计算权益曲线
        eq = np.empty(m + 1)
        eq[0] = init_equity
        for j, r in enumerate(seq):
            eq[j + 1] = eq[j] * (1 + r)
        
        # CAGR
        ratio = max(eq[-1] / init_equity, 1e-12)
        cagrs[i] = (ratio ** (1.0 / span_years)) - 1.0
        
        # MaxDD
        peak = eq[0]
        max_dd = 0.0
        for e in eq:
            peak = max(peak, e)
            dd = (e / peak - 1.0) if peak > 0 else 0.0
            max_dd = min(max_dd, dd)
        maxdds[i] = max_dd
    
    # 结果
    mc_result = {
        'cagr_p05': float(np.percentile(cagrs, 5)),
        'cagr_p50': float(np.percentile(cagrs, 50)),
        'cagr_p95': float(np.percentile(cagrs, 95)),
        'maxdd_p50': float(np.percentile(maxdds, 50)),
        'maxdd_p95': float(np.percentile(maxdds, 95)),
        'prob_positive': float(np.mean(cagrs > 0))
    }
    
    with open(mc_dir / 'summary.json', 'w') as f:
        json.dump(mc_result, f, indent=2)
    
    print(f"\n结果:")
    print(f"  CAGR 5th: {mc_result['cagr_p05']*100:.1f}%")
    print(f"  CAGR 50th: {mc_result['cagr_p50']*100:.1f}%")
    print(f"  CAGR 95th: {mc_result['cagr_p95']*100:.1f}%")
    print(f"  MaxDD 50th: {mc_result['maxdd_p50']*100:.1f}%")
    print(f"  MaxDD 95th: {mc_result['maxdd_p95']*100:.1f}%")
    print(f"  正收益概率: {mc_result['prob_positive']*100:.1f}%")
    
    return mc_result


def main():
    args = parse_args()

    # 导入数据加载器
    import sys
    sys.path.insert(0, args.data_dir)

    try:
        from universal_data_updater_5m import DataLoader5m
    except ImportError:
        print("错误: 找不到 universal_data_updater_5m.py")
        print("请确保数据目录中包含此文件")
        return

    # 加载数据
    print("加载数据...")
    loader = DataLoader5m(args.data_dir)

    try:
        df_5m, df_4h = loader.load_data()
    except FileNotFoundError as e:
        print(f"错误: {e}")
        print("请先运行: python universal_data_updater_5m.py --fetch")
        return

    print(f"5m数据: {len(df_5m)} 根K线")
    print(f"4h数据: {len(df_4h)} 根K线")

    # 确保时间戳为索引
    if 'timestamp' in df_4h.columns:
        df_4h = df_4h.set_index('timestamp')
    df_4h = df_4h.sort_index()

    # 验证4H数据
    if len(df_4h) > 1:
        time_diff = (df_4h.index[1] - df_4h.index[0]).total_seconds() / 3600
        print(f"K线间隔: {time_diff:.1f}小时")
        if abs(time_diff - 4) > 0.5:
            print(f"⚠️ 警告: 数据不是4H周期!")
            return

    # 输出目录
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    outdir = Path(args.outdir) if args.outdir else Path('./data') / f'v85_validation_{stamp}'
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"\n输出目录: {outdir}")

    # 1. 基础回测
    bt_result = run_basic_backtest(df_5m, df_4h, outdir, args.verbose)

    # 2. 逐年评估
    pye_result = run_per_year_eval(df_5m, df_4h, outdir)

    # 3. 蒙特卡洛
    mc_result = run_monte_carlo(df_5m, df_4h, outdir, args.mc_n)
    
    # 汇总报告
    print("\n" + "=" * 70)
    print("V8.5 验证报告")
    print("=" * 70)
    
    stats = bt_result['stats']
    print(f"\n📊 基础回测:")
    print(f"   总收益: {stats['TotalReturn_pct']:.1f}%")
    print(f"   CAGR: {stats['CAGR']*100:.1f}%")
    print(f"   Sharpe: {stats['Sharpe']:.3f}")
    print(f"   MaxDD: {stats['MaxDD_pct']*100:.1f}%")
    print(f"   Profit Factor: {stats['ProfitFactor']:.2f}")
    print(f"   交易数: {stats['Trades']} (胜率: {stats['WinRate_pct']:.1f}%)")
    
    if pye_result:
        print(f"\n📅 逐年评估:")
        print(f"   平均Sharpe: {pye_result['avg_sharpe']:.3f}")
        print(f"   平均CAGR: {pye_result['avg_cagr']*100:.1f}%")
        print(f"   盈利年份: {pye_result['positive_years']}/{pye_result['total_years']}")
    
    if mc_result:
        print(f"\n🎲 蒙特卡洛:")
        print(f"   CAGR 5th: {mc_result['cagr_p05']*100:.1f}%")
        print(f"   CAGR 50th: {mc_result['cagr_p50']*100:.1f}%")
        print(f"   CAGR 95th: {mc_result['cagr_p95']*100:.1f}%")
        print(f"   正收益概率: {mc_result['prob_positive']*100:.1f}%")
    
    print("\n" + "=" * 70)
    print(f"✓ 验证完成! 结果保存至: {outdir}")
    print("=" * 70)
    
    # 保存汇总
    summary = {
        'backtest': stats,
        'per_year': pye_result,
        'monte_carlo': mc_result
    }
    
    with open(outdir / 'validation_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else x)


if __name__ == "__main__":
    main()
