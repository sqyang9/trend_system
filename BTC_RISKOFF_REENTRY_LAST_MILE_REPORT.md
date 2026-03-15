# BTC Risk-Off Reentry Last Mile Report

## Final Judgment

- This round is the last-mile re-entry repair check, not a new search.
- Last-mile answer: PARTIAL. Re-entry timing helps, but not enough to rescue promotion.
- Best repair candidate: RO_EMA220_REENTRY_CLOSE_HOLD_3
- Promotion decision: Stop Risk-Off promotion
- Recommendation: Stop Risk-Off promotion. Keep AddOn-only baseline unchanged.

## Candidate Comparison

| Candidate | Strict OOS Win Ratio | Avg dReturn | Avg dSharpe | Avg dCalmar | Bull dReturn | Recovery dReturn | Sideways dReturn | Major Drawdown dMaxDD | Avg Flat Upside Drag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RO_EMA220_TWOSTAGE_50_TO_0_BASE | 0.33 | -20.54pp | -0.048 | -0.863 | -333.47pp | -86.65pp | +25.36pp | +15.32pp | 274543.71 |
| RO_EMA220_REENTRY_CLOSE_HOLD_1 | 0.33 | -11.47pp | -0.047 | -0.174 | -225.46pp | -48.82pp | +23.19pp | +18.24pp | 230424.90 |
| RO_EMA220_REENTRY_CLOSE_HOLD_2 | 0.33 | -14.29pp | -0.055 | -0.269 | -166.30pp | -56.61pp | +22.83pp | +15.76pp | 253021.94 |
| RO_EMA220_REENTRY_CLOSE_HOLD_3 | 0.67 | -11.07pp | +0.049 | -0.051 | -181.72pp | -61.57pp | +35.76pp | +14.05pp | 258103.71 |
| RO_EMA220_REENTRY_STAGE50_CLOSE_1 | 0.33 | -9.47pp | -0.019 | +0.054 | -191.02pp | -42.21pp | +25.20pp | +16.91pp | 230242.66 |
| RO_EMA220_REENTRY_STAGE75_CLOSE_1 | 0.33 | -10.46pp | -0.033 | -0.061 | -208.28pp | -45.49pp | +24.20pp | +17.57pp | 230333.42 |

## Full-Sample References

| Scheme | Return% | Sharpe | Calmar | MaxDD% | Exposure% |
| --- | --- | --- | --- | --- | --- |
| Core+AddOnOverlay | 960.72 | 0.791 | 0.636 | -72.61 | 108.8 |
| Core+AddOnOverlay+RO_EMA220_FLAT | 1626.59 | 1.068 | 1.097 | -52.90 | 67.7 |
| Core+AddOnOverlay+RO_EMA220_REENTRY_CLOSE_HOLD_3 | 1821.45 | 1.106 | 1.034 | -58.78 | 66.8 |

## Execution Stress And Causality

- RO_EMA220_TWOSTAGE_50_TO_0_BASE: stress delta Return +109.87pp, Sharpe +0.023, Calmar +0.044, MaxDD improve +0.68pp
- RO_EMA220_REENTRY_CLOSE_HOLD_1: stress delta Return +117.18pp, Sharpe +0.019, Calmar +0.028, MaxDD improve -0.05pp
- RO_EMA220_REENTRY_CLOSE_HOLD_2: stress delta Return +153.46pp, Sharpe +0.024, Calmar +0.060, MaxDD improve +1.26pp
- RO_EMA220_REENTRY_CLOSE_HOLD_3: stress delta Return +149.16pp, Sharpe +0.023, Calmar +0.046, MaxDD improve +0.71pp
- RO_EMA220_REENTRY_STAGE50_CLOSE_1: stress delta Return +142.17pp, Sharpe +0.021, Calmar +0.046, MaxDD improve +0.65pp
- RO_EMA220_REENTRY_STAGE75_CLOSE_1: stress delta Return +129.18pp, Sharpe +0.020, Calmar +0.037, MaxDD improve +0.30pp
- Default-mode causality violations: 0
- Stress-mode causality violations: 0

## Direct Answers

- Partially. Re-entry timing can still be improved, but the improvement is not enough to remove the promotion blocker.
- Best re-entry repair candidate is Core+AddOnOverlay+RO_EMA220_REENTRY_CLOSE_HOLD_3.
- Yes. Strict OOS win ratio rises to 0.67.
- No. Avg delta Calmar improves to -0.051, but it does not turn non-negative.
- Recovery drag improves versus the base repair, but remains too large at -61.57pp.
- Yes. Stop Risk-Off promotion and keep AddOn-only baseline unchanged.
- No. Evidence still does not reach promotion-candidate level.