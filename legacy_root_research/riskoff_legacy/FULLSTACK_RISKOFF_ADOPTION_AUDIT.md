# Full-Stack Risk-Off Adoption Audit

- Semantics: full-stack cash-like Risk-Off. `Core + Sleeve #1 + Sleeve #2` all flatten when Risk-Off is active.
- Re-entry restores core first; sleeves only participate when core is on and fresh native trades occur.

## Default

| System | Return% | CAGR% | Sharpe | Calmar | MaxDD% | RecoveryDays | Worst3m | Worst6m | AvgTotalExp% | AvgCoreExp% | RiskOffActive% | S1Active% | S2Active% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Formal Portfolio | 1591.16 | 57.51 | 0.986 | 1.008 | -57.08 | 463.5 | -39.91 | -44.55 | 136.85 | 100.00 | 0.00 | 25.12 | 11.73 |
| Formal + RO_LOWVALUE_WEEKLY_RSI30_HOLD | 2722.96 | 71.03 | 1.198 | 1.747 | -40.66 | 329.2 | -15.26 | -27.29 | 96.94 | 60.27 | 39.73 | 24.67 | 12.01 |
| Formal + RO_LOWVALUE_4H_RSI10_HOLD | 2799.57 | 71.76 | 1.215 | 1.487 | -48.26 | 376.0 | -24.38 | -31.81 | 97.49 | 60.82 | 39.18 | 24.67 | 12.01 |

## Stress Delta Vs Formal

| System | Stress dReturn | Stress dCalmar | Stress dMaxDD | Stress dRecoveryDays |
| --- | --- | --- | --- | --- |
| Formal + RO_LOWVALUE_WEEKLY_RSI30_HOLD | +1254.84pp | +0.778 | +16.55pp | -134.3 |
| Formal + RO_LOWVALUE_4H_RSI10_HOLD | +1354.81pp | +0.518 | +9.11pp | -87.5 |