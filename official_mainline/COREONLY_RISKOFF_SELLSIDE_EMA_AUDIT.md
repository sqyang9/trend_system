# Core-Only Risk-Off Sell-Side EMA Audit

- Scope: re-entry fixed near the current incumbents, then compare sell-side EMA replacement value.
- Architecture fixed: `Formal Portfolio = Core + ConstAddOn[1.00x] + RangeRotation` with core-only Risk-Off overlay.

## Default

| System | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgTotalExp% | AvgCoreExp% | RiskOffActive% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Formal | 1591.16 | 1.008 | -57.08 | -39.91 | -44.55 | 463.5 | 136.85 | 100.00 | 0.00 |
| Formal + WRSI14_30_EMA220 | 3049.55 | 1.886 | -39.28 | -14.77 | -25.54 | 329.3 | 97.39 | 60.54 | 39.73 |
| Formal + WRSI14_30_EMA250 | 2720.25 | 2.024 | -35.07 | -14.84 | -19.42 | 327.7 | 97.52 | 60.67 | 39.56 |
| Formal + H4RSI14_10_EMA220 | 3131.23 | 1.615 | -46.30 | -22.08 | -29.47 | 376.0 | 97.94 | 61.09 | 39.18 |
| Formal + H4RSI14_10_EMA200 | 2734.24 | 1.637 | -43.46 | -19.26 | -26.03 | 352.3 | 97.77 | 60.92 | 39.35 |

## Stress / Harsh Delta Vs Formal

| System | Stress dReturn | Stress dCalmar | Stress dMaxDD | Harsh dReturn | Harsh dCalmar | Harsh dMaxDD |
| --- | --- | --- | --- | --- | --- | --- |
| Formal + WRSI14_30_EMA220 | +1631.36pp | +0.931 | +18.02pp | +1314.82pp | +0.805 | +17.99pp |
| Formal + WRSI14_30_EMA250 | +1270.64pp | +1.075 | +22.22pp | +1022.63pp | +0.927 | +22.26pp |
| Formal + H4RSI14_10_EMA220 | +1739.61pp | +0.660 | +11.17pp | +1411.03pp | +0.580 | +11.27pp |
| Formal + H4RSI14_10_EMA200 | +1314.19pp | +0.685 | +14.02pp | +1028.38pp | +0.592 | +14.15pp |

## Readout

- This audit answers whether the incumbent EMA220 sell-side should survive once re-entry is fixed.
- Weekly branch compare: `WRSI14_30_EMA220` vs `WRSI14_30_EMA250`.
- 4h branch compare: `H4RSI14_10_EMA220` vs `H4RSI14_10_EMA200`.