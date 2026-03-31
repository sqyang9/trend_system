# Failed Breakdown Reversal Acceptance Default Probe

- Scope: default-only probe for the second reset `Sleeve #3` family on top of the current adopted mainline.
- Baseline: `Core + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay (EMA250 / Weekly RSI30 hold)`.

## Default

| System | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgExp% | PeakExp% | S3Active% | CapBind% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Formal | 2705.88 | 2.021 | -35.06 | -14.84 | -19.41 | 327.7 | 97.52 | 300.00 | 0.00 | 0.00 |
| Formal + FailedBreakdown | 2676.39 | 2.006 | -35.19 | -15.21 | -19.65 | 327.5 | 99.79 | 300.00 | 3.28 | 1.01 |

## Incremental vs Formal

- dReturn: -29.48pp
- dCalmar: -0.016
- dMaxDD: -0.13pp
- dSharpe: -0.007
- Trade count: 28

## Readout

- This is a screening probe, not a full `default / stress / harsher friction` closure.
- Directionally it is already weak enough to reject without promoting it to a heavier full audit.
