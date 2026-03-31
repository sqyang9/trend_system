# RO_REENTRY_TREND_REBUILD_STAGE50_100 Audit

## Scope

- This round tests only `RO_REENTRY_TREND_REBUILD_STAGE50_100`.
- Bear-side de-risking stays locked to the archived `EMA220 two-stage` deterioration logic.
- The only change is flat-state re-entry: restore 50% on trend rebuild, then 100% on stronger rebuild follow-through.

## Candidate Summary

| Scheme | Strict OOS | Avg dReturn | Avg dSharpe | Avg dCalmar | Bull dReturn | Recovery dReturn | Major Drawdown dMaxDD | Avg Flat Upside Drag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RO_EMA220_FLAT | 0.33 | -19.29pp | -0.139 | -0.767 | -233.07pp | -77.59pp | +20.26pp | 233618.10 |
| RO_EMA220_REENTRY_CLOSE_HOLD_3 | 0.67 | -11.07pp | +0.049 | -0.051 | -181.72pp | -61.57pp | +14.05pp | 258103.71 |
| RO_REENTRY_TREND_REBUILD_STAGE50_100 | 0.33 | -18.54pp | -0.038 | -0.713 | -286.03pp | -79.42pp | +15.09pp | 267600.77 |

## Trigger Diagnostics

- `trend_rebuild_50` trigger count: 2263
- `trend_rebuild_full` trigger count: 1913
- State distribution: 100% `54.62%`, 50% `2.05%`, flat `43.33%`
- Interpretation: this candidate succeeds only if rebuild triggers are frequent enough to restore participation without fully collapsing back into EMA-delay logic.

## Full-Sample Portfolio References

| Scheme | Return% | Sharpe | Calmar | MaxDD% | Exposure% | Avg Core Exposure% | RiskOff Active Ratio% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 856.16 | 0.750 | 0.568 | -77.04 | 100.0 | 100.0 | 0.0 |
| Core+AddOnOverlay+RO_EMA220_FLAT | 1626.59 | 1.068 | 1.097 | -52.90 | 67.7 | 58.9 | 41.1 |
| Core+AddOnOverlay+RO_EMA220_REENTRY_CLOSE_HOLD_3 | 1821.45 | 1.106 | 1.034 | -58.78 | 66.8 | 58.0 | 42.2 |
| Core+AddOnOverlay+RO_REENTRY_TREND_REBUILD_STAGE50_100 | 1439.60 | 1.051 | 0.956 | -57.71 | 64.4 | 55.6 | 45.4 |

## Direct Delta Vs Best Archived Repair

| Measure | New minus Old Best |
| --- | --- |
| strict_oos_win_ratio_delta | -0.33 |
| avg_delta_return_pct_delta | -7.47pp |
| avg_delta_calmar_delta | -0.66pp |
| bull_delta_return_pct_delta | -104.30pp |
| recovery_delta_return_pct_delta | -17.85pp |
| major_drawdown_dmaxdd_pct_delta | +1.05pp |
| avg_flat_state_upside_drag_delta | +9497.06 |

## Execution Stress

- RO_EMA220_FLAT: stress delta Return +80.03pp, Sharpe +0.014, Calmar +0.019, MaxDD improve -0.11pp
- RO_EMA220_REENTRY_CLOSE_HOLD_3: stress delta Return +149.16pp, Sharpe +0.023, Calmar +0.046, MaxDD improve +0.71pp
- RO_REENTRY_TREND_REBUILD_STAGE50_100: stress delta Return +132.77pp, Sharpe +0.026, Calmar +0.052, MaxDD improve +0.91pp
- Default-mode causality violations: 0
- Stress-mode causality violations: 0

## Direct Answers

- No. It does not beat RO_EMA220_REENTRY_CLOSE_HOLD_3: strict OOS stays 0.33 vs 0.67, avg dReturn is -18.54pp vs -11.07pp, and avg dCalmar is -0.713 vs -0.051.
- No. Bull/recovery opportunity cost is not materially reduced: bull -286.03pp vs old best -181.72pp, recovery -79.42pp vs -61.57pp.
- Yes. Downside-control value is broadly preserved: major-drawdown dMaxDD is +15.09pp.
- Stay exploratory. The line is not strong enough to reopen promotion yet, but this single test does not justify re-freezing the entire re-entry deep dive.