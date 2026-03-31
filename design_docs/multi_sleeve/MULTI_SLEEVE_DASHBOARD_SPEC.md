# Multi-Sleeve Dashboard Spec

## Purpose

This file defines the quick-glance dashboard for the formal portfolio:

- `Core BTC holding`
- `Sleeve #1 = ConstAddOn[1.00x]`
- `Sleeve #2 = RangeRotation`

The dashboard should answer the current-state question first, not the research question first.

## Layout

Use a compact three-row layout.

### Row 1: State And Risk Tiles

Required tiles:

- `portfolio_state`
- `total_exposure`
- `cap_headroom`
- `cap_utilization_pct`
- `current_drawdown_pct`
- `days_since_equity_high`
- `sleeve1_active`
- `sleeve2_active`

Optional tiles:

- `soft_cap_band`
- `rolling_30d_portfolio_return_pct`

Display rules:

- tiles should be color-coded by state and burden
- avoid more than `8` primary tiles

### Row 2: Main Time-Series Panel

Required chart:

- combined panel with:
  - equity curve
  - underwater curve directly below
  - state ribbon below the shared time axis

Why:

- this is the fastest way to connect pnl, burden, and operating state

### Row 3: Exposure And Contribution Panels

Left panel:

- exposure stack area
- lines:
  - `total_exposure`
  - hard cap `3.0x`
  - optional soft thresholds `2.0x`, `2.5x`, `2.85x`

Right panel:

- rolling `30d` pnl contribution by:
  - `Core`
  - `Sleeve #1`
  - `Sleeve #2`

## Dashboard Charts

### Chart 1: Portfolio State Ribbon

States:

- `Core-Only`
- `Expansion-Carry`
- `Diversification-Carry`
- `Stacked Multi-Sleeve`
- `High-Use / Near-Cap`

Best form:

- categorical ribbon with distinct colors

### Chart 2: Exposure Stack

Series:

- `core_exposure`
- `sleeve1_exposure`
- `sleeve2_exposure`
- `total_exposure`

Overlays:

- cap line at `3.0x`
- shaded cap bands

Best form:

- stacked area with line overlay for total

### Chart 3: Equity + Underwater

Series:

- portfolio equity
- drawdown from equity high

Best form:

- top line chart + bottom filled drawdown chart

### Chart 4: Rolling 30d Contribution

Series:

- `Core 30d contribution`
- `Sleeve #1 30d contribution`
- `Sleeve #2 30d contribution`

Best form:

- grouped bars or signed stacked bars

## Dashboard Interaction Rules

- shared time cursor across all charts
- click legend to isolate one sleeve
- latest timestamp marker should be emphasized
- hovering the state ribbon should show:
  - state name
  - total exposure
  - cap headroom

## Minimum Viable Dashboard

If only the minimum dashboard is built, it must include:

1. state ribbon
2. exposure stack
3. equity curve
4. underwater curve
5. rolling `30d` contribution by layer
6. top tiles for state, exposure, cap headroom, drawdown, days since high

## What Not To Put On The Dashboard

- full-sample slice tables
- long governance text blocks
- detailed overlap histograms
- every rolling horizon at once
- research-only comparison charts versus legacy systems

Those belong in deeper diagnostics, not in the quick-glance layer.

## Direct Answers

1. Highest-priority dashboard charts:
   - state ribbon
   - exposure stack
   - equity + underwater
   - rolling `30d` contribution

2. What belongs in the quick-glance dashboard:
   - current state
   - current exposure and cap headroom
   - current path burden
   - recent contribution mix

3. What should stay out:
   - dense policy text
   - duplicate long-horizon charts
   - legacy research comparisons
