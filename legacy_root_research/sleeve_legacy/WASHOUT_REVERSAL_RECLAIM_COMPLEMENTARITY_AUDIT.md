# Washout Reversal Reclaim Complementarity Audit

## Full-Sample Comparison

| System | TotalReturn | MaxDD | Calmar | Ulcer | AvgExposure |
| --- | --- | --- | --- | --- | --- |
| CoreOnly | 860.94% | -77.04% | 0.569 | 37.80 | 100.00% |
| Core+BinaryAddOn | 965.43% | -72.63% | 0.637 | 35.38 | 108.79% |
| Core+ConstAddOn[1.00x] | 1330.99% | -63.70% | 0.837 | 30.33 | 125.12% |
| Core+ConstAddOn[1.00x]+Washout | 1303.02% | -64.30% | 0.822 | 30.64 | 131.61% |

## Incremental Effect Vs Const1x

- dReturn: -27.98pp
- dMaxDD: -0.61pp
- dCalmar: -0.015
- dSharpe: -0.005

## Orthogonality

- Active overlap ratio: 0.89%
- Candidate-only active ratio: 5.60%
- Candidate entries when current sleeve is flat: 98.3%
- Active return correlation: 0.087

## Major Slices

| Slice | dReturn vs Const1x | dMaxDD vs Const1x |
| --- | --- | --- |
| bull_expansion | -85.09pp | -0.12pp |
| major_drawdown | -0.49pp | -0.61pp |
| recovery_phase | +0.40pp | -0.53pp |
| sideways_volatility | -1.21pp | -0.73pp |

## Early Recovery Window

- Window: 2022-11-21 -> 2023-05-20
- dReturn vs Const1x: +1.11pp
- dMaxDD vs Const1x: -0.07pp