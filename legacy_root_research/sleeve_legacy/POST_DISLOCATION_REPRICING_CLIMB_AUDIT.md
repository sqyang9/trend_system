# Post Dislocation Repricing Climb Audit

- Scope: test the first reset `Sleeve #3` family on top of the current adopted mainline.
- Baseline: `Core + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay (EMA250 / Weekly RSI30 hold)`.
- Candidate semantics: participate after shock damage starts resolving into orderly repricing and climb.

## Default

| System | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgExp% | PeakExp% | S3Active% | CapBind% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Formal | 2705.88 | 2.021 | -35.06 | -14.84 | -19.41 | 327.7 | 97.52 | 300.00 | 0.00 | 0.00 |
| Formal + PostDislocation | 2709.60 | 1.963 | -36.12 | -15.05 | -19.87 | 327.5 | 104.82 | 300.00 | 9.71 | 2.40 |

## Incremental vs Formal

- dReturn: +3.73pp
- dCalmar: -0.058
- dMaxDD: -1.06pp
- dSharpe: -0.026
- Trade count: 84

## Stress / Harsh

- Stress dReturn / dCalmar / dMaxDD: +12.48pp / -0.049 / -0.90pp
- Harsh dReturn / dCalmar / dMaxDD: -12.93pp / -0.068 / -1.32pp