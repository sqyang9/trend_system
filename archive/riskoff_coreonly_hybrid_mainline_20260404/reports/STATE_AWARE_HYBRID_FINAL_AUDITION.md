# State-Aware Hybrid Final Audition

## Scope

- Mainline reference: `baseline close3`.
- Standing reference: `state-aware strict`.
- Challenger: `high churn -> strict AND breakout_4`.
- Sell-side and `weekly_rsi30_hold` stay fixed.
- Adoption framing: compare the challenger against both the mainline and the standing reference across `default`, `stress`, and `harsh_friction`.

## Default

| System | Return% | CAGR% | Sharpe | Calmar | MaxDD% | RecoveryDays | Worst3m | Worst6m | AvgTotalExp% | AvgCoreExp% | RiskOffActive% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mainline baseline close3 | 2329.48 | 66.95 | 1.228 | 2.129 | -31.45 | 19.7 | -15.48 | -17.12 | 88.63 | 45.50 | 39.56 |
| Reference: high churn -> strict EMA50 | 2237.77 | 65.92 | 1.227 | 2.258 | -29.20 | 61.7 | -16.45 | -20.34 | 86.10 | 42.97 | 42.87 |
| Challenger: high churn -> strict AND breakout (4 bars) | 2459.02 | 68.35 | 1.255 | 2.352 | -29.06 | 19.3 | -16.25 | -16.47 | 85.06 | 41.93 | 44.25 |

## Stress / Harsh Delta Vs Mainline

| Scenario | dReturn | dCalmar | dMaxDD |
| --- | --- | --- | --- |
| Default | +129.55pp | +0.223 | +2.39pp |
| Stress | +111.91pp | +0.248 | +2.68pp |
| Harsh friction | +164.69pp | +0.245 | +2.86pp |

## Default Churn Audit

| System | Full RE | RE->next FLAT Median Days | Quick re-FLAT 14d | Quick re-FLAT 30d | High-Churn RE | High-Churn Median Days | High-Churn Quick 14d | High-Churn Quick 30d |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mainline baseline close3 | 57 | 9.6 | 59.6% | 73.7% | 41 | 8.2 | 58.5% | 75.6% |
| Reference: high churn -> strict EMA50 | 40 | 19.0 | 47.5% | 62.5% | 24 | 20.8 | 37.5% | 58.3% |
| Challenger: high churn -> strict AND breakout (4 bars) | 38 | 19.0 | 44.7% | 60.5% | 22 | 21.7 | 31.8% | 54.5% |

## Recent Windows

### Mainline baseline close3

- 2024-12_to_2025-06: short 14d / 30d = `5` / `6`, high-churn short 14d / 30d = `3` / `4`
- 2025-06_to_2025-12: short 14d / 30d = `6` / `6`, high-churn short 14d / 30d = `5` / `5`

### Reference: high churn -> strict EMA50

- 2024-12_to_2025-06: short 14d / 30d = `2` / `3`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `3` / `3`, high-churn short 14d / 30d = `2` / `2`

### Challenger: high churn -> strict AND breakout (4 bars)

- 2024-12_to_2025-06: short 14d / 30d = `2` / `3`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `3` / `3`, high-churn short 14d / 30d = `2` / `2`

## Annual Starts

| Start | dReturn vs Mainline | dCalmar vs Mainline | dMaxDD vs Mainline | dReturn vs Strict | dCalmar vs Strict | dMaxDD vs Strict |
| --- | --- | --- | --- | --- | --- | --- |
| 2020-01-01 | +132.79pp | +0.227 | +2.39pp | +226.79pp | +0.096 | +0.14pp |
| 2021-01-01 | +11.29pp | +0.369 | +8.02pp | +38.33pp | +0.355 | +5.85pp |
| 2022-01-01 | +11.39pp | +0.152 | +2.53pp | +23.90pp | +0.231 | +3.08pp |
| 2023-01-01 | -18.05pp | +0.043 | +2.53pp | +6.24pp | +0.219 | +3.08pp |
| 2024-01-01 | -1.67pp | +0.104 | +2.53pp | +2.16pp | +0.177 | +3.08pp |
| 2025-01-01 | -0.83pp | -0.027 | +0.64pp | -2.54pp | -0.121 | -1.46pp |
| 2026-01-01 | +0.01pp | +0.029 | -0.21pp | -0.59pp | -0.213 | -0.38pp |

## Readout

- Standing reference: Return `2237.77%`, Calmar `2.258`, MaxDD `-29.20%`.
- Challenger: Return `2459.02%`, Calmar `2.352`, MaxDD `-29.06%`.
- Challenger vs standing reference in default: dReturn `+221.25pp`, dCalmar `+0.094`, dMaxDD `+0.14pp`.
- Annual starts where challenger improves Calmar vs mainline: `6` / `7`.
- Annual starts where challenger improves MaxDD vs mainline: `6` / `7`.
- Annual starts where challenger improves Calmar vs strict: `5` / `7`.
- Annual starts where challenger improves MaxDD vs strict: `5` / `7`.
- Promotion bar: the challenger should not only reduce churn, but also survive default / stress / harsh and keep that advantage credible across annual start offsets.