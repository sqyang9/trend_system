#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v85_wfo_validate.py
===================
V8.5策略 Walk-Forward Optimization 验证

模式:
1. per_year_eval: 固定参数逐年评估
2. wfo_rolling: 滚动窗口WFO

V8.5主要更新:
- 新增 useIntrabarStop 参数，支持保护止损模式
- 调整各项止损和止盈参数
- minSqueezeCandles: 2 → 4

使用:
  python v85_wfo_validate.py --csv ./data/btc_usdt_swap_4h.csv --mode per_year_eval
  python v85_wfo_validate.py --csv ./data/btc_usdt_swap_4h.csv --mode wfo_rolling --train_years 2
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from v85_intrabar_backtest import V85Params, IntrabarBacktestEngine, plot_results


def parse_args():
    ap = argparse.ArgumentParser(description='V8.5 WFO Validation')
    ap.add_argument('--data_dir', default='./data', help='数据目录')
    ap.add_argument('--mode', required=True, choices=['per_year_eval', 'wfo_rolling'])
    ap.add_argument('--train_years', type=int, default=2, help='WFO训练窗口年数')
    ap.add_argument('--outdir', default=None)
    ap.add_argument('--verbose', action='store_true')
    return ap.parse_args()


def year_slices(index: pd.DatetimeIndex) -> List[Tuple[str, pd.Timestamp, pd.Timestamp]]:
    """生成年度切片"""
    years = sorted(set(index.year.tolist()))
    slices = []
    
    # 单年
    for y in years:
        start = pd.Timestamp(f"{y}-01-01", tz="UTC")
        end = pd.Timestamp(f"{y+1}-01-01", tz="UTC")
        slices.append((str(y), start, end))
    
    # 2年合并
    for i in range(len(years) - 1):
        y0, y1 = years[i], years[i + 1]
        start = pd.Timestamp(f"{y0}-01-01", tz="UTC")
        end = pd.Timestamp(f"{y1+1}-01-01", tz="UTC")
        slices.append((f"{y0}-{y1}", start, end))
    
    # 3年合并
    for i in range(len(years) - 2):
        y0, y2 = years[i], years[i + 2]
        start = pd.Timestamp(f"{y0}-01-01", tz="UTC")
        end = pd.Timestamp(f"{y2+1}-01-01", tz="UTC")
        slices.append((f"{y0}-{y2}", start, end))
    
    return slices


def backtest_slice(df_5m: pd.DataFrame, df_4h: pd.DataFrame, p: V85Params,
                   start: pd.Timestamp, end: pd.Timestamp) -> Optional[Dict]:
    """对特定时间切片进行回测"""
    sub_4h = df_4h.loc[(df_4h.index >= start) & (df_4h.index < end)].copy()

    # 4H数据每天6根，至少需要30天数据
    if len(sub_4h) < 180:
        return None

    engine = IntrabarBacktestEngine(p, use_intrabar_stop=True)
    return engine.run(df_5m, sub_4h)


def per_year_evaluation(df_5m: pd.DataFrame, df_4h: pd.DataFrame, outdir: Path, verbose: bool):
    """固定参数逐年评估"""
    print("\n" + "=" * 60)
    print("模式: 固定参数逐年评估 (V8.5默认参数)")
    print("=" * 60)

    p = V85Params()  # 使用默认参数
    slices = year_slices(df_4h.index)

    rows = []

    for label, start, end in slices:
        print(f"\n[评估] 切片: {label} ({start.date()} → {end.date()})")

        result = backtest_slice(df_5m, df_4h, p, start, end)
        
        if result is None:
            print(f"  数据不足，跳过")
            continue
        
        stats = result['stats']
        
        # 保存切片详情
        slice_dir = outdir / f"slice_{label}"
        slice_dir.mkdir(parents=True, exist_ok=True)
        
        result['trades'].to_csv(slice_dir / 'trades.csv', index=False)
        result['equity'].to_csv(slice_dir / 'equity.csv')
        
        with open(slice_dir / 'stats.json', 'w') as f:
            json.dump(stats, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else x)
        
        try:
            plot_results(result, slice_dir, f" ({label})")
        except Exception as e:
            print(f"  绘图失败: {e}")
        
        row = {'slice': label, **stats}
        rows.append(row)
        
        print(f"  Sharpe={stats['Sharpe']:.3f}, CAGR={stats['CAGR']*100:.1f}%, "
              f"MaxDD={stats['MaxDD_pct']*100:.1f}%, Trades={stats['Trades']}")
    
    # 汇总
    summary_df = pd.DataFrame(rows)
    summary_df.to_csv(outdir / 'summary.csv', index=False)
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("逐年评估汇总")
    print("=" * 60)
    
    single_years = [r for r in rows if '-' not in r['slice']]
    if single_years:
        avg_sharpe = np.mean([r['Sharpe'] for r in single_years])
        avg_cagr = np.mean([r['CAGR'] for r in single_years])
        avg_dd = np.mean([r['MaxDD_pct'] for r in single_years])
        
        print(f"\n单年平均:")
        print(f"  Sharpe: {avg_sharpe:.3f}")
        print(f"  CAGR: {avg_cagr*100:.1f}%")
        print(f"  MaxDD: {avg_dd*100:.1f}%")
        
        positive_years = sum(1 for r in single_years if r['CAGR'] > 0)
        print(f"  盈利年份: {positive_years}/{len(single_years)}")
    
    return summary_df


def wfo_rolling(df_5m: pd.DataFrame, df_4h: pd.DataFrame, train_years: int, outdir: Path, verbose: bool):
    """滚动窗口WFO验证 (固定参数，不做网格搜索)"""
    print("\n" + "=" * 60)
    print(f"模式: 滚动WFO (训练{train_years}年 → 测试1年)")
    print("=" * 60)

    years = sorted(set(df_4h.index.year.tolist()))
    print(f"数据年份: {years}")

    rows = []

    for oos_year in years:
        # 训练窗口
        train_years_list = [y for y in years if (oos_year - train_years) <= y < oos_year]

        if len(train_years_list) < train_years:
            print(f"\n[WFO] OOS年: {oos_year} - 训练数据不足，跳过")
            continue

        print(f"\n[WFO] OOS年: {oos_year}, 训练年: {train_years_list}")

        # 测试OOS年
        test_start = pd.Timestamp(f"{oos_year}-01-01", tz="UTC")
        test_end = pd.Timestamp(f"{oos_year+1}-01-01", tz="UTC")

        p = V85Params()  # 使用固定默认参数

        oos_result = backtest_slice(df_5m, df_4h, p, test_start, test_end)
        
        if oos_result is None:
            print(f"  OOS数据不足")
            continue
        
        oos_stats = oos_result['stats']
        
        # 保存OOS详情
        oos_dir = outdir / f"oos_{oos_year}"
        oos_dir.mkdir(parents=True, exist_ok=True)
        
        oos_result['trades'].to_csv(oos_dir / 'trades.csv', index=False)
        oos_result['equity'].to_csv(oos_dir / 'equity.csv')
        
        with open(oos_dir / 'stats.json', 'w') as f:
            json.dump(oos_stats, f, indent=2, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else x)
        
        try:
            plot_results(oos_result, oos_dir, f" (OOS {oos_year})")
        except:
            pass
        
        row = {
            'oos_year': oos_year,
            'train_years': str(train_years_list),
            **oos_stats
        }
        rows.append(row)
        
        print(f"  OOS结果: Sharpe={oos_stats['Sharpe']:.3f}, CAGR={oos_stats['CAGR']*100:.1f}%, "
              f"Trades={oos_stats['Trades']}, WinRate={oos_stats['WinRate_pct']:.1f}%")
    
    # 汇总
    if rows:
        summary_df = pd.DataFrame(rows)
        summary_df.to_csv(outdir / 'summary.csv', index=False)
        
        print("\n" + "=" * 60)
        print("WFO汇总")
        print("=" * 60)
        
        avg_sharpe = summary_df['Sharpe'].mean()
        avg_cagr = summary_df['CAGR'].mean()
        avg_dd = summary_df['MaxDD_pct'].mean()
        
        print(f"OOS平均:")
        print(f"  Sharpe: {avg_sharpe:.3f}")
        print(f"  CAGR: {avg_cagr*100:.1f}%")
        print(f"  MaxDD: {avg_dd*100:.1f}%")
        
        positive_years = sum(1 for _, r in summary_df.iterrows() if r['CAGR'] > 0)
        print(f"  盈利年份: {positive_years}/{len(summary_df)}")
        
        return summary_df
    
    return None


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

    # 输出目录
    stamp = pd.Timestamp.utcnow().strftime('%Y%m%d_%H%M%S')
    outdir = Path(args.outdir) if args.outdir else Path(args.data_dir) / f'v85_wfo_{args.mode}_{stamp}'
    outdir.mkdir(parents=True, exist_ok=True)

    # 执行
    if args.mode == 'per_year_eval':
        per_year_evaluation(df_5m, df_4h, outdir, args.verbose)
    elif args.mode == 'wfo_rolling':
        wfo_rolling(df_5m, df_4h, args.train_years, outdir, args.verbose)
    
    print(f"\n结果保存至: {outdir}")


if __name__ == "__main__":
    main()
