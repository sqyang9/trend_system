# RO_REENTRY_TIME_PLUS_STATE_FULL Audit

## Scope

- This round tests only `RO_REENTRY_TIME_PLUS_STATE_FULL`.
- Bear-side de-risking stays locked to the archived `EMA220 two-stage` deterioration logic.
- The only change is flat-state re-entry: wait briefly, require a lightweight state clearance, then restore directly to 100%.

## Candidate Summary

| Scheme | Strict OOS | Avg dReturn | Avg dSharpe | Avg dCalmar | Bull dReturn | Recovery dReturn | Major Drawdown dMaxDD | Avg Flat Upside Drag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RO_EMA220_FLAT | 0.33 | -19.29pp | -0.139 | -0.767 | -233.07pp | -77.59pp | +20.26pp | 233618.10 |
| RO_EMA220_REENTRY_CLOSE_HOLD_3 | 0.67 | -11.07pp | +0.049 | -0.051 | -181.72pp | -61.57pp | +14.05pp | 258103.71 |
| RO_REENTRY_TREND_REBUILD_FULL | 0.67 | -13.44pp | +0.042 | -0.327 | -233.11pp | -64.47pp | +15.34pp | 267345.94 |
| RO_REENTRY_TIME_PLUS_STATE_FULL | 0.67 | -13.69pp | +0.038 | -0.229 | -303.84pp | -62.11pp | +15.12pp | 269135.40 |

## Trigger Diagnostics

- `time_state_full` trigger count: 2580
- Minimum flat wait: 2 bars
- State distribution: 100% `56.04%`, 50% `0.40%`, flat `43.57%`
- Interpretation: the key question is whether a small wait plus light state confirmation can restore participation earlier than trend-rebuild full without losing too much protection.

## Full-Sample Portfolio References

| Scheme | Return% | Sharpe | Calmar | MaxDD% | Exposure% | Avg Core Exposure% | RiskOff Active Ratio% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 856.16 | 0.750 | 0.568 | -77.04 | 100.0 | 100.0 | 0.0 |
| Core+AddOnOverlay+RO_EMA220_FLAT | 1626.59 | 1.068 | 1.097 | -52.90 | 67.7 | 58.9 | 41.1 |
| Core+AddOnOverlay+RO_EMA220_REENTRY_CLOSE_HOLD_3 | 1821.45 | 1.106 | 1.034 | -58.78 | 66.8 | 58.0 | 42.2 |
| Core+AddOnOverlay+RO_REENTRY_TIME_PLUS_STATE_FULL | 1555.47 | 1.071 | 0.991 | -57.52 | 65.0 | 56.2 | 44.0 |
| Core+AddOnOverlay+RO_REENTRY_TREND_REBUILD_FULL | 1737.24 | 1.100 | 1.039 | -57.41 | 65.3 | 56.5 | 43.7 |

## Direct Delta Vs Best Archived Repair

| Measure | New minus Old Best |
| --- | --- |
| strict_oos_win_ratio_delta | +0.00 |
| avg_delta_return_pct_delta | -2.62pp |
| avg_delta_calmar_delta | -0.18pp |
| bull_delta_return_pct_delta | -122.11pp |
| recovery_delta_return_pct_delta | -0.54pp |
| major_drawdown_dmaxdd_pct_delta | +1.08pp |
| avg_flat_state_upside_drag_delta | +11031.70 |

## Execution Stress

- RO_EMA220_FLAT: stress delta Return +80.03pp, Sharpe +0.014, Calmar +0.019, MaxDD improve -0.11pp
- RO_EMA220_REENTRY_CLOSE_HOLD_3: stress delta Return +149.16pp, Sharpe +0.023, Calmar +0.046, MaxDD improve +0.71pp
- RO_REENTRY_TIME_PLUS_STATE_FULL: stress delta Return +122.72pp, Sharpe +0.022, Calmar +0.045, MaxDD improve +0.72pp
## Direct Answers

- No. It does not beat RO_REENTRY_TREND_REBUILD_FULL: strict OOS 0.67 vs 0.67, avg dReturn -13.69pp vs -13.44pp, avg dCalmar -0.229 vs -0.327.
- No. It does not beat RO_EMA220_REENTRY_CLOSE_HOLD_3: strict OOS 0.67 vs 0.67, avg dReturn -13.69pp vs -11.07pp, avg dCalmar -0.229 vs -0.051.
- No. Opportunity-cost drag is not materially reduced: bull -303.84pp vs old best -181.72pp, recovery -62.11pp vs -61.57pp.
- Yes. Downside-control value remains acceptable: major-drawdown dMaxDD is +15.12pp.