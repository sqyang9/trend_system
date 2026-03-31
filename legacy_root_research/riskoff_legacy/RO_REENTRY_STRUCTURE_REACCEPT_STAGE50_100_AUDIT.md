# RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100 Audit

## Scope

- This round tests only `RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100`.
- Bear-side de-risking stays locked to the archived `EMA220 two-stage` deterioration logic.
- The only change is flat-state re-entry: restore 50% on structure re-acceptance, then 100% on follow-through acceptance.

## Candidate Summary

| Scheme | Strict OOS | Avg dReturn | Avg dSharpe | Avg dCalmar | Bull dReturn | Recovery dReturn | Major Drawdown dMaxDD | Avg Flat Upside Drag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RO_EMA220_FLAT | 0.33 | -19.29pp | -0.139 | -0.767 | -233.07pp | -77.59pp | +20.26pp | 233618.10 |
| RO_EMA220_REENTRY_CLOSE_HOLD_3 | 0.67 | -11.07pp | +0.049 | -0.051 | -181.72pp | -61.57pp | +14.05pp | 258103.71 |
| RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100 | 0.00 | -65.89pp | -0.638 | -2.804 | -904.99pp | -254.03pp | +45.76pp | 519568.19 |

## Trigger Diagnostics

- `structure_reaccept_50` trigger count: 53
- `structure_reaccept_full` trigger count: 640
- State distribution: 100% `16.87%`, 50% `2.24%`, flat `80.89%`
- Interpretation: the candidate fails mainly because the first restoration step is too sparse, so the line stays flat for too long and misses most bull / recovery participation.

## Full-Sample Portfolio References

| Scheme | Return% | Sharpe | Calmar | MaxDD% | Exposure% | Avg Core Exposure% | RiskOff Active Ratio% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 856.16 | 0.750 | 0.568 | -77.04 | 100.0 | 100.0 | 0.0 |
| Core+AddOnOverlay+RO_EMA220_FLAT | 1626.59 | 1.068 | 1.097 | -52.90 | 67.7 | 58.9 | 41.1 |
| Core+AddOnOverlay+RO_EMA220_REENTRY_CLOSE_HOLD_3 | 1821.45 | 1.106 | 1.034 | -58.78 | 66.8 | 58.0 | 42.2 |
| Core+AddOnOverlay+RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100 | 113.83 | 0.520 | 0.296 | -43.95 | 26.8 | 18.0 | 83.1 |

## Direct Delta Vs Best Archived Repair

| Measure | New minus Old Best |
| --- | --- |
| strict_oos_win_ratio_delta | -0.67 |
| avg_delta_return_pct_delta | -54.82pp |
| avg_delta_calmar_delta | -2.75pp |
| bull_delta_return_pct_delta | -723.26pp |
| recovery_delta_return_pct_delta | -192.46pp |
| major_drawdown_dmaxdd_pct_delta | +31.72pp |
| avg_flat_state_upside_drag_delta | +261464.48 |

## Execution Stress

- RO_EMA220_FLAT: stress delta Return +80.03pp, Sharpe +0.014, Calmar +0.019, MaxDD improve -0.11pp
- RO_EMA220_REENTRY_CLOSE_HOLD_3: stress delta Return +149.16pp, Sharpe +0.023, Calmar +0.046, MaxDD improve +0.71pp
- RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100: stress delta Return +2.79pp, Sharpe +0.007, Calmar +0.010, MaxDD improve +0.68pp
- Default-mode causality violations: 0
- Stress-mode causality violations: 0

## Direct Answers

- No. It does not beat RO_EMA220_REENTRY_CLOSE_HOLD_3: strict OOS stays 0.00 vs 0.67, avg dReturn is -65.89pp vs -11.07pp, and avg dCalmar is -2.804 vs -0.051.
- No. Bull/recovery opportunity cost is not materially reduced: bull -904.99pp vs old best -181.72pp, recovery -254.03pp vs -61.57pp.
- Yes. Downside-control value is broadly preserved: major-drawdown dMaxDD is +45.76pp.
- Stay exploratory. The line is not strong enough to reopen promotion yet, but this single test does not justify re-freezing the entire re-entry deep dive.