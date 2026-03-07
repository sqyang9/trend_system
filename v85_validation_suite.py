#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v85_validation_suite.py
=======================
V8.5策略验证套件：WFO、年度验证、蒙特卡洛模拟

基于v85_intrabar_backtest.py的完整验证框架
"""

import argparse
import json
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from datetime import datetime, timedelta
from itertools import product
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# 导入原有的回测引擎
from v85_intrabar_backtest import (
    V85Params, IntrabarBacktestEngine, Direction,
    IndicatorEngine, check_entry_conditions
)


# ============================================================
# 1. WFO验证框架
# ============================================================

@dataclass
class WFOParams:
    """WFO参数配置"""
    # 时间划分
    train_periods: int = 6        # 训练周期数
    test_periods: int = 2         # 测试周期数
    step_periods: int = 1         # 步进周期数

    # 参数优化范围
    param_ranges: dict = None

    def __post_init__(self):
        if self.param_ranges is None:
            self.param_ranges = {
                'initial_stop_atr': (1.5, 3.5, 0.2),
                'trail_start_atr': (2.0, 4.0, 0.2),
                'trail_offset_atr': (1.5, 3.5, 0.2),
                'tp1_atr': (1.5, 3.0, 0.15),
                'tp2_atr': (2.5, 4.5, 0.2),
                'position_pct': (40, 80, 10),
                'min_long_score': (0, 2, 1),
                'min_short_score': (2, 4, 1),
                'squeeze_threshold': (0.8, 1.0, 0.05),
                'min_squeeze_candles': (3, 6, 1)
            }


class WFOValidator:
    """Walk Forward Optimization验证器"""

    def __init__(self, wfo_params: WFOParams, base_params: V85Params):
        self.wfo = wfo_params
        self.base_params = base_params
        self.results = []

    def optimize_parameters(self, df_5m: pd.DataFrame, df_4h: pd.DataFrame,
                          start_idx: int, end_idx: int) -> Tuple[V85Params, Dict]:
        """参数优化"""
        print(f"    参数优化: {start_idx} -> {end_idx} ({len(df_4h.iloc[start_idx:end_idx])} 根4HK线)")

        param_ranges = self.wfo.param_ranges
        best_params = None
        best_score = -np.inf
        best_stats = None

        # 生成参数组合 (限制组合数量避免过度计算)
        param_combinations = self._generate_param_combinations(param_ranges)

        print(f"    测试 {len(param_combinations)} 种参数组合...")

        for i, param_set in enumerate(param_combinations):
            # 创建参数对象
            params = V85Params(**{**asdict(self.base_params), **param_set})

            # 运行回测
            engine = IntrabarBacktestEngine(params, use_intrabar_stop=True)

            # 切片数据
            train_5m = df_5m.copy()
            train_4h = df_4h.iloc[start_idx:end_idx].copy()

            try:
                result = engine.run(train_5m, train_4h)
                stats = result['stats']

                # 计算综合评分 (Sharpe * sqrt(trades) - drawdown_penalty)
                if stats['Trades'] > 10:
                    score = stats['Sharpe'] * np.sqrt(stats['Trades']) / 100
                    score += stats['MaxDD_pct'] * 2  # 回撤惩罚

                    if score > best_score:
                        best_score = score
                        best_params = params
                        best_stats = stats

                if (i + 1) % 20 == 0:
                    print(f"      进度: {i + 1}/{len(param_combinations)}, 最佳分数: {best_score:.3f}")

            except Exception as e:
                continue

        print(f"    最佳参数: {best_score:.3f}")
        return best_params, best_stats

    def _generate_param_combinations(self, param_ranges: dict) -> List[dict]:
        """生成参数组合"""
        keys = list(param_ranges.keys())
        ranges = []

        for key in keys:
            start, end, step = param_ranges[key]
            if isinstance(step, float):
                # 浮点数参数
                values = []
                v = start
                while v <= end + 1e-9:
                    values.append(round(v, 2))
                    v += step
                ranges.append(values)
            else:
                # 整数参数
                values = list(range(int(start), int(end) + 1, int(step)))
                ranges.append(values)

        # 限制组合数量
        total_combinations = np.prod([len(r) for r in ranges])
        if total_combinations > 200:
            # 随机采样
            np.random.seed(42)
            sampled_indices = np.random.choice(total_combinations, size=200, replace=False)
            combinations = []
            for idx in sampled_indices:
                param_set = {}
                for i, key in enumerate(keys):
                    param_idx = idx % len(ranges[i])
                    param_set[key] = ranges[i][param_idx]
                    idx //= len(ranges[i])
                combinations.append(param_set)
            return combinations
        else:
            # 全组合
            return [dict(zip(keys, combo)) for combo in product(*ranges)]

    def run_wfo(self, df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
        """运行WFO验证"""
        print("=" * 70)
        print("WFO (Walk Forward Optimization) 验证")
        print("=" * 70)

        total_periods = len(df_4h)
        period_size = total_periods // 12  # 大约按月份划分

        wfo_results = []
        current_idx = 0

        while current_idx + self.wfo.train_periods + self.wfo.test_periods <= total_periods:
            train_start = current_idx
            train_end = current_idx + self.wfo.train_periods * period_size
            test_start = train_end
            test_end = test_start + self.wfo.test_periods * period_size

            print(f"\n--- WFO Fold {len(wfo_results) + 1} ---")
            print(f"训练期: {df_4h.index[train_start]} -> {df_4h.index[train_end-1]}")
            print(f"测试期: {df_4h.index[test_start]} -> {df_4h.index[test_end-1]}")

            # 1. 参数优化
            best_params, train_stats = self.optimize_parameters(
                df_5m, df_4h, train_start, train_end
            )

            if best_params is None:
                print("    优化失败，跳过此fold")
                current_idx += self.wfo.step_periods * period_size
                continue

            # 2. 测试期验证
            print(f"    测试期验证...")
            engine = IntrabarBacktestEngine(best_params, use_intrabar_stop=True)
            test_result = engine.run(df_5m, df_4h.iloc[test_start:test_end])

            # 3. 记录结果
            fold_result = {
                'fold': len(wfo_results) + 1,
                'train_period': (df_4h.index[train_start], df_4h.index[train_end-1]),
                'test_period': (df_4h.index[test_start], df_4h.index[test_end-1]),
                'best_params': asdict(best_params),
                'train_stats': train_stats,
                'test_stats': test_result['stats'],
                'test_trades': test_result['trades'],
                'test_equity': test_result['equity']
            }

            wfo_results.append(fold_result)

            print(f"    训练期Sharpe: {train_stats.get('Sharpe', 0):.3f}")
            print(f"    测试期Sharpe: {test_result['stats'].get('Sharpe', 0):.3f}")
            print(f"    测试期收益: {test_result['stats'].get('TotalReturn_pct', 0):.2f}%")

            # 4. 步进
            current_idx += self.wfo.step_periods * period_size

        # 汇总WFO结果
        wfo_summary = self._summarize_wfo(wfo_results)

        return {
            'wfo_results': wfo_results,
            'wfo_summary': wfo_summary,
            'total_folds': len(wfo_results)
        }

    def _summarize_wfo(self, wfo_results: List[Dict]) -> Dict:
        """汇总WFO结果"""
        if not wfo_results:
            return {}

        train_sharpes = [r['train_stats'].get('Sharpe', 0) for r in wfo_results if r['train_stats']]
        test_sharpes = [r['test_stats'].get('Sharpe', 0) for r in wfo_results if r['test_stats']]
        test_returns = [r['test_stats'].get('TotalReturn_pct', 0) for r in wfo_results if r['test_stats']]
        test_trades = [r['test_stats'].get('Trades', 0) for r in wfo_results if r['test_stats']]

        total_test_return = sum(test_returns)
        avg_test_sharpe = np.mean(test_sharpes) if test_sharpes else 0

        # 计算参数稳定性
        param_stability = self._calc_param_stability(wfo_results)

        return {
            'avg_train_sharpe': np.mean(train_sharpes) if train_sharpes else 0,
            'avg_test_sharpe': avg_test_sharpe,
            'total_test_return': total_test_return,
            'avg_test_return': np.mean(test_returns) if test_returns else 0,
            'total_test_trades': sum(test_trades),
            'out_of_sample_ratio': avg_test_sharpe / (np.mean(train_sharpes) if train_sharpes else 1),
            'param_stability': param_stability,
            'fold_count': len(wfo_results)
        }

    def _calc_param_stability(self, wfo_results: List[Dict]) -> Dict:
        """计算参数稳定性"""
        if len(wfo_results) < 2:
            return {}

        param_names = ['initial_stop_atr', 'trail_start_atr', 'tp1_atr', 'tp2_atr', 'position_pct']
        stability = {}

        for param in param_names:
            values = [r['best_params'][param] for r in wfo_results if param in r['best_params']]
            if values:
                stability[param] = {
                    'mean': np.mean(values),
                    'std': np.std(values),
                    'cv': np.std(values) / (np.mean(values) + 1e-9)  # 变异系数
                }

        return stability


# ============================================================
# 2. 年度验证框架
# ============================================================

class YearlyValidator:
    """年度验证器"""

    def __init__(self, params: V85Params):
        self.params = params

    def run_yearly_validation(self, df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
        """运行年度验证"""
        print("=" * 70)
        print("年度验证")
        print("=" * 70)

        # 获取年份范围
        start_year = df_4h.index[0].year
        end_year = df_4h.index[-1].year

        yearly_results = []

        for year in range(start_year, end_year + 1):
            print(f"\n--- {year}年 ---")

            # 筛选年度数据
            year_mask = df_4h.index.year == year
            year_4h = df_4h[year_mask].copy()

            if len(year_4h) < 100:  # 数据不足
                print(f"  数据不足，跳过")
                continue

            print(f"  数据量: {len(year_4h)} 根4H K线")

            # 运行回测
            engine = IntrabarBacktestEngine(self.params, use_intrabar_stop=True)
            try:
                year_result = engine.run(df_5m, year_4h)

                yearly_result = {
                    'year': year,
                    'stats': year_result['stats'],
                    'trades': year_result['trades'],
                    'equity': year_result['equity']
                }

                yearly_results.append(yearly_result)

                stats = year_result['stats']
                print(f"  收益: {stats.get('TotalReturn_pct', 0):.2f}%")
                print(f"  Sharpe: {stats.get('Sharpe', 0):.3f}")
                print(f"  最大回撤: {stats.get('MaxDD_pct', 0)*100:.2f}%")
                print(f"  交易数: {stats.get('Trades', 0)}")
                print(f"  胜率: {stats.get('WinRate_pct', 0):.1f}%")

            except Exception as e:
                print(f"  错误: {e}")
                continue

        # 汇总年度结果
        yearly_summary = self._summarize_yearly(yearly_results)

        return {
            'yearly_results': yearly_results,
            'yearly_summary': yearly_summary
        }

    def _summarize_yearly(self, yearly_results: List[Dict]) -> Dict:
        """汇总年度结果"""
        if not yearly_results:
            return {}

        returns = [r['stats'].get('TotalReturn_pct', 0) for r in yearly_results if r['stats']]
        sharpes = [r['stats'].get('Sharpe', 0) for r in yearly_results if r['stats']]
        drawdowns = [r['stats'].get('MaxDD_pct', 0) for r in yearly_results if r['stats']]
        trades = [r['stats'].get('Trades', 0) for r in yearly_results if r['stats']]

        positive_years = len([r for r in returns if r > 0])

        return {
            'years_analyzed': len(yearly_results),
            'positive_years': positive_years,
            'win_rate_years': positive_years / len(yearly_results) * 100,
            'avg_return': np.mean(returns) if returns else 0,
            'return_std': np.std(returns) if returns else 0,
            'best_year': max(returns) if returns else 0,
            'worst_year': min(returns) if returns else 0,
            'avg_sharpe': np.mean(sharpes) if sharpes else 0,
            'avg_maxdd': np.mean(drawdowns) if drawdowns else 0,
            'avg_trades_per_year': np.mean(trades) if trades else 0,
            'total_return': sum(returns)
        }


# ============================================================
# 3. 蒙特卡洛模拟框架
# ============================================================

class MonteCarloValidator:
    """蒙特卡洛验证器"""

    def __init__(self, params: V85Params, n_simulations: int = 1000):
        self.params = params
        self.n_simulations = n_simulations

    def run_monte_carlo(self, df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict:
        """运行蒙特卡洛模拟"""
        print("=" * 70)
        print(f"蒙特卡洛模拟 ({self.n_simulations} 次)")
        print("=" * 70)

        # 1. 基准回测
        print("运行基准回测...")
        base_engine = IntrabarBacktestEngine(self.params, use_intrabar_stop=True)
        base_result = base_engine.run(df_5m, df_4h)
        base_trades = base_result['trades']

        if len(base_trades) == 0:
            print("没有交易记录，无法进行蒙特卡洛模拟")
            return {}

        print(f"基准交易数: {len(base_trades)}")

        # 2. 准备交易数据
        trade_returns = base_trades['pnl'].values
        trade_dates = base_trades['exit_time'].values

        # 3. 蒙特卡洛模拟
        simulation_results = []

        for i in range(self.n_simulations):
            if (i + 1) % 100 == 0:
                print(f"  模拟进度: {i + 1}/{self.n_simulations}")

            # 随机重排交易序列
            np.random.seed(i)  # 保证可重复性
            shuffled_returns = np.random.permutation(trade_returns)

            # 计算累计权益曲线
            cumulative_returns = np.cumsum(shuffled_returns)
            equity_curve = self.params.init_equity + cumulative_returns

            # 计算统计指标
            peak = np.maximum.accumulate(equity_curve)
            drawdown = (equity_curve - peak) / peak
            max_dd = drawdown.min()

            # 计算收益率和Sharpe
            returns = np.diff(equity_curve) / equity_curve[:-1]
            sharpe = np.mean(returns) / (np.std(returns) + 1e-9) * np.sqrt(252) if len(returns) > 1 else 0

            final_equity = equity_curve[-1]
            total_return = (final_equity / self.params.init_equity - 1) * 100

            simulation_results.append({
                'final_equity': final_equity,
                'total_return': total_return,
                'max_dd': max_dd,
                'sharpe': sharpe,
                'equity_curve': equity_curve
            })

        # 4. 统计分析
        mc_summary = self._analyze_monte_carlo(simulation_results, base_result['stats'])

        return {
            'base_result': base_result,
            'simulation_results': simulation_results,
            'monte_carlo_summary': mc_summary
        }

    def _analyze_monte_carlo(self, simulation_results: List[Dict], base_stats: Dict) -> Dict:
        """分析蒙特卡洛结果"""
        returns = [s['total_return'] for s in simulation_results]
        max_dds = [s['max_dd'] for s in simulation_results]
        sharpes = [s['sharpe'] for s in simulation_results]
        final_equities = [s['final_equity'] for s in simulation_results]

        # 分位数分析
        percentiles = [5, 10, 25, 50, 75, 90, 95]

        return_stats = {}
        dd_stats = {}
        sharpe_stats = {}
        equity_stats = {}

        for p in percentiles:
            return_stats[f'p{p}'] = np.percentile(returns, p)
            dd_stats[f'p{p}'] = np.percentile(max_dds, p)
            sharpe_stats[f'p{p}'] = np.percentile(sharpes, p)
            equity_stats[f'p{p}'] = np.percentile(final_equities, p)

        # 概率计算
        prob_positive = len([r for r in returns if r > 0]) / len(returns) * 100
        prob_beat_base = len([r for r in returns if r > base_stats.get('TotalReturn_pct', 0)]) / len(returns) * 100

        return {
            'percentiles_return': return_stats,
            'percentiles_maxdd': dd_stats,
            'percentiles_sharpe': sharpe_stats,
            'percentiles_equity': equity_stats,
            'prob_positive': prob_positive,
            'prob_beat_base': prob_beat_base,
            'base_return': base_stats.get('TotalReturn_pct', 0),
            'base_sharpe': base_stats.get('Sharpe', 0),
            'base_maxdd': base_stats.get('MaxDD_pct', 0),
            'simulations_count': len(simulation_results)
        }


# ============================================================
# 4. 综合报告生成器
# ============================================================

class ValidationReporter:
    """验证报告生成器"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_comprehensive_report(self, wfo_result: Dict,
                                    yearly_result: Dict,
                                    monte_carlo_result: Dict,
                                    base_result: Dict) -> Dict:
        """生成综合报告"""
        print("=" * 70)
        print("生成综合验证报告")
        print("=" * 70)

        report = {
            'timestamp': datetime.now().isoformat(),
            'base_backtest': base_result['stats'],
            'wfo_validation': wfo_result.get('wfo_summary', {}),
            'yearly_validation': yearly_result.get('yearly_summary', {}),
            'monte_carlo_validation': monte_carlo_result.get('monte_carlo_summary', {}),
            'overall_assessment': self._overall_assessment(
                wfo_result, yearly_result, monte_carlo_result, base_result
            )
        }

        # 保存报告
        with open(self.output_dir / 'validation_report.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)

        # 生成图表
        self._create_visualizations(wfo_result, yearly_result, monte_carlo_result, base_result)

        # 打印摘要
        self._print_summary(report)

        return report

    def _overall_assessment(self, wfo_result: Dict, yearly_result: Dict,
                          monte_carlo_result: Dict, base_result: Dict) -> Dict:
        """综合评估"""
        assessment = {
            'strategy_strength': 'UNKNOWN',
            'robustness_score': 0,
            'recommendations': []
        }

        base_stats = base_result['stats']
        score = 0

        # 1. 基础性能评估 (40%)
        base_sharpe = base_stats.get('Sharpe', 0)
        base_return = base_stats.get('TotalReturn_pct', 0)
        base_dd = abs(base_stats.get('MaxDD_pct', 0))

        if base_sharpe > 1.0:
            score += 15
            assessment['recommendations'].append("基础Sharpe比率优秀")
        elif base_sharpe > 0.5:
            score += 10
            assessment['recommendations'].append("基础Sharpe比率良好")

        if base_return > 50:
            score += 15
            assessment['recommendations'].append("总收益率优秀")
        elif base_return > 20:
            score += 10
            assessment['recommendations'].append("总收益率良好")

        if base_dd < 0.2:
            score += 10
            assessment['recommendations'].append("最大回撤控制良好")

        # 2. WFO稳健性评估 (30%)
        wfo_summary = wfo_result.get('wfo_summary', {})
        if wfo_summary:
            oos_ratio = wfo_summary.get('out_of_sample_ratio', 0)
            if oos_ratio > 0.7:
                score += 20
                assessment['recommendations'].append("样本外表现稳健")
            elif oos_ratio > 0.5:
                score += 15
                assessment['recommendations'].append("样本外表现良好")

            fold_count = wfo_summary.get('fold_count', 0)
            if fold_count >= 3:
                score += 10
                assessment['recommendations'].append("WFO验证次数充足")

        # 3. 年度一致性评估 (20%)
        yearly_summary = yearly_result.get('yearly_summary', {})
        if yearly_summary:
            win_rate_years = yearly_summary.get('win_rate_years', 0)
            if win_rate_years > 70:
                score += 15
                assessment['recommendations'].append("年度表现一致性高")
            elif win_rate_years > 50:
                score += 10
                assessment['recommendations'].append("年度表现一致性中等")

            avg_return = yearly_summary.get('avg_return', 0)
            if avg_return > 0:
                score += 5
                assessment['recommendations'].append("平均年度收益为正")

        # 4. 蒙特卡洛风险评估 (10%)
        mc_summary = monte_carlo_result.get('monte_carlo_summary', {})
        if mc_summary:
            prob_positive = mc_summary.get('prob_positive', 0)
            if prob_positive > 80:
                score += 10
                assessment['recommendations'].append("盈利概率高")
            elif prob_positive > 60:
                score += 5
                assessment['recommendations'].append("盈利概率中等")

        # 5. 综合评级
        assessment['robustness_score'] = score

        if score >= 80:
            assessment['strategy_strength'] = 'EXCELLENT'
            assessment['final_recommendation'] = "策略表现优秀，建议实盘交易"
        elif score >= 60:
            assessment['strategy_strength'] = 'GOOD'
            assessment['final_recommendation'] = "策略表现良好，可考虑实盘交易"
        elif score >= 40:
            assessment['strategy_strength'] = 'FAIR'
            assessment['final_recommendation'] = "策略表现中等，建议进一步优化"
        else:
            assessment['strategy_strength'] = 'POOR'
            assessment['final_recommendation'] = "策略表现不佳，不建议实盘交易"

        return assessment

    def _create_visualizations(self, wfo_result: Dict, yearly_result: Dict,
                             monte_carlo_result: Dict, base_result: Dict):
        """创建可视化图表"""
        # 1. WFO结果图
        if wfo_result and wfo_result.get('wfo_results'):
            self._plot_wfo_results(wfo_result['wfo_results'])

        # 2. 年度表现图
        if yearly_result and yearly_result.get('yearly_results'):
            self._plot_yearly_results(yearly_result['yearly_results'])

        # 3. 蒙特卡洛分布图
        if monte_carlo_result and monte_carlo_result.get('simulation_results'):
            self._plot_monte_carlo_results(monte_carlo_result)

    def _plot_wfo_results(self, wfo_results: List[Dict]):
        """绘制WFO结果"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

        folds = [r['fold'] for r in wfo_results]
        train_sharpes = [r['train_stats'].get('Sharpe', 0) for r in wfo_results]
        test_sharpes = [r['test_stats'].get('Sharpe', 0) for r in wfo_results]
        test_returns = [r['test_stats'].get('TotalReturn_pct', 0) for r in wfo_results]

        # Sharpe对比
        x = np.arange(len(folds))
        width = 0.35
        ax1.bar(x - width/2, train_sharpes, width, label='Training', alpha=0.7)
        ax1.bar(x + width/2, test_sharpes, width, label='Testing', alpha=0.7)
        ax1.set_xlabel('WFO Fold')
        ax1.set_ylabel('Sharpe Ratio')
        ax1.set_title('WFO: Training vs Testing Sharpe Ratio')
        ax1.set_xticks(x)
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 测试期收益
        ax2.bar(folds, test_returns, alpha=0.7, color='green')
        ax2.set_xlabel('WFO Fold')
        ax2.set_ylabel('Return (%)')
        ax2.set_title('WFO: Out-of-Sample Returns')
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'wfo_validation.png', dpi=150)
        plt.close()

    def _plot_yearly_results(self, yearly_results: List[Dict]):
        """绘制年度结果"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        years = [r['year'] for r in yearly_results]
        returns = [r['stats'].get('TotalReturn_pct', 0) for r in yearly_results]
        sharpes = [r['stats'].get('Sharpe', 0) for r in yearly_results]
        maxdds = [r['stats'].get('MaxDD_pct', 0) * 100 for r in yearly_results]
        trades = [r['stats'].get('Trades', 0) for r in yearly_results]

        # 年度收益
        colors = ['green' if r > 0 else 'red' for r in returns]
        ax1.bar(years, returns, color=colors, alpha=0.7)
        ax1.set_title('Yearly Returns')
        ax1.set_ylabel('Return (%)')
        ax1.grid(True, alpha=0.3)

        # 年度Sharpe
        ax2.bar(years, sharpes, alpha=0.7, color='blue')
        ax2.set_title('Yearly Sharpe Ratio')
        ax2.set_ylabel('Sharpe')
        ax2.grid(True, alpha=0.3)

        # 年度最大回撤
        ax3.bar(years, maxdds, alpha=0.7, color='red')
        ax3.set_title('Yearly Maximum Drawdown')
        ax3.set_ylabel('Drawdown (%)')
        ax3.grid(True, alpha=0.3)

        # 年度交易数
        ax4.bar(years, trades, alpha=0.7, color='orange')
        ax4.set_title('Yearly Trade Count')
        ax4.set_ylabel('Number of Trades')
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'yearly_validation.png', dpi=150)
        plt.close()

    def _plot_monte_carlo_results(self, monte_carlo_result: Dict):
        """绘制蒙特卡洛结果"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

        sim_results = monte_carlo_result['simulation_results']
        base_stats = monte_carlo_result['base_result']['stats']

        returns = [s['total_return'] for s in sim_results]
        max_dds = [s['max_dd'] for s in sim_results]
        sharpes = [s['sharpe'] for s in sim_results]
        final_equities = [s['final_equity'] for s in sim_results]

        # 收益分布
        ax1.hist(returns, bins=50, alpha=0.7, color='blue')
        ax1.axvline(base_stats.get('TotalReturn_pct', 0), color='red',
                   linestyle='--', label='Base Return')
        ax1.set_title('Monte Carlo: Return Distribution')
        ax1.set_xlabel('Total Return (%)')
        ax1.set_ylabel('Frequency')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 最大回撤分布
        ax2.hist(max_dds, bins=50, alpha=0.7, color='red')
        ax2.set_title('Monte Carlo: Max Drawdown Distribution')
        ax2.set_xlabel('Max Drawdown')
        ax2.set_ylabel('Frequency')
        ax2.grid(True, alpha=0.3)

        # 权益曲线百分位数
        equity_curves = [s['equity_curve'] for s in sim_results]
        max_len = max(len(curve) for curve in equity_curves)

        # 对齐权益曲线
        aligned_curves = []
        for curve in equity_curves:
            if len(curve) < max_len:
                # 填充到最后值
                padded = np.pad(curve, (0, max_len - len(curve)), 'edge')
                aligned_curves.append(padded)
            else:
                aligned_curves.append(curve)

        aligned_curves = np.array(aligned_curves)

        percentiles = [5, 25, 50, 75, 95]
        colors = ['red', 'orange', 'green', 'blue', 'purple']

        for p, color in zip(percentiles, colors):
            ax3.plot(np.percentile(aligned_curves, p, axis=0),
                    label=f'P{p}', color=color, alpha=0.7)

        ax3.set_title('Monte Carlo: Equity Curve Percentiles')
        ax3.set_xlabel('Trade Number')
        ax3.set_ylabel('Equity')
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        # 最终权益分布
        ax4.hist(final_equities, bins=50, alpha=0.7, color='green')
        ax4.axvline(base_stats.get('FinalEquity', 0), color='red',
                   linestyle='--', label='Base Final Equity')
        ax4.set_title('Monte Carlo: Final Equity Distribution')
        ax4.set_xlabel('Final Equity ($)')
        ax4.set_ylabel('Frequency')
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'monte_carlo_validation.png', dpi=150)
        plt.close()

    def _print_summary(self, report: Dict):
        """打印报告摘要"""
        print("\n" + "=" * 70)
        print("策略验证综合报告")
        print("=" * 70)

        # 基础表现
        base = report['base_backtest']
        print(f"\n【基础回测表现】")
        print(f"总收益: {base.get('TotalReturn_pct', 0):.2f}%")
        print(f"Sharpe: {base.get('Sharpe', 0):.3f}")
        print(f"最大回撤: {base.get('MaxDD_pct', 0)*100:.2f}%")
        print(f"交易数: {base.get('Trades', 0)}")
        print(f"胜率: {base.get('WinRate_pct', 0):.1f}%")

        # WFO验证
        wfo = report['wfo_validation']
        if wfo:
            print(f"\n【WFO验证结果】")
            print(f"样本外Sharpe: {wfo.get('avg_test_sharpe', 0):.3f}")
            print(f"样本内外比率: {wfo.get('out_of_sample_ratio', 0):.3f}")
            print(f"验证轮数: {wfo.get('fold_count', 0)}")

        # 年度验证
        yearly = report['yearly_validation']
        if yearly:
            print(f"\n【年度验证结果】")
            print(f"分析年数: {yearly.get('years_analyzed', 0)}")
            print(f"盈利年份占比: {yearly.get('win_rate_years', 0):.1f}%")
            print(f"平均年度收益: {yearly.get('avg_return', 0):.2f}%")
            print(f"最佳年份: {yearly.get('best_year', 0):.2f}%")
            print(f"最差年份: {yearly.get('worst_year', 0):.2f}%")

        # 蒙特卡洛验证
        mc = report['monte_carlo_validation']
        if mc:
            print(f"\n【蒙特卡洛验证结果】")
            print(f"盈利概率: {mc.get('prob_positive', 0):.1f}%")
            print(f"超越基准概率: {mc.get('prob_beat_base', 0):.1f}%")
            print(f"5%分位收益: {mc['percentiles_return'].get('p5', 0):.2f}%")
            print(f"95%分位收益: {mc['percentiles_return'].get('p95', 0):.2f}%")

        # 综合评估
        overall = report['overall_assessment']
        print(f"\n【综合评估】")
        print(f"稳健性得分: {overall.get('robustness_score', 0)}/100")
        print(f"策略评级: {overall.get('strategy_strength', 'UNKNOWN')}")
        print(f"建议: {overall.get('final_recommendation', '无')}")

        if overall.get('recommendations'):
            print(f"\n【关键发现】")
            for rec in overall['recommendations']:
                print(f"  • {rec}")

        print("=" * 70)
        print(f"详细报告已保存至: {self.output_dir}")


# ============================================================
# 5. 主程序
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='V8.5策略综合验证套件')
    parser.add_argument('--data_dir', default='./data', help='数据目录')
    parser.add_argument('--start', default=None, help='起始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', default=None, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--n_mc', type=int, default=500, help='蒙特卡洛模拟次数')
    parser.add_argument('--outdir', default=None, help='输出目录')

    args = parser.parse_args()

    # 导入数据加载器
    import sys
    sys.path.insert(0, args.data_dir)

    try:
        from universal_data_updater_5m import DataLoader5m
    except ImportError:
        print("错误: 找不到 universal_data_updater_5m.py")
        return

    # 加载数据
    print("加载数据...")
    loader = DataLoader5m(args.data_dir)

    try:
        df_5m, df_4h = loader.load_data(args.start, args.end)
    except FileNotFoundError as e:
        print(f"错误: {e}")
        return

    print(f"5m数据: {len(df_5m)} 根K线")
    print(f"4h数据: {len(df_4h)} 根K线")

    # 基础参数
    base_params = V85Params()

    # 输出目录
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    outdir = Path(args.outdir) if args.outdir else Path(args.data_dir) / f'v85_validation_{stamp}'

    # 初始化验证器
    wfo_validator = WFOValidator(WFOParams(), base_params)
    yearly_validator = YearlyValidator(base_params)
    mc_validator = MonteCarloValidator(base_params, args.n_mc)
    reporter = ValidationReporter(outdir)

    # 运行验证
    print(f"\n开始V8.5策略综合验证...")
    print(f"输出目录: {outdir}")

    # 1. 基础回测
    print(f"\n{'='*50}")
    print("1/4: 基础回测")
    print(f"{'='*50}")
    base_engine = IntrabarBacktestEngine(base_params, use_intrabar_stop=True)
    base_result = base_engine.run(df_5m, df_4h)

    # 2. WFO验证
    print(f"\n{'='*50}")
    print("2/4: WFO验证")
    print(f"{'='*50}")
    wfo_result = wfo_validator.run_wfo(df_5m, df_4h)

    # 3. 年度验证
    print(f"\n{'='*50}")
    print("3/4: 年度验证")
    print(f"{'='*50}")
    yearly_result = yearly_validator.run_yearly_validation(df_5m, df_4h)

    # 4. 蒙特卡洛验证
    print(f"\n{'='*50}")
    print("4/4: 蒙特卡洛验证")
    print(f"{'='*50}")
    monte_carlo_result = mc_validator.run_monte_carlo(df_5m, df_4h)

    # 5. 生成报告
    print(f"\n{'='*50}")
    print("生成综合报告")
    print(f"{'='*50}")
    report = reporter.generate_comprehensive_report(
        wfo_result, yearly_result, monte_carlo_result, base_result
    )

    print(f"\n验证完成! 结果保存至: {outdir}")


if __name__ == "__main__":
    main()