# RO_REENTRY_TREND_REBUILD_FULL Audit

## Scope

- This round tests only `RO_REENTRY_TREND_REBUILD_FULL`.
- Bear-side de-risking stays locked to the archived `EMA220 two-stage` deterioration logic.
- The only change is flat-state re-entry: restore directly to 100% on trend rebuild confirmation.

## Candidate Summary

| Scheme | Strict OOS | Avg dReturn | Avg dSharpe | Avg dCalmar | Bull dReturn | Recovery dReturn | Major Drawdown dMaxDD | Avg Flat Upside Drag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RO_EMA220_FLAT | 0.33 | -19.29pp | -0.139 | -0.767 | -233.07pp | -77.59pp | +20.26pp | 233618.10 |
| RO_EMA220_REENTRY_CLOSE_HOLD_3 | 0.67 | -11.07pp | +0.049 | -0.051 | -181.72pp | -61.57pp | +14.05pp | 258103.71 |
| RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100 | 0.00 | -65.89pp | -0.638 | -2.804 | -904.99pp | -254.03pp | +45.76pp | 519568.19 |
| RO_REENTRY_TREND_REBUILD_STAGE50_100 | 0.33 | -18.54pp | -0.038 | -0.713 | -286.03pp | -79.42pp | +15.09pp | 267600.77 |
| RO_REENTRY_TREND_REBUILD_FULL | 0.67 | -13.44pp | +0.042 | -0.327 | -233.11pp | -64.47pp | +15.34pp | 267345.94 |

## Trigger Diagnostics

- `trend_rebuild_50` trigger count: 2263
- `trend_rebuild_full` trigger count: 1913
- State distribution: 100% `56.33%`, 50% `0.41%`, flat `43.26%`
- Interpretation: the key question is whether removing staged restoration improves participation enough to justify the extra early re-risking.

## Full-Sample Portfolio References

| Scheme | Return% | Sharpe | Calmar | MaxDD% | Exposure% | Avg Core Exposure% | RiskOff Active Ratio% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 856.16 | 0.750 | 0.568 | -77.04 | 100.0 | 100.0 | 0.0 |
| Core+AddOnOverlay+RO_EMA220_FLAT | 1626.59 | 1.068 | 1.097 | -52.90 | 67.7 | 58.9 | 41.1 |
| Core+AddOnOverlay+RO_EMA220_REENTRY_CLOSE_HOLD_3 | 1821.45 | 1.106 | 1.034 | -58.78 | 66.8 | 58.0 | 42.2 |
| Core+AddOnOverlay+RO_REENTRY_TREND_REBUILD_FULL | 1737.24 | 1.100 | 1.039 | -57.41 | 65.3 | 56.5 | 43.7 |
| Core+AddOnOverlay+RO_REENTRY_TREND_REBUILD_STAGE50_100 | 1439.60 | 1.051 | 0.956 | -57.71 | 64.4 | 55.6 | 45.4 |

## Direct Delta Vs Best Archived Repair

| Measure | New minus Old Best |
| --- | --- |
| strict_oos_win_ratio_delta | +0.00 |
| avg_delta_return_pct_delta | -2.36pp |
| avg_delta_calmar_delta | -0.28pp |
| bull_delta_return_pct_delta | -51.38pp |
| recovery_delta_return_pct_delta | -2.91pp |
| major_drawdown_dmaxdd_pct_delta | +1.29pp |
| avg_flat_state_upside_drag_delta | +9242.23 |

## Execution Stress

- RO_EMA220_FLAT: stress delta Return +80.03pp, Sharpe +0.014, Calmar +0.019, MaxDD improve -0.11pp
- RO_EMA220_REENTRY_CLOSE_HOLD_3: stress delta Return +149.16pp, Sharpe +0.023, Calmar +0.046, MaxDD improve +0.71pp
- RO_REENTRY_TREND_REBUILD_FULL: stress delta Return +167.18pp, Sharpe +0.027, Calmar +0.055, MaxDD improve +0.82pp
- Default-mode causality violations: 0
- Stress-mode causality violations: 0

## Direct Answers

- Yes. It beats RO_REENTRY_TREND_REBUILD_STAGE50_100: strict OOS 0.67 vs 0.33, avg dReturn -13.44pp vs -18.54pp, avg dCalmar -0.327 vs -0.713.
- No. It does not beat RO_EMA220_REENTRY_CLOSE_HOLD_3: strict OOS stays 0.67 vs 0.67, avg dReturn is -13.44pp vs -11.07pp, and avg dCalmar is -0.327 vs -0.051.
- No. Bull/recovery opportunity cost is not materially reduced: bull -233.11pp vs old best -181.72pp, recovery -64.47pp vs -61.57pp.
- Yes. Downside-control value remains acceptable: major-drawdown dMaxDD is +15.34pp.