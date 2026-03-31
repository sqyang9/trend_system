# Risk-Off Low-Value Re-Entry Report

## Scope

- Base mainline remains `RO_EMA220_REENTRY_CLOSE_HOLD_3`.
- Each candidate only adds a low-value override-hold re-entry after flat.
- Sell-side Risk-Off logic remains unchanged.

## Candidate Table

| Candidate | Trigger Count | Strict OOS | Avg dReturn | Avg dCalmar | Bull dReturn | Recovery dReturn | Major Drawdown dMaxDD | Return% | Calmar | MaxDD% | Avg Core Exposure% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RO_EMA220_REENTRY_CLOSE_HOLD_3 | 0 | 0.67 | -11.07pp | -0.051 | -181.72pp | -61.57pp | +14.05pp | 1821.45 | 1.034 | -58.78 | 58.0 |
| RO_LOWVALUE_WEEKLY_RSI35_HOLD | 1427 | 0.67 | -8.80pp | +0.052 | -77.65pp | -51.50pp | +11.62pp | 1872.77 | 1.007 | -61.02 | 67.1 |
| RO_LOWVALUE_WEEKLY_RSI30_HOLD | 377 | 0.67 | -9.86pp | -0.033 | -181.72pp | -57.08pp | +25.54pp | 2408.33 | 1.431 | -47.38 | 60.5 |
| RO_LOWVALUE_DAILY_RSI15_HOLD | 6 | 0.67 | -11.43pp | -0.057 | -74.25pp | -62.89pp | +14.26pp | 1696.71 | 1.008 | -58.57 | 59.2 |
| RO_LOWVALUE_4H_RSI10_HOLD | 12 | 0.67 | +3.87pp | +0.518 | -181.72pp | +8.25pp | +15.98pp | 2489.61 | 1.212 | -56.67 | 61.1 |
| RO_LOWVALUE_EMA220_ATR_DISLOCATION | 2337 | 0.67 | +13.29pp | +0.794 | +68.53pp | -8.54pp | -2.68pp | 1315.91 | 0.705 | -75.28 | 90.8 |
| RO_LOWVALUE_PANIC_RANGE_EXPANSION | 270 | 0.67 | +8.26pp | +0.317 | +1.06pp | -37.07pp | -4.01pp | 2484.63 | 0.896 | -76.61 | 84.3 |
| RO_LOWVALUE_RANGE_BOTTOM_PERCENTILE | 215 | 0.67 | +14.93pp | +0.590 | -123.13pp | -30.85pp | -3.65pp | 1111.87 | 0.647 | -76.25 | 88.1 |
| RO_LOWVALUE_BB_ZSCORE | 298 | 0.67 | +18.74pp | +1.456 | -142.88pp | -12.55pp | +2.47pp | 1456.16 | 0.790 | -70.15 | 89.7 |
| RO_LOWVALUE_FLUSH_REVERSAL | 77 | 0.67 | +3.76pp | +0.213 | -127.21pp | -56.58pp | -1.71pp | 2127.15 | 0.870 | -74.32 | 77.2 |
| RO_LOWVALUE_DRAWDOWN_60D | 1946 | 0.67 | -0.21pp | +1.206 | -211.46pp | -70.10pp | +7.73pp | 1524.09 | 0.871 | -64.90 | 76.9 |

## Equity Curves

- HTML: `RISK_OFF_LOWVALUE_REENTRY_EQUITY_CURVES.html`