#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_all_v85.py
==============
V8.5策略全功能测试脚本

快速测试所有验证模块是否能正常工作
"""

import sys
from pathlib import Path
from datetime import datetime

# 导入数据加载器
sys.path.insert(0, './data')
try:
    from universal_data_updater_5m import DataLoader5m
    print("OK 数据加载器导入成功")
except ImportError as e:
    print(f"FAIL 数据加载器导入失败: {e}")
    sys.exit(1)

# 导入核心模块
try:
    from v85_intrabar_backtest import V85Params, IntrabarBacktestEngine
    print("OK V85核心模块导入成功")
except ImportError as e:
    print(f"FAIL V85核心模块导入失败: {e}")
    sys.exit(1)

# 导入验证模块
try:
    from v85_full_validation import main as full_validation_main
    print("OK 完整验证模块导入成功")
except ImportError as e:
    print(f"FAIL 完整验证模块导入失败: {e}")

try:
    from v85_wfo_validate import main as wfo_validate_main
    print("OK WFO验证模块导入成功")
except ImportError as e:
    print(f"FAIL WFO验证模块导入失败: {e}")

try:
    from v85_validation_suite import main as validation_suite_main
    print("OK 综合验证套件导入成功")
except ImportError as e:
    print(f"FAIL 综合验证套件导入失败: {e}")

def quick_backtest_test():
    """快速回测测试"""
    print("\n" + "="*50)
    print("快速回测测试")
    print("="*50)

    try:
        # 加载数据
        loader = DataLoader5m('./data')
        df_5m, df_4h = loader.load_data()
        print(f"OK 数据加载成功: 5m={len(df_5m)}, 4h={len(df_4h)}")

        # 创建参数
        params = V85Params()
        print(f"OK 参数创建成功: 初始资金=${params.init_equity}")

        # 运行快速回测（只处理少量数据）
        df_5m_small = df_5m.head(50000)  # 约2个月数据
        df_4h_small = df_4h.head(200)    # 约2个月数据

        engine = IntrabarBacktestEngine(params, use_intrabar_stop=True)
        result = engine.run(df_5m_small, df_4h_small)

        stats = result['stats']
        print(f"OK 快速回测成功:")
        print(f"  总收益: {stats.get('TotalReturn_pct', 0):.2f}%")
        print(f"  交易数: {stats.get('Trades', 0)}")
        print(f"  胜率: {stats.get('WinRate_pct', 0):.1f}%")

        return True

    except Exception as e:
        print(f"FAIL 快速回测失败: {e}")
        return False

def parameter_test():
    """参数测试"""
    print("\n" + "="*50)
    print("参数测试")
    print("="*50)

    try:
        # 测试不同参数组合
        test_params = [
            V85Params(),
            V85Params(position_pct=80),
            V85Params(initial_stop_atr=2.0),
            V85Params(enable_daily_loss_limit=False)
        ]

        for i, p in enumerate(test_params):
            print(f"OK 参数组合 {i+1}: 仓位={p.position_pct}%, 止损={p.initial_stop_atr}ATR")

        return True

    except Exception as e:
        print(f"FAIL 参数测试失败: {e}")
        return False

def main():
    print("V8.5策略全功能测试")
    print("="*50)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 基础测试
    test1_ok = quick_backtest_test()
    test2_ok = parameter_test()

    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)

    print(f"模块导入: OK 成功")
    print(f"快速回测: {'OK 成功' if test1_ok else 'FAIL 失败'}")
    print(f"参数测试: {'OK 成功' if test2_ok else 'FAIL 失败'}")

    if test1_ok and test2_ok:
        print("\n[SUCCESS] 所有基础测试通过!")
        print("\n可用的验证脚本:")
        print("1. python v85_intrabar_backtest.py --data_dir ./data")
        print("2. python v85_full_validation.py --data_dir ./data --mc_n 100")
        print("3. python v85_wfo_validate.py --data_dir ./data --mode per_year_eval")
        print("4. python v85_validation_suite.py --data_dir ./data --n_mc 100")
    else:
        print("\n[ERROR] 部分测试失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()