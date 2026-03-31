# Formal Base + Risk-Off Re-Entry Audit

## Scope

- Base architecture is fixed to `Core + ConstAddOn[1.00x] + RangeRotation`.
- Risk-Off only changes the `core` layer.
- `ConstAddOn[1.00x]` and `RangeRotation` remain unchanged.
- Comparison set:
  - `Formal Portfolio`
  - `Formal + RO_EMA220_REENTRY_CLOSE_HOLD_3`
  - `Formal + RO_LOWVALUE_WEEKLY_RSI30_HOLD`
  - `Formal + RO_LOWVALUE_4H_RSI10_HOLD`

## Default Comparison

| System | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Avg Core Exposure% | Peak Total Exposure% | RiskOff Active% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Formal Portfolio | 1591.16 | 57.51 | 0.986 | 1.008 | -57.08 | 100.0 | 300.0 | 0.0 |
| Formal + RO_EMA220_REENTRY_CLOSE_HOLD_3 | nan | nan | 1.216 | nan | -47.86 | 58.0 | 300.0 | 42.2 |
| Formal + RO_LOWVALUE_WEEKLY_RSI30_HOLD | nan | nan | 1.261 | nan | -39.25 | 60.5 | 300.0 | 39.7 |
| Formal + RO_LOWVALUE_4H_RSI10_HOLD | nan | nan | 1.278 | nan | -46.27 | 61.1 | 300.0 | 39.2 |

## Delta Vs Formal Portfolio

| System | dReturn | dCalmar | dMaxDD | Stress dReturn | Stress dCalmar | Stress dMaxDD |
| --- | --- | --- | --- | --- | --- | --- |
| Formal + RO_EMA220_REENTRY_CLOSE_HOLD_3 | +nanpp | +nan | +9.22pp | +nanpp | +nan | +9.52pp |
| Formal + RO_LOWVALUE_WEEKLY_RSI30_HOLD | +nanpp | +nan | +17.83pp | +nanpp | +nan | +18.01pp |
| Formal + RO_LOWVALUE_4H_RSI10_HOLD | +nanpp | +nan | +10.81pp | +nanpp | +nan | +11.16pp |

## Default Path Burden

| System | Worst 3m Cluster% | Worst 6m Cluster% | Rolling 180d Worst MaxDD% | Rolling 365d Worst Return% | Longest Neg Month Streak |
| --- | --- | --- | --- | --- | --- |
| Formal Portfolio | -39.91 | -44.55 | -45.48 | -55.98 | 5 |
| Formal + RO_EMA220_REENTRY_CLOSE_HOLD_3 | -22.06 | -34.94 | -30.78 | -45.73 | 6 |
| Formal + RO_LOWVALUE_WEEKLY_RSI30_HOLD | -14.75 | -25.51 | -31.48 | -36.46 | 5 |
| Formal + RO_LOWVALUE_4H_RSI10_HOLD | -22.06 | -29.44 | -29.01 | -44.68 | 6 |

## Readout

- Best candidate on the latest base: `RO_LOWVALUE_WEEKLY_RSI30_HOLD`.
- Plot: `FORMAL_PLUS_RISKOFF_REENTRY_PLOTS.html`