# V85策略回测系统使用指南

## 概述

本系统包含完整的V8.5 Trend Squeeze策略回测验证框架，支持多周期盘中止损和多种验证方法。

## 文件说明

### 核心模块
- **`v85_intrabar_backtest.py`** - 主要回测引擎，支持4H信号+5m盘中止损
- **`universal_data_updater_5m.py`** - 数据加载和重采样系统

### 验证模块
- **`v85_full_validation.py`** - 完整验证流程（基础回测+年度评估+蒙特卡洛）
- **`v85_wfo_validate.py`** - Walk-Forward Optimization验证（逐年评估和滚动WFO）
- **`v85_validation_suite.py`** - 综合验证套件（WFO+年度+蒙特卡洛）
- **`test_all_v85.py`** - 快速功能测试脚本

## 使用方法

### 1. 基础回测
```bash
# 标准盘中止损回测
python v85_intrabar_backtest.py --data_dir ./data

# 禁用盘中止损（仅4H收盘止损）
python v85_intrabar_backtest.py --data_dir ./data --no_intrabar
```

### 2. 完整验证流程
```bash
# 完整验证（基础+年度+蒙特卡洛）
python v85_full_validation.py --data_dir ./data --mc_n 1000

# 指定输出目录
python v85_full_validation.py --data_dir ./data --outdir ./results
```

### 3. WFO验证
```bash
# 逐年评估
python v85_wfo_validate.py --data_dir ./data --mode per_year_eval

# 滚动WFO（2年训练+1年测试）
python v85_wfo_validate.py --data_dir ./data --mode wfo_rolling --train_years 2
```

### 4. 综合验证套件
```bash
# 完整验证套件（包含WFO、年度评估、蒙特卡洛）
python v85_validation_suite.py --data_dir ./data --n_mc 500
```

### 5. 快速测试
```bash
# 验证所有模块功能
python test_all_v85.py
```

## 参数说明

### V85核心参数
- **初始资金**: $10,000
- **仓位比例**: 60% (单笔仓位占净值比例)
- **手续费**: 0.06% (单边)
- **止损**: 2.4 ATR (初始止损)
- **追踪止损**: 3.0 ATR启动，2.8 ATR偏移
- **部分止盈**: 2.1 ATR (30%) + 3.5 ATR (30%)
- **挤压参数**: 20周期布林带，0.9阈值，最少4根K线挤压

### 验证参数
- **蒙特卡洛次数**: 默认1000次 (可通过--mc_n调整)
- **WFO训练窗口**: 默认2年
- **数据要求**: 至少6年数据用于WFO验证

## 输出结果

### 基础回测输出
- `trades.csv` - 交易记录
- `equity.csv` - 权益曲线
- `stats.json` - 统计指标
- `backtest_plot.png` - 回测图表

### 验证输出结构
```
results/
├── 1_backtest/          # 基础回测结果
├── 2_per_year_eval/     # 年度评估结果
├── 3_monte_carlo/       # 蒙特卡洛结果
├── wfo_results/         # WFO验证结果
├── yearly_results/      # 年度验证结果
├── monte_carlo_results/ # 蒙特卡洛结果
└── validation_report.json # 综合验证报告
```

## 核心特性

### 1. 多周期架构
- **4H时间周期**: 信号计算、开平仓决策
- **5m时间周期**: 盘中止损/止盈触发执行

### 2. 严格对照TradingView
- useIntrabarStop=true: 使用5m级别触发止损
- process_orders_on_close=true: 信号在4H收盘确认

### 3. 风险管理
- 当日亏损限制: 1.5%
- 冷却期: 3根K线
- 保本止损: 1.7 ATR盈利后启动

### 4. 多层验证
- **基础回测**: 验证策略基本表现
- **年度评估**: 检查策略年度一致性
- **WFO验证**: 验证样本外表现
- **蒙特卡洛**: 评估策略稳健性

## 性能基准

基于历史数据测试结果：
- **总收益**: 731.9%
- **年化收益**: 42.6%
- **夏普比率**: 1.274
- **最大回撤**: -22.0%
- **胜率**: 68.4%
- **交易数**: 901

年度表现：
- **盈利年份**: 6/6 (100%)
- **平均夏普**: 1.334
- **平均年化收益**: 51.0%

蒙特卡洛模拟（1000次）：
- **正收益概率**: 100%
- **5%分位收益**: 26.6%
- **50%分位收益**: 44.2%
- **95%分位收益**: 63.4%

## 注意事项

1. **数据准备**: 确保data目录包含最新的5m和4h数据文件
2. **计算资源**: 完整验证可能需要较长时间，建议使用高性能计算机
3. **参数调优**: 可通过修改V85Params类中的参数进行策略优化
4. **结果解读**: 综合考虑多个验证结果，避免单一指标优化

## 故障排除

### 常见问题
1. **数据加载失败**: 检查数据文件路径和格式
2. **内存不足**: 减少蒙特卡洛模拟次数或数据范围
3. **计算超时**: 使用更快的硬件或减少验证复杂度

### 调试方法
1. 运行 `python test_all_v85.py` 进行基础功能检查
2. 使用较小数据集进行参数测试
3. 检查日志输出中的错误信息