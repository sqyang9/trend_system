# Full-Stack Risk-Off Re-Entry Audit

- Semantics: any non-normal Risk-Off state forces `Core + Sleeve #1 + Sleeve #2` into cash-like flat.
- Re-entry restores `Core` first; sleeves only participate when core is back on and their own native rules are active.

| System | Return% | CAGR% | Sharpe | Calmar | MaxDD% | RecoveryDays | Worst3m | Worst6m | AvgTotalExp% | AvgCoreExp% | RiskOffActive% | S1Active% | S2Active% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Formal Portfolio | 1591.16 | 57.51 | 0.986 | 1.008 | -57.08 | 463.5 | -39.91 | -44.55 | 136.85 | 100.00 | 0.00 | 25.12 | 11.73 |
| Formal + RO_LOWVALUE_WEEKLY_RSI30_HOLD | 6936.49 | 98.06 | 1.823 | 4.363 | -22.48 | 20.8 | -10.57 | -12.86 | 97.02 | 60.27 | 39.73 | 25.03 | 11.71 |
| Formal + RO_LOWVALUE_4H_RSI10_HOLD | 7013.10 | 98.40 | 1.835 | 3.646 | -26.99 | 86.8 | -12.00 | -15.50 | 97.57 | 60.82 | 39.18 | 25.03 | 11.71 |