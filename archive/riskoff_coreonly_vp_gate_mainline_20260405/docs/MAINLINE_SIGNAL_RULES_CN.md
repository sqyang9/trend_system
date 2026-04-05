# Mainline 图上标记说明

当前 adopted mainline：

- `Core = 1.00`
- `Sleeve #1 = 1.00`
- `Sleeve #2 = 1.00`
- `S1 ATRVT = 90d median / 0.35-1.50`
- `S2 ATRVT = 60d median / 0.35-1.50`
- `Risk-Off sell-side = EMA250`
- `stable re-entry = close3`
- `high-churn re-entry = strict EMA50 + breakout_4`
- `HV percentile >= 85` 会更早强制切到 high-churn gate
- `override re-entry = Weekly RSI(14) <= 30 hold`
- `S1 gate = VP_LB60_EA050_VR120`

## Core: IN / FLAT / RE

### Core IN

- 含义：`core_target > 0`
- 运行上分两档：
  - `full = 1.0 unit`，组合映射成 `Core = 1.00`
  - `soft_off = 0.5 unit`，组合映射成 `Core = 0.50`

### Core FLAT

触发逻辑：

- `4h close < EMA250`
- 且 `EMA250 slope < 0`
- 连续确认 2 根 `4h bar`

状态机：

1. 第 1 根 bearish 确认：`full -> soft_off`
2. 第 2 根 bearish 确认：`soft_off -> flat`

图上 `FLAT` 标记的意思：

- `core_target` 从 `>0` 变成 `0` 的那根 bar

### Core RE

图上 `RE` 标记的意思：

- `core_target` 从 `0` 重新变成 `>0`

Core 回场有两条路：

1. `Weekly RSI30 hold override`
- Core 已经 flat
- 已完成周线 `RSI(14) <= 30`
- 立即恢复到 `override_hold / full`

2. `正常恢复`
- Core 已经 flat
- `4h close > EMA250` 连续 3 根
- 若环境稳定，直接恢复到 `normal / full`
- 若环境处于高 churn：
  - 先要求 `EMA50 > EMA250`
  - 且 `EMA50 slope > 0`
  - 再在 4 根 `4h bar` 内突破 `close3` 触发 bar 高点
  - 通过后才恢复到 `normal / full`

一句话：

- `FLAT` = EMA250 bearish deterioration 连续确认后把 Core 清掉
- `RE` = Core 清掉后重新回场；在高 churn 环境里，`close3` 只是恢复资格起点，不再自动 full

## S1B / S1S

`Sleeve #1` 本质是：

- `squeeze_release_20`
- breakout / expansion sleeve

### S1B

同时满足这些条件才开：

- `close > EMA200`
- `EMA200 slope > 0`
- `ADX(14) >= 10`
- `close > 20-bar donchian high`
- 之前已经有连续 `>= 6` 根 squeeze
- `close_location >= 0.60`
- `bar_range / ATR >= 0.55`
- `volume >= SMA20(volume)`
- `S1 volume-profile proxy gate` 通过：
  - 最近 `60` 根里，当前突破价格相对近端高值节点至少逃离 `0.50 ATR`
  - 且 `volume / SMA20(volume) >= 1.20`

图上 `S1B`：

- `Sleeve #1` 从空变成 active 的那根 bar

### S1X

图上 `S1X`：

- 原始 breakout 候选已经出现
- 但被 `volume-profile proxy gate` 拦下

它的意思不是反手，只表示：

- breakout 本身出现了
- 但没有通过“脱离近端筹码密集区 + 量能确认”这道额外门

### S1S

退出不是反手信号，而是止损 / trailing stop：

- 初始止损大致是：
  - `entry - 3.2 * ATR`
  - 再结合 `20-bar structure low`
- 浮盈达到约 `2.5 ATR` 后，启动 trailing：
  - `highest_high - 5.0 * ATR`
- 价格跌破 stop，就退出

图上 `S1S`：

- `Sleeve #1` 从 active 变回 0 的那根 bar

一句话：

- `S1B` = bullish breakout + squeeze release + quality filter + VP proxy gate 通过
- `S1X` = breakout 候选出现，但被 VP proxy gate 拦掉
- `S1S` = 被初始止损或 trailing stop 打掉

## S2B / S2S

`Sleeve #2` 本质是：

- `RangeRotation`
- lower-range reclaim / rotation sleeve

### S2B

先要满足背景：

- 最近 6 根里出现过 lower rotation touch

然后当前 bar 同时满足：

- `close > reclaim_high_2`
- `close > EMA20`
- `close >= range_mid_20`
- `close_location >= 0.55`
- `close <= upper_rotation_cap`
- `close > EMA200`
- `EMA50 >= EMA200`
- `EMA slope / ATR > -0.08`
- `range_width / ATR` 在 `2.5 ~ 7.5`
- `ADX <= 28`
- `bb_width_norm <= 1.15`

图上 `S2B`：

- `Sleeve #2` 从空变成 active 的那根 bar

### S2S

退出逻辑：

- 初始止损大致是：
  - `entry - 2.2 * ATR`
  - 再结合 `5-bar rotation pivot low`
- 浮盈达到约 `1.4 ATR` 后，启动 trailing：
  - `highest_high - 3.6 * ATR`
- 同时用 `8-bar swing low` 做 swing trail
- 跌破 stop，就退出

图上 `S2S`：

- `Sleeve #2` 从 active 变回 0 的那根 bar

一句话：

- `S2B` = lower-range touch 后的 reclaim / rotation entry
- `S2S` = 被 rotation stop 或 trailing swing stop 打掉

## 一页理解

图上的 6 类标记，分别对应：

- `FLAT`：Core 退场
- `RE`：Core 回场
- `S1B`：Sleeve #1 开
- `S1S`：Sleeve #1 平
- `S2B`：Sleeve #2 开
- `S2S`：Sleeve #2 平

最简理解：

- `Core` 管大级别在不在场
- `S1` 管 breakout / expansion，但要额外确认价格真正脱离近端筹码密集区
- `S2` 管 range rotation / chop
