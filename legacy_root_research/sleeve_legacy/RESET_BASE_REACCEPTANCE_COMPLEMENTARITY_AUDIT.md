# Reset Base Reacceptance Complementarity Audit

## Full-Sample Comparison

| System | TotalReturn | MaxDD | Calmar | Ulcer | AvgExposure | RecoveryDays |
| --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 860.94% | -77.04% | 0.569 | 37.80 | 100.00% | 473.0 |
| Core+ConstAddOn[1.00x] | 1330.99% | -63.70% | 0.837 | 30.33 | 125.12% | 462.3 |
| Core+ConstAddOn[1.00x]+RangeRotation | 1591.16% | -57.08% | 1.008 | 27.94 | 136.85% | 463.5 |
| Core+ConstAddOn[1.00x]+RangeRotation+ResetBase | 1612.42% | -55.75% | 1.037 | 27.49 | 139.44% | 463.7 |

## Incremental Effect Vs Current Two-Sleeve Baseline

- dReturn: +21.26pp
- dMaxDD: +1.33pp
- dCalmar: +0.030
- dSharpe: +0.010
- dRecoveryDays: +0.2

## Orthogonality

- Vs Sleeve #1 active overlap: 1.66%
- Vs Sleeve #2 active overlap: 1.60%
- Candidate entries when full two-sleeve stack is flat: 36.8%
- Candidate-only active ratio vs full stack: 0.34%
- Active return correlation vs Sleeve #1: 0.279
- Active return correlation vs Sleeve #2: 0.257

## Major Slices

| Slice | dReturn vs Two-Sleeve | dMaxDD vs Two-Sleeve |
| --- | --- | --- |
| bull_expansion | +30.24pp | +0.81pp |
| major_drawdown | +1.35pp | +1.37pp |
| recovery_phase | -10.71pp | +0.57pp |
| sideways_volatility | -0.60pp | +0.26pp |

## Early Recovery Window

- Window: 2022-11-21 -> 2023-05-20
- dReturn vs Two-Sleeve: -2.61pp
- dMaxDD vs Two-Sleeve: +0.52pp