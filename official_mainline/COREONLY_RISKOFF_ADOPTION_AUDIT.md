# Core-Only Risk-Off Adoption Audit

- Semantics: Risk-Off only changes the `core` layer.
- `Sleeve #1 = ConstAddOn[1.00x]` and `Sleeve #2 = RangeRotation` keep their native activation and are not forced flat by Risk-Off.
- Purpose: run the same promotion-style adoption framing used for the full-stack study, but on the core-only architecture.

## Default

| System | Return% | CAGR% | Sharpe | Calmar | MaxDD% | RecoveryDays | Worst3m | Worst6m | AvgTotalExp% | AvgCoreExp% | RiskOffActive% | S1Active% | S2Active% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Formal Portfolio | 1591.16 | 57.51 | 0.986 | 1.008 | -57.08 | 463.5 | -39.91 | -44.55 | 136.85 | 100.00 | 0.00 | 25.12 | 11.73 |
| Formal + RO_LOWVALUE_WEEKLY_RSI30_HOLD | 3036.06 | 73.94 | 1.261 | 1.884 | -39.25 | 329.3 | -14.75 | -25.51 | 97.39 | 60.54 | 39.73 | 25.12 | 11.73 |
| Formal + RO_LOWVALUE_4H_RSI10_HOLD | 3117.34 | 74.66 | 1.278 | 1.614 | -46.27 | 376.0 | -22.06 | -29.44 | 97.94 | 61.09 | 39.18 | 25.12 | 11.73 |

## Stress / Harsh Delta Vs Formal

| System | Stress dReturn | Stress dCalmar | Stress dMaxDD | Harsh dReturn | Harsh dCalmar | Harsh dMaxDD |
| --- | --- | --- | --- | --- | --- | --- |
| Formal + RO_LOWVALUE_WEEKLY_RSI30_HOLD | +1613.81pp | +0.927 | +18.01pp | +1300.03pp | +0.802 | +17.98pp |
| Formal + RO_LOWVALUE_4H_RSI10_HOLD | +1721.53pp | +0.656 | +11.16pp | +1395.77pp | +0.577 | +11.27pp |

## Readout

- Compare this file directly against `FULLSTACK_RISKOFF_ADOPTION_AUDIT.md` before deciding which structure survives.
- If core-only remains stronger here, then full-stack flattening should be rejected as unnecessary suppression.