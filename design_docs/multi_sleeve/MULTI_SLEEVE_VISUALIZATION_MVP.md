# Multi-Sleeve Visualization MVP

## Implemented P1 Charts

1. `Portfolio State Ribbon`
2. `Exposure Stack With 3.0x Cap Line`
3. `Equity Curve + Buy & Hold Overlay`
4. `Underwater Curve`
5. `BTC Candlestick Panel With B / S Markers`
6. `Rolling 30d Contribution By Layer`
7. `Days Since Equity High`

## Data Series Used

- `Portfolio State Ribbon`: `state_label`, `state_code`, `total_exposure`, `cap_headroom`
- `Exposure Stack`: `core_exposure`, `sleeve1_exposure`, `sleeve2_exposure`, `total_exposure`, hard cap `3.0x`
- `Equity Curve`: `portfolio_equity`, `buy_and_hold_equity` (`CoreOnly` proxy)
- `Underwater Curve`: `underwater_pct`
- `Candlestick Panel`: real `open`, `high`, `low`, `close` from BTC 4h data
- `B / S Markers`: `total_exposure_change`, with hover showing `sleeve1_exposure_change` and `sleeve2_exposure_change`
- `Rolling 30d Contribution`: `rolling_30d_contrib_core`, `rolling_30d_contrib_sleeve1`, `rolling_30d_contrib_sleeve2`
- `Days Since Equity High`: `days_since_high`

## Current Snapshot

- Latest timestamp: `2026-03-07 16:00 UTC`
- Current state: `Core-Only`
- Total exposure: `1.00x`
- Cap headroom: `2.00x`
- Current drawdown: `-33.44%`
- Days since high: `236.5`

## Supporting Export

- Timeseries CSV: `MULTI_SLEEVE_VISUALIZATION_MVP_TIMESERIES.csv`

## Deferred For Later

- P2: rolling `90d` contribution, rolling `180d` max DD, trailing `3m / 6m` cluster loss, sleeve activation / overlap map, contribution by phase window
- P3: overlap duration histogram, cap-utilization duration distribution, sleeve contribution scatter

## Intentionally Left Out

- frozen-line comparison visuals
- old Risk-Off dashboards
- policy-heavy governance diagrams
- redundant multi-horizon contribution panels
- decorative or archive-heavy research charts