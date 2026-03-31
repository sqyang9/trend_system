# Risk-Off Re-Entry Top-2 Promotion Audit

## Scope

- Locked sell-side Risk-Off logic remains unchanged.
- Only two low-value re-entry candidates are audited:
  - `RO_LOWVALUE_WEEKLY_RSI30_HOLD`
  - `RO_LOWVALUE_4H_RSI10_HOLD`
- Current formal portfolio is included as reference only.

## Default Full-Sample Table

| System | Return% | CAGR% | Sharpe | Calmar | MaxDD% | MaxDD Duration(d) | Avg Core / Total Exposure% | RiskOff Active% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 860.94 | 43.84 | 0.751 | 0.569 | -77.04 | 850.5 | 100.0 | 0.0 |
| Formal Portfolio | 1591.16 | 57.51 | 0.986 | 1.008 | -57.08 | 841.0 | 136.8 | n/a |
| RO_EMA220_REENTRY_CLOSE_HOLD_3 | 1821.45 | 60.78 | 1.106 | 1.034 | -58.78 | 839.5 | 58.0 | 42.2 |
| RO_LOWVALUE_WEEKLY_RSI30_HOLD | 2408.33 | 67.82 | 1.165 | 1.431 | -47.38 | 753.7 | 60.5 | 39.7 |
| RO_LOWVALUE_4H_RSI10_HOLD | 2489.61 | 68.68 | 1.184 | 1.212 | -56.67 | 745.3 | 61.1 | 39.2 |

## Promotion Comparison Vs Archived Best

| Candidate | Strict OOS | Avg dReturn | Avg dCalmar | Bull dReturn | Recovery dReturn | Major Drawdown dMaxDD | Vs Old dReturn | Vs Old dCalmar | Vs Old dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RO_LOWVALUE_WEEKLY_RSI30_HOLD | 0.67 | -9.86pp | -0.033 | -181.72pp | -57.08pp | +25.54pp | +1.21pp | +0.018 | +11.49pp |
| RO_LOWVALUE_4H_RSI10_HOLD | 0.67 | +3.87pp | +0.518 | -181.72pp | +8.25pp | +15.98pp | +14.94pp | +0.570 | +1.93pp |

## Execution Robustness

| Candidate | Stress dReturn vs Old | Stress dCalmar vs Old | Stress dMaxDD vs Old |
| --- | --- | --- | --- |
| RO_LOWVALUE_WEEKLY_RSI30_HOLD | +609.52pp | +0.405 | +11.21pp |
| RO_LOWVALUE_4H_RSI10_HOLD | +717.24pp | +0.184 | +2.16pp |

## Path Burden

| System | Worst 3m Cluster% | Worst 6m Cluster% | Rolling 180d Worst MaxDD% | Rolling 365d Worst Return% | Longest Neg Month Streak |
| --- | --- | --- | --- | --- | --- |
| Formal Portfolio | -39.91 | -44.55 | -45.48 | -55.98 | 5 |
| RO_EMA220_REENTRY_CLOSE_HOLD_3 | -28.58 | -49.69 | -41.29 | -56.01 | 6 |
| RO_LOWVALUE_WEEKLY_RSI30_HOLD | -21.67 | -33.86 | -40.11 | -43.73 | 5 |
| RO_LOWVALUE_4H_RSI10_HOLD | -28.58 | -41.00 | -38.28 | -55.12 | 6 |

## Vs Current Formal Portfolio Reference

| Candidate | dReturn vs Formal | dCalmar vs Formal | dMaxDD vs Formal |
| --- | --- | --- | --- |
| RO_LOWVALUE_WEEKLY_RSI30_HOLD | +817.17pp | +0.424 | +9.70pp |
| RO_LOWVALUE_4H_RSI10_HOLD | +898.45pp | +0.204 | +0.41pp |

## Plot

- HTML: `RISK_OFF_REENTRY_TOP2_PROMOTION_PLOTS.html`