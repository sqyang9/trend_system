# Trend Drift Persistence Complementarity Audit

## Full-Sample Comparison

| System | TotalReturn | MaxDD | Calmar | Ulcer | AvgExposure | RecoveryDays |
| --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 860.94% | -77.04% | 0.569 | 37.80 | 100.00% | 473.0 |
| Core+ConstAddOn[1.00x] | 1330.99% | -63.70% | 0.837 | 30.33 | 125.12% | 462.3 |
| Core+ConstAddOn[1.00x]+RangeRotation | 1591.16% | -57.08% | 1.008 | 27.94 | 136.85% | 463.5 |
| Core+ConstAddOn[1.00x]+RangeRotation+TrendDrift | 1611.85% | -57.14% | 1.012 | 27.89 | 138.92% | 463.5 |

## Incremental Effect Vs Current Two-Sleeve Baseline

- dReturn: +20.69pp
- dMaxDD: -0.06pp
- dCalmar: +0.004
- dSharpe: +0.007
- dRecoveryDays: +0.0

## Orthogonality

- Vs Sleeve #1 active overlap: 1.80%
- Vs Sleeve #2 active overlap: 0.88%
- Candidate entries when full two-sleeve stack is flat: 25.0%
- Candidate-only active ratio vs full stack: 0.17%
- Active return correlation vs Sleeve #1: 0.285
- Active return correlation vs Sleeve #2: 0.123

## Major Slices

| Slice | dReturn vs Two-Sleeve | dMaxDD vs Two-Sleeve |
| --- | --- | --- |
| bull_expansion | -24.04pp | +0.20pp |
| major_drawdown | -0.08pp | -0.06pp |
| recovery_phase | +0.98pp | +0.08pp |
| sideways_volatility | +0.07pp | +0.29pp |

## Early Recovery Window

- Window: 2022-11-21 -> 2023-05-20
- dReturn vs Two-Sleeve: -0.29pp
- dMaxDD vs Two-Sleeve: +0.07pp