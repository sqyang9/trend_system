# Risk-Off Structure Screen

- Purpose: screen `core-only Risk-Off` vs `full-stack cash-like Risk-Off` on the current formal portfolio.
- Base architecture fixed: `Core + ConstAddOn[1.00x] + RangeRotation`.
- Re-entry candidates fixed: `RO_LOWVALUE_WEEKLY_RSI30_HOLD`, `RO_LOWVALUE_4H_RSI10_HOLD`.

## Default

| System | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgTotalExp% | RiskOffActive% | S1Active% | S2Active% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Formal | 1591.16 | 1.008 | -57.08 | -39.91 | -44.55 | 463.5 | 136.85 | 0.00 | 25.12 | 11.73 |
| CoreOnly + Weekly30 | 3036.06 | 1.884 | -39.25 | -14.75 | -25.51 | 329.3 | 97.39 | 39.73 | 25.12 | 11.73 |
| FullStack + Weekly30 | 2722.96 | 1.747 | -40.66 | -15.26 | -27.29 | 329.2 | 96.94 | 39.73 | 24.67 | 12.01 |
| CoreOnly + 4H10 | 3117.34 | 1.614 | -46.27 | -22.06 | -29.44 | 376.0 | 97.94 | 39.18 | 25.12 | 11.73 |
| FullStack + 4H10 | 2799.57 | 1.487 | -48.26 | -24.38 | -31.81 | 376.0 | 97.49 | 39.18 | 24.67 | 12.01 |

## Stress Delta Vs Formal

| System | dReturn | dCalmar | dMaxDD | dWorst3m | dWorst6m | dRecoveryDays |
| --- | --- | --- | --- | --- | --- | --- |
| CoreOnly + Weekly30 | +1613.81pp | +0.927 | +18.01pp | +25.47pp | +19.24pp | -134.3 |
| FullStack + Weekly30 | +1254.84pp | +0.778 | +16.55pp | +24.96pp | +17.47pp | -134.3 |
| CoreOnly + 4H10 | +1721.53pp | +0.656 | +11.16pp | +18.41pp | +15.94pp | -109.3 |
| FullStack + 4H10 | +1354.81pp | +0.518 | +9.11pp | +16.10pp | +13.70pp | -87.5 |

## Structure Readout

- If full-stack wins, the edge is coming from flattening the whole portfolio ecology, not just the core.
- If core-only wins, the edge is mainly a core carry timing fix and sleeves should remain independent.