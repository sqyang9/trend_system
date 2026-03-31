# Pullback Reclaim Continuation Complementarity Audit

## Full-Sample Comparison

| System | TotalReturn | MaxDD | Calmar | Ulcer | AvgExposure |
| --- | --- | --- | --- | --- | --- |
| CoreOnly | 860.94% | -77.04% | 0.569 | 37.80 | 100.00% |
| Core+BinaryAddOn | 965.43% | -72.63% | 0.637 | 35.38 | 108.79% |
| Core+ConstAddOn[1.00x] | 1330.99% | -63.70% | 0.837 | 30.33 | 125.12% |
| Core+ConstAddOn[1.00x]+PullbackReclaim | 1329.29% | -63.93% | 0.834 | 31.67 | 150.29% |

## Incremental Effect Vs Const1x

- dReturn: -1.71pp
- dMaxDD: -0.24pp
- dCalmar: -0.004
- dSharpe: -0.011

## Orthogonality

- Active overlap ratio: 15.55%
- Candidate-only active ratio: 9.62%
- Candidate entries when current sleeve is flat: 55.1%
- Active return correlation: 0.667

## Major Slices

| Slice | dReturn vs Const1x | dMaxDD vs Const1x |
| --- | --- | --- |
| bull_expansion | -56.96pp | +0.70pp |
| major_drawdown | -0.22pp | -0.23pp |
| recovery_phase | -17.72pp | -1.93pp |
| sideways_volatility | +0.03pp | -0.40pp |

## Early Recovery Window

- Window: 2022-11-21 -> 2023-05-20
- dReturn vs Const1x: -9.83pp
- dMaxDD vs Const1x: -1.88pp