# Mainline Live Status

- Time: `2026-03-07 16:00:00+00:00`
- State: `core_full_s1_0_s2_0`
- Portfolio state: `Core-Only`
- Risk-Off active: `False`

## Target Exposure

- Core = `1.00`
- Sleeve1 = `0.00`
- Sleeve2 = `0.00`
- Total = `1.00`
- Headroom to 3.0x cap = `2.00x`
- ATR scale = `1.00x`
- HV percentile = `92.0`
- Core gate = `weekly_rsi30_hold` / instability `highly_unstable` via `hv_force`

## Target Notional

- Account equity = `100000.00 USDT`
- Core target notional = `100000.00 USDT`
- Sleeve1 target notional = `0.00 USDT`
- Sleeve2 target notional = `0.00 USDT`
- Total target notional = `100000.00 USDT`

## Rebalance Instruction

- Current actual notional = `100000.00 USDT`
- Target notional = `100000.00 USDT`
- Delta = `0.00 USDT`
- Action = `HOLD`
- Suggested order = `No trade`

## Operating Memo

- Suggestion: `持有核心主姿态，继续观察 sleeves 是否重新激活`
- Governance alert: `Observe`
- Current drawdown: `-17.82%`
- Days since equity high: `236.5`
- Trailing 3m cluster loss: `-16.13%`
- Trailing 6m cluster loss: `-15.63%`

## Scheduling

- Recommended run frequency: `every 4h bar close`.
- ATR sleeve scaling, HV-forced high-churn qualification, and weekly override are already captured by the same 4h refresh cycle.