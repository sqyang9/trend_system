# Hybrid Parameter Screen

- Scope: only test two parameter classes for the promoted hybrid qualification.
- Tuned dimensions:
  - breakout window length
  - high-churn trigger thresholds
- Fixed:
  - sell-side `EMA250`
  - stable-environment `close3` full recovery
  - high-churn gate family `strict EMA50 AND breakout`
  - `weekly_rsi30_hold` override

## Default Summary

| Candidate | Return% | Calmar | MaxDD% | Full RE | HC quick 14d | HC quick 30d |
| --- | --- | --- | --- | --- | --- | --- |
| HC 2/3 + breakout_4 | 2459.02 | 2.352 | -29.06 | 38 | 31.8% | 54.5% |
| HC 2/3 + breakout_3 | 2320.71 | 2.299 | -29.09 | 37 | 33.3% | 52.4% |
| HC 2/3 + breakout_6 | 2213.97 | 2.238 | -29.34 | 38 | 31.8% | 54.5% |
| HC 2/3 + breakout_5 | 2260.41 | 2.225 | -29.75 | 38 | 31.8% | 54.5% |
| HC 2/4 + breakout_4 | 2120.36 | 2.042 | -31.61 | 43 | 27.8% | 50.0% |
| HC 3/4 + breakout_4 | 1952.30 | 1.977 | -31.61 | 46 | 27.8% | 50.0% |
| HC 3/5 + breakout_4 | 1952.30 | 1.977 | -31.61 | 46 | 27.8% | 50.0% |

## Readout

- Current promotion point `HC 2/3 + breakout_4`: Return `2459.02%`, Calmar `2.352`, MaxDD `-29.06%`.
- Best point in this lightweight screen: `HC 2/3 + breakout_4` with Return `2459.02%`, Calmar `2.352`, MaxDD `-29.06%`.
- Conclusion: the current promotion point remains the best or tied-best practical setting in this screen.

## Recent Windows


### HC 2/3 + breakout_3

- 2024-12_to_2025-06: short 14d / 30d = `2` / `3`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `3` / `3`, high-churn short 14d / 30d = `2` / `2`

### HC 2/3 + breakout_4

- 2024-12_to_2025-06: short 14d / 30d = `2` / `3`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `3` / `3`, high-churn short 14d / 30d = `2` / `2`

### HC 2/3 + breakout_5

- 2024-12_to_2025-06: short 14d / 30d = `2` / `3`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `3` / `3`, high-churn short 14d / 30d = `2` / `2`

### HC 2/3 + breakout_6

- 2024-12_to_2025-06: short 14d / 30d = `2` / `3`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `3` / `3`, high-churn short 14d / 30d = `2` / `2`

### HC 2/4 + breakout_4

- 2024-12_to_2025-06: short 14d / 30d = `2` / `3`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `4` / `4`, high-churn short 14d / 30d = `2` / `2`

### HC 3/4 + breakout_4

- 2024-12_to_2025-06: short 14d / 30d = `3` / `4`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `4` / `4`, high-churn short 14d / 30d = `2` / `2`

### HC 3/5 + breakout_4

- 2024-12_to_2025-06: short 14d / 30d = `3` / `4`, high-churn short 14d / 30d = `0` / `1`
- 2025-06_to_2025-12: short 14d / 30d = `4` / `4`, high-churn short 14d / 30d = `2` / `2`