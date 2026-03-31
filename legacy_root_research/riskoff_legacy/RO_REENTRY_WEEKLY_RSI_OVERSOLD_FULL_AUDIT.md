# RO_REENTRY_WEEKLY_RSI_OVERSOLD_FULL Audit

## Scope

- This round tests only `RO_REENTRY_WEEKLY_RSI_OVERSOLD_FULL`.
- Bear-side de-risking stays locked to the archived `EMA220 two-stage` deterioration logic.
- The candidate keeps `RO_EMA220_REENTRY_CLOSE_HOLD_3` unchanged and adds one early re-entry override.
- The only added rule is: if state is flat, weekly RSI(14) oversold may restore core to 100% before the 3-close condition completes.

## Candidate Summary

| Scheme | Strict OOS | Avg dReturn | Avg dSharpe | Avg dCalmar | Bull dReturn | Recovery dReturn | Major Drawdown dMaxDD | Avg Flat Upside Drag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RO_EMA220_FLAT | 0.33 | -19.29pp | -0.139 | -0.767 | -233.07pp | -77.59pp | +20.26pp | 233618.10 |
| RO_EMA220_REENTRY_CLOSE_HOLD_3 | 0.67 | -11.07pp | +0.049 | -0.051 | -181.72pp | -61.57pp | +14.05pp | 258103.71 |
| RO_REENTRY_TREND_REBUILD_FULL | 0.33 | -22.89pp | -0.107 | -0.979 | -338.65pp | -84.68pp | +14.89pp | 278350.32 |
| RO_REENTRY_WEEKLY_RSI_OVERSOLD_FULL | 0.33 | -20.94pp | +0.015 | -0.249 | -203.20pp | -97.81pp | -9.70pp | 258528.31 |

## Trigger Diagnostics

- Weekly RSI threshold: `35.0`
- Latest weekly RSI(14): `26.76`
- Weekly oversold bars on 4h alignment: `1427`
- Weekly RSI oversold availability count: `1427`
- State distribution: 100% `60.85%`, 50% `3.47%`, flat `35.68%`

## Full-Sample Portfolio References

| Scheme | Return% | Sharpe | Calmar | MaxDD% | Exposure% | Avg Core Exposure% | RiskOff Active Ratio% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 856.16 | 0.750 | 0.568 | -77.04 | 100.0 | 100.0 | 0.0 |
| Core+AddOnOverlay+RO_EMA220_FLAT | 1626.59 | 1.068 | 1.097 | -52.90 | 67.7 | 58.9 | 41.1 |
| Core+AddOnOverlay+RO_EMA220_REENTRY_CLOSE_HOLD_3 | 1821.45 | 1.106 | 1.034 | -58.78 | 66.8 | 58.0 | 42.2 |
| Core+AddOnOverlay+RO_REENTRY_TREND_REBUILD_FULL | 1203.37 | 1.001 | 0.883 | -57.82 | 63.6 | 54.8 | 45.3 |
| Core+AddOnOverlay+RO_REENTRY_WEEKLY_RSI_OVERSOLD_FULL | 369.30 | 0.662 | 0.341 | -82.70 | 71.4 | 62.6 | 39.2 |

## Full-Sample Equity / Underwater Plots

- Plot file: `RO_REENTRY_WEEKLY_RSI_OVERSOLD_FULL_PLOTS.html`

## Direct Delta Vs TREND_REBUILD_FULL

| Measure | Weekly RSI minus Trend Rebuild Full |
| --- | --- |
| strict_oos_win_ratio_delta | +0.00 |
| avg_delta_return_pct_delta | +1.95pp |
| avg_delta_calmar_delta | +0.73pp |
| bull_delta_return_pct_delta | +135.45pp |
| recovery_delta_return_pct_delta | -13.13pp |
| major_drawdown_dmaxdd_pct_delta | -24.59pp |
| avg_flat_state_upside_drag_delta | -19822.01 |

## Direct Delta Vs Best Archived Repair

| Measure | Weekly RSI minus Old Best |
| --- | --- |
| strict_oos_win_ratio_delta | -0.33 |
| avg_delta_return_pct_delta | -9.87pp |
| avg_delta_calmar_delta | -0.20pp |
| bull_delta_return_pct_delta | -21.48pp |
| recovery_delta_return_pct_delta | -36.24pp |
| major_drawdown_dmaxdd_pct_delta | -23.74pp |
| avg_flat_state_upside_drag_delta | +424.60 |

## Execution Stress

- RO_EMA220_FLAT: stress delta Return +80.03pp, Sharpe +0.014, Calmar +0.019, MaxDD improve -0.11pp
- RO_EMA220_REENTRY_CLOSE_HOLD_3: stress delta Return +149.16pp, Sharpe +0.023, Calmar +0.046, MaxDD improve +0.71pp
- RO_REENTRY_TREND_REBUILD_FULL: stress delta Return +110.87pp, Sharpe +0.025, Calmar +0.050, MaxDD improve +0.96pp
- RO_REENTRY_WEEKLY_RSI_OVERSOLD_FULL: stress delta Return +338.96pp, Sharpe +0.164, Calmar +0.181, MaxDD improve +6.31pp
- Default-mode causality violations: 0
- Stress-mode causality violations: 0

## Direct Answers

- No. It does not beat RO_REENTRY_TREND_REBUILD_FULL: strict OOS 0.33 vs 0.33, avg dReturn -20.94pp vs -22.89pp, avg dCalmar -0.249 vs -0.979.
- No. It does not beat RO_EMA220_REENTRY_CLOSE_HOLD_3: strict OOS 0.33 vs 0.67, avg dReturn -20.94pp vs -11.07pp, avg dCalmar -0.249 vs -0.051.
- No. Bull/recovery opportunity cost is not materially reduced: bull -203.20pp vs old best -181.72pp, recovery -97.81pp vs -61.57pp.
- No. Downside-control value is not preserved enough: major-drawdown dMaxDD is only -9.70pp.
- This is another dead end and should also be frozen.