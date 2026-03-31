# Dislocation Repricing Rebuild Complementarity Audit

## Full-Sample Comparison

| System | TotalReturn | MaxDD | Calmar | Ulcer | AvgExposure | RecoveryDays |
| --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 860.94% | -77.04% | 0.569 | 37.80 | 100.00% | 473.0 |
| Core+ConstAddOn[1.00x] | 1330.99% | -63.70% | 0.837 | 30.33 | 125.12% | 462.3 |
| Core+ConstAddOn[1.00x]+RangeRotation | 1591.16% | -57.08% | 1.008 | 27.94 | 136.85% | 463.5 |
| Core+ConstAddOn[1.00x]+RangeRotation+DislocationRebuild | 1587.92% | -57.21% | 1.004 | 28.00 | 137.27% | 463.5 |

## Incremental Effect Vs Current Two-Sleeve Baseline

- dReturn: -3.24pp
- dMaxDD: -0.13pp
- dCalmar: -0.003
- dSharpe: -0.001
- dRecoveryDays: +0.0

## Orthogonality

- Vs Sleeve #1 active overlap: 0.00%
- Vs Sleeve #2 active overlap: 0.14%
- Candidate entries when full two-sleeve stack is flat: 66.7%
- Candidate-only active ratio vs full stack: 0.28%
- Active return correlation vs Sleeve #1: -0.000
- Active return correlation vs Sleeve #2: 0.084

## Major Slices

| Slice | dReturn vs Two-Sleeve | dMaxDD vs Two-Sleeve |
| --- | --- | --- |
| bull_expansion | -2.43pp | -0.07pp |
| major_drawdown | -0.13pp | -0.13pp |
| recovery_phase | +0.88pp | -0.06pp |
| sideways_volatility | +0.01pp | -0.05pp |

## Early Recovery Window

- Window: 2022-11-21 -> 2023-05-20
- dReturn vs Two-Sleeve: +0.21pp
- dMaxDD vs Two-Sleeve: -0.05pp