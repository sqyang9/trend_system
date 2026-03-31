# Failed Breakdown Acceptance Complementarity Audit

## Full-Sample Comparison

| System | TotalReturn | MaxDD | Calmar | Ulcer | AvgExposure | RecoveryDays |
| --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 860.94% | -77.04% | 0.569 | 37.80 | 100.00% | 473.0 |
| Core+ConstAddOn[1.00x] | 1330.99% | -63.70% | 0.837 | 30.33 | 125.12% | 462.3 |
| Core+ConstAddOn[1.00x]+RangeRotation | 1591.16% | -57.08% | 1.008 | 27.94 | 136.85% | 463.5 |
| Core+ConstAddOn[1.00x]+RangeRotation+FailedBreakdown | 1580.42% | -56.84% | 1.009 | 27.95 | 140.13% | 463.5 |

## Incremental Effect Vs Current Two-Sleeve Baseline

- dReturn: -10.74pp
- dMaxDD: +0.24pp
- dCalmar: +0.001
- dSharpe: -0.004
- dRecoveryDays: +0.0

## Orthogonality

- Vs Sleeve #1 active overlap: 1.52%
- Vs Sleeve #2 active overlap: 1.65%
- Candidate entries when full two-sleeve stack is flat: 39.3%
- Candidate-only active ratio vs full stack: 1.12%
- Active return correlation vs Sleeve #1: 0.121
- Active return correlation vs Sleeve #2: 0.200

## Major Slices

| Slice | dReturn vs Two-Sleeve | dMaxDD vs Two-Sleeve |
| --- | --- | --- |
| bull_expansion | -0.85pp | -0.34pp |
| major_drawdown | +0.25pp | +0.24pp |
| recovery_phase | -2.73pp | -0.21pp |
| sideways_volatility | -0.05pp | -0.20pp |

## Early Recovery Window

- Window: 2022-11-21 -> 2023-05-20
- dReturn vs Two-Sleeve: -0.37pp
- dMaxDD vs Two-Sleeve: +0.05pp