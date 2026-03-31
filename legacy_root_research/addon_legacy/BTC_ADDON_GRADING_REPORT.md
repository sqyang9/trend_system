# BTC AddOn Grading Report

## Final Judgment

- AddOn-only baseline improved by grading: no
- Best grading scheme: Core+GradedAddOn[compression_breakout]
- Main conclusion: Core+GradedAddOn[compression_breakout] is the most reasonable graded AddOn variant, and it is worth a formal next-round study, but it still does not justify baseline promotion.
- Worth formal next-round research: yes

## Baseline Alignment

- Locked baseline: BTC long-only squeeze_release_20 / lb20_stop3.2_trail5.0_beoff
- Default tuple: next_bar_open + legacy_bar_extrema + midpoint + full_model
- Baseline simulator drift vs committed AddOnOverlay artifact: Return +4.71pp, Sharpe +0.001, Calmar +0.001, MaxDD improve -0.02pp

## Candidate Table

| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Exposure% | AddOn active% | dRet vs base | dSharpe | dCalmar | dMaxDD | WF strict | WF dRet | WF dSharpe | WF dCalmar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core+GradedAddOn[breakout_slope] | 983.32 | 46.64 | 0.800 | 0.652 | -71.50 | 109.7 | 25.1 | +17.89 | +0.008 | +0.016 | +1.14 | 0.33 | -2.08 | -0.009 | -0.121 |
| Core+GradedAddOn[adx_close_range] | 1013.21 | 47.28 | 0.810 | 0.668 | -70.77 | 109.8 | 25.1 | +47.79 | +0.018 | +0.031 | +1.86 | 0.33 | -6.00 | -0.005 | -0.077 |
| Core+GradedAddOn[compression_breakout] | 979.83 | 46.56 | 0.793 | 0.635 | -73.35 | 109.6 | 25.1 | +14.41 | +0.001 | -0.002 | -0.72 | 1.00 | +4.52 | +0.035 | +0.202 |

## Time-Slice Deltas Vs AddOn Baseline

| Scheme | Bull dRet | Recovery dRet | Major Drawdown dRet | Major Drawdown dMaxDD |
| --- | --- | --- | --- | --- |
| Core+GradedAddOn[breakout_slope] | +23.14pp | -15.69pp | +1.13pp | +1.14pp |
| Core+GradedAddOn[adx_close_range] | +14.18pp | -18.47pp | +1.86pp | +1.86pp |
| Core+GradedAddOn[compression_breakout] | +11.15pp | +15.15pp | -0.71pp | -0.72pp |

## Best Candidate Detail

- Best scheme description: Grade entries by squeeze quality, squeeze persistence, and breakout distance.
- Grade counts: {"weak": 19, "base": 18, "strong": 19}
- Avg AddOn weight when active: 0.382
- Execution stress delta: Return +0.31pp, Sharpe +0.000, Calmar +0.000

## Direct Answers

- No clear formal upgrade is proven. Core+GradedAddOn[compression_breakout] is the best exploratory grading variant, but the improvement is not strong enough to rewrite the binary AddOn baseline.
- The most reasonable grading scheme is Core+GradedAddOn[compression_breakout], because it leads the small candidate set on OOS strict ratio and full-sample risk-adjusted deltas without changing the mother logic.
- The improvement mainly comes from risk-adjusted improvement more than raw-return expansion.
- Yes. The best graded sleeve is worth a next-round formal study.
- Current Risk-Off status is frozen: directionally valid, execution-aligned, repeatedly failed promotion, and not part of the baseline.
- No. The team should not continue Risk-Off promotion on the same frozen line.
- The active mainline is the locked BTC long-only mother with AddOn-only baseline semantics; Risk-Off is archived and frozen, while AddOn grading is the active extension line.