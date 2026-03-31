# Formal Mainline Rolling Start Audit

- Scope: start-date sensitivity test on the current official mainline.
- Mainline under test:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - sell-side `EMA250`
  - re-entry `Weekly RSI(14) <= 30 hold`
  - posture `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`

## Full-Sample Reference

- Return: `2705.88%`
- Calmar: `2.021`
- MaxDD: `-35.06%`
- Worst 3m cluster: `-14.84%`
- Worst 6m cluster: `-19.41%`
- Recovery from max DD: `327.7 days`

## Monthly Start Summary

- Monthly start points tested: `74`
- Best Calmar start: `2020-01-01` -> `2.048`
- Worst Calmar start: `2026-02-01` -> `-1.722`
- Best 12m start: `2020-04-01` -> `600.31%`
- Worst 12m start: `2022-01-01` -> `-24.21%`

## Annual Start Readout

| Start | 1M | 3M | 6M | 12M | TotalReturn | Calmar | MaxDD | Worst3m | Worst6m | RecoveryDays | AvgTotalExp | dCalmar vs Full | dMaxDD vs Full |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2020-01-01 | 74.84% | 69.62% | 129.79% | 539.67% | 2735.52% | 2.048 | -35.06% | -14.84% | -19.41% | 327.6666666666667 | 97.22% | +0.027 | +0.00pp |
  Chart: [2020-01-01](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/formal_mainline_rolling_start_charts/rolling_start_2020-01-01.html)
| 2021-01-01 | -1.28% | 85.70% | 62.65% | 87.14% | 343.28% | 0.950 | -35.06% | -14.84% | -19.41% | 327.6666666666667 | 90.62% | -1.071 | +0.00pp |
  Chart: [2021-01-01](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/formal_mainline_rolling_start_charts/rolling_start_2021-01-01.html)
| 2022-01-01 | -0.00% | -8.24% | -7.67% | -24.21% | 136.86% | 0.813 | -28.19% | -14.84% | -19.41% | 61.0 | 87.76% | -1.208 | +6.87pp |
  Chart: [2022-01-01](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/formal_mainline_rolling_start_charts/rolling_start_2022-01-01.html)
| 2023-01-01 | 31.68% | 39.38% | 41.23% | 68.69% | 212.54% | 1.669 | -25.82% | -14.84% | -16.92% | 56.0 | 101.73% | -0.353 | +9.23pp |
  Chart: [2023-01-01](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/formal_mainline_rolling_start_charts/rolling_start_2023-01-01.html)
| 2024-01-01 | -4.14% | 54.19% | 32.88% | 78.00% | 85.28% | 1.265 | -25.82% | -14.84% | -16.92% | 56.0 | 100.91% | -0.756 | +9.23pp |
  Chart: [2024-01-01](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/formal_mainline_rolling_start_charts/rolling_start_2024-01-01.html)
| 2025-01-01 | 1.03% | -3.26% | 12.95% | 8.03% | 4.09% | 0.147 | -23.58% | -11.21% | -13.38% | 11.5 | 80.46% | -1.875 | +11.48pp |
  Chart: [2025-01-01](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/formal_mainline_rolling_start_charts/rolling_start_2025-01-01.html)
| 2026-01-01 | -2.17% | -3.65% | -3.65% | -3.65% | -3.65% | -1.501 | -12.45% | 0.00% | 0.00% | 11.5 | 79.37% | -3.522 | +22.61pp |
  Chart: [2026-01-01](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/formal_mainline_rolling_start_charts/rolling_start_2026-01-01.html)