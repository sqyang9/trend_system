# Risk-Off Final Promotion Audit

## Scope

- Final decision round for the reopened Risk-Off core re-entry line.
- Decision set is fixed to:
  - `RO_EMA220_REENTRY_CLOSE_HOLD_3`
  - `RO_LOWVALUE_WEEKLY_RSI30_HOLD`
  - `RO_LOWVALUE_4H_RSI10_HOLD`
- Current formal portfolio remains reference-only in this round.

## Default Full-Sample Comparison

| System | Return% | CAGR% | Sharpe | Calmar | MaxDD% | DD Duration(d) | Avg Core / Total Exposure% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Formal Portfolio | 1591.16 | 57.51 | 0.986 | 1.008 | -57.08 | 841.0 | 136.8 |
| RO_EMA220_REENTRY_CLOSE_HOLD_3 | 1821.45 | 60.78 | 1.106 | 1.034 | -58.78 | 839.5 | 58.0 |
| RO_LOWVALUE_WEEKLY_RSI30_HOLD | 2408.33 | 67.82 | 1.165 | 1.431 | -47.38 | 753.7 | 60.5 |
| RO_LOWVALUE_4H_RSI10_HOLD | 2489.61 | 68.68 | 1.184 | 1.212 | -56.67 | 745.3 | 61.1 |

## Promotion Lens Vs Archived Best

| Candidate | Strict OOS | Avg dReturn | Avg dCalmar | Recovery dReturn | Major Drawdown dMaxDD | Stress dReturn vs Old | Stress dCalmar vs Old |
| --- | --- | --- | --- | --- | --- | --- | --- |
| RO_LOWVALUE_WEEKLY_RSI30_HOLD | 0.67 | -9.86pp | -0.033 | -57.08pp | +25.54pp | +609.52pp | +0.405 |
| RO_LOWVALUE_4H_RSI10_HOLD | 0.67 | +3.87pp | +0.518 | +8.25pp | +15.98pp | +717.24pp | +0.184 |

## Vs Current Formal Portfolio

| Candidate | dReturn vs Formal | dCalmar vs Formal | dMaxDD vs Formal |
| --- | --- | --- | --- |
| RO_LOWVALUE_WEEKLY_RSI30_HOLD | +817.17pp | +0.424 | +9.70pp |
| RO_LOWVALUE_4H_RSI10_HOLD | +898.45pp | +0.204 | +0.41pp |

## Final Read

- `RO_LOWVALUE_WEEKLY_RSI30_HOLD` is the strongest all-around successor: it beats `RO_EMA220_REENTRY_CLOSE_HOLD_3` on return, calmar, drawdown, path burden, and stress robustness.
- `RO_LOWVALUE_4H_RSI10_HOLD` also clears the replacement bar against `RO_EMA220_REENTRY_CLOSE_HOLD_3`, but it is the more aggressive variant: higher return than `RO_LOWVALUE_WEEKLY_RSI30_HOLD`, weaker calmar and shallower protection gain.
- Both candidates also beat the current formal portfolio on default full-sample return and calmar.

- Plot: `RISK_OFF_FINAL_PROMOTION_PLOTS.html`