# BTC Risk-Off Narrow Promotion Check

## Final Judgment

- This round is a single-candidate diagnostic for `RO_EMA220_TWOSTAGE_50_TO_0`.
- Main finding: The remaining blocker is still upside opportunity cost after Risk-Off, especially in recovery-like windows. The main drag is not the 50% bridge itself; it is staying flat for too long after risk conditions improve.
- Promotion implication: Do not promote Risk-Off yet. If work continues, focus only on re-entry timing out of flat state for RO_EMA220_TWOSTAGE_50_TO_0.

## Full-Sample Comparison

| Scheme | Return% | Sharpe | Calmar | MaxDD% | Exposure% |
| --- | --- | --- | --- | --- | --- |
| Core+AddOnOverlay | 960.72 | 0.791 | 0.636 | -72.61 | 108.8 |
| Core+AddOnOverlay+RO_EMA220_FLAT | 1626.59 | 1.068 | 1.097 | -52.90 | 67.7 |
| Core+AddOnOverlay+RO_EMA220_TWOSTAGE_50_TO_0 | 1778.06 | 1.092 | 1.102 | -54.60 | 68.1 |

## OOS Windows

| Window | dReturn | dSharpe | dCalmar | dMaxDD improve | Strict | state 1.0% | state 0.5% | state 0.0% | State Changes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| OOS_2023 | -25.91pp | -0.149 | -1.199 | +0.65pp | False | 69.2 | 0.9 | 29.9 | 52 |
| OOS_2024 | -9.73pp | +0.102 | +0.700 | +6.81pp | True | 70.4 | 0.8 | 28.7 | 49 |
| OOS_2025 | +1.21pp | -0.095 | -0.023 | +9.70pp | False | 51.0 | 1.1 | 47.9 | 68 |

## Problem Diagnosis

- OOS_2023: upside_drag=54384.07, downside_protection=50500.49, soft_upside_drag=0.00, flat_upside_drag=47034.83, soft_downside_protection=0.00, flat_downside_protection=50500.49
- OOS_2024: upside_drag=213487.51, downside_protection=211362.20, soft_upside_drag=0.00, flat_upside_drag=193961.95, soft_downside_protection=0.00, flat_downside_protection=211362.20
- OOS_2025: upside_drag=491021.01, downside_protection=493299.93, soft_upside_drag=0.00, flat_upside_drag=447980.80, soft_downside_protection=0.00, flat_downside_protection=493299.93

## Worst Months

### OOS_2023
- 2023-09: -7.77pp
- 2023-04: -3.41pp
- 2023-03: -3.16pp
- 2023-05: -0.66pp
- 2023-07: -0.36pp
### OOS_2024
- 2024-05: -9.34pp
- 2024-10: -3.52pp
- 2024-08: -2.42pp
- 2024-09: -1.17pp
- 2024-01: +0.00pp
### OOS_2025
- 2025-04: -9.76pp
- 2025-09: -9.63pp
- 2025-03: -2.57pp
- 2025-10: -1.90pp
- 2025-06: -1.62pp

## Direct Answers

- The main blocker is still recovery-side opportunity cost. Worst OOS window is OOS_2023 with dReturn -25.91pp and dCalmar -1.199.
- The repaired structure does defend downside, but most of its remaining problem comes from missed upside while reduced. Largest upside-drag window is OOS_2025 with upside_drag 491021.01 versus downside_protection 493299.93.
- The 50% soft stage is not the main problem. In OOS_2023, state_0.50 is only 0.9% of bars, while flat-state upside drag is 47034.83 and dominates the missed upside.
- Promotion still fails because the candidate improves full-sample optics and downside control, but cannot convert that into repeated strict OOS wins. The next step, if any, should target re-entry timing out of flat state rather than the bear trigger itself.