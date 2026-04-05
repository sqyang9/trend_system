# Mainline Live Status

- Time: `2026-03-29 12:00:00+00:00`
- State: `core_flat_s1_0_s2_0`
- Portfolio state: `Core-Only`
- Risk-Off active: `True`

## Target Exposure

- Core = `0.00`
- Sleeve1 = `0.00`
- Sleeve2 = `0.00`
- Total = `0.00`
- Headroom to 3.0x cap = `3.00x`
- ATR scale = `1.25x`
- ATR scales = `S1 1.25x / S2 1.36x`
- ATRVT contract = `ATRVT_90D_med_035_150__ATRVT_60D_med_035_150`
- ATRVT detail = `S1 90d / median / 0.35-1.50; S2 60d / median / 0.35-1.50`
- S1 gate contract = `S1_VP_LB60_EA050_VR120`
- S1 gate latest = `candidate=False / pass=False / reason=not_applicable`
- HV percentile = `35.4`
- Core gate = `baseline_close3` / instability `highly_unstable` via `flips`

## Target Notional

- Account equity = `100000.00 USDT`
- Core target notional = `0.00 USDT`
- Sleeve1 target notional = `0.00 USDT`
- Sleeve2 target notional = `0.00 USDT`
- Total target notional = `0.00 USDT`

## Rebalance Instruction

- Current actual notional = `100000.00 USDT`
- Target notional = `0.00 USDT`
- Delta = `-100000.00 USDT`
- Action = `REDUCE`
- Suggested order = `REDUCE 100000.00 USDT BTCUSDT perpetual`

## Operating Memo

- Suggestion: `持有核心主姿态，继续观察 sleeves 是否重新激活`
- Governance alert: `Observe`
- Current drawdown: `-14.86%`
- Days since equity high: `258.3`
- Trailing 3m cluster loss: `-16.68%`
- Trailing 6m cluster loss: `-16.14%`

## Scheduling

- Recommended run frequency: `every 4h bar close`.
- ATR sleeve scaling, HV-forced high-churn qualification, and weekly override are already captured by the same 4h refresh cycle.