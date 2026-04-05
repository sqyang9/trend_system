# State-Aware Hybrid Qualification Audit

## Scope

- Mainline reference: `baseline close3`.
- Keep `state-aware strict` as the standing strongest challenger and reference group.
- Only test high-churn hybrid qualifications:
  `strict AND breakout_4`
  `strict OR breakout_4`
- Sell-side and `weekly_rsi30_hold` stay fixed.
- Audit focus: `default / stress / harsh_friction`, high-churn churn metrics, recent two windows, and whether FULL RE count gets over-compressed.

## Default

| System | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline close3 | 2329.48 | 2.129 | -31.45 | -15.48 | -17.12 | 19.7 |
| State-aware: high churn -> strict EMA50 | 2237.77 | 2.258 | -29.20 | -16.45 | -20.34 | 61.7 |
| State-aware: high churn -> strict AND breakout (4 bars) | 2459.02 | 2.352 | -29.06 | -16.25 | -16.47 | 19.3 |
| State-aware: high churn -> strict OR breakout (4 bars) | 2169.69 | 2.044 | -31.87 | -15.85 | -18.37 | 303.7 |

## Stress / Harsh Delta Vs Mainline

| Candidate | Default dReturn | Default dCalmar | Default dMaxDD | Stress dReturn | Stress dCalmar | Stress dMaxDD | Harsh dReturn | Harsh dCalmar | Harsh dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| State-aware: high churn -> strict EMA50 | -91.70pp | +0.129 | +2.25pp | -119.58pp | +0.136 | +2.37pp | -54.98pp | +0.145 | +2.65pp |
| State-aware: high churn -> strict AND breakout (4 bars) | +129.55pp | +0.223 | +2.39pp | +111.91pp | +0.248 | +2.68pp | +164.69pp | +0.245 | +2.86pp |
| State-aware: high churn -> strict OR breakout (4 bars) | -159.78pp | -0.085 | -0.42pp | -142.41pp | -0.069 | -0.29pp | -95.63pp | -0.051 | -0.28pp |

## Default Churn Audit

| System | FULL RE | RE->next FLAT Median Days | Quick re-FLAT 14d | Quick re-FLAT 30d | High-Churn FULL RE | High-Churn Median Days | High-Churn Quick 14d | High-Churn Quick 30d |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline close3 | 57 | 9.6 | 59.6% | 73.7% | 41 | 8.2 | 58.5% | 75.6% |
| State-aware: high churn -> strict EMA50 | 40 | 19.0 | 47.5% | 62.5% | 24 | 20.8 | 37.5% | 58.3% |
| State-aware: high churn -> strict AND breakout (4 bars) | 38 | 19.0 | 44.7% | 60.5% | 22 | 21.7 | 31.8% | 54.5% |
| State-aware: high churn -> strict OR breakout (4 bars) | 47 | 13.2 | 53.2% | 68.1% | 31 | 14.2 | 48.4% | 67.7% |

## Recent Windows

### Baseline close3

- 2024-12_to_2025-06: short 14d / 30d = `5` / `6`, high-churn short 14d / 30d = `3` / `4`
- 2025-06_to_2025-12: short 14d / 30d = `6` / `6`, high-churn short 14d / 30d = `5` / `5`

### State-aware: high churn -> strict EMA50

- 2024-12_to_2025-06: short 14d / 30d = `2` / `3`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `3` / `3`, high-churn short 14d / 30d = `2` / `2`

### State-aware: high churn -> strict AND breakout (4 bars)

- 2024-12_to_2025-06: short 14d / 30d = `2` / `3`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `3` / `3`, high-churn short 14d / 30d = `2` / `2`

### State-aware: high churn -> strict OR breakout (4 bars)

- 2024-12_to_2025-06: short 14d / 30d = `3` / `4`, high-churn short 14d / 30d = `1` / `2`
- 2025-06_to_2025-12: short 14d / 30d = `4` / `4`, high-churn short 14d / 30d = `3` / `3`

## Readout

- Standing challenger remains `state-aware strict`: Return `2237.77%`, Calmar `2.258`, MaxDD `-29.20%`.
- `Strict AND breakout_4` vs standing challenger: dReturn `+221.25pp`, dCalmar `+0.094`, dMaxDD `+0.14pp`.
- `Strict OR breakout_4` vs standing challenger: dReturn `-68.08pp`, dCalmar `-0.214`, dMaxDD `-2.67pp`.
- Promotion bar here is stricter than just reducing churn: the hybrid should survive default / stress / harsh without over-compressing FULL RE count and without losing too much total-return efficiency.