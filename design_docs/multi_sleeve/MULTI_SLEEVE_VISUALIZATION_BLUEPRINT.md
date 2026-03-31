# Multi-Sleeve Visualization Blueprint

## Objective

This document defines the visualization layer for the formal BTC portfolio:

- `Core BTC holding`
- `Sleeve #1 = ConstAddOn[1.00x]`
- `Sleeve #2 = RangeRotation`
- approved hard total exposure cap = `3.0x`

The goal is not new research.
The goal is to make the approved portfolio easy to see, explain, monitor, and review.

## Visualization Architecture

The visualization layer should be organized into two levels:

### 1. Quick-Glance Dashboard

Purpose:

- answer the current-state question in seconds
- show layered exposure immediately
- show whether the portfolio is stacked, near-cap, or under path burden

Audience:

- trader
- operator
- daily reviewer

Time orientation:

- live / latest state
- trailing `30d`
- trailing `90d`
- current underwater state

### 2. Deeper Diagnostic Views

Purpose:

- explain why the dashboard looks the way it does
- show who contributed pnl
- show where path burden came from
- show whether sleeves are independent or stacked

Audience:

- weekly reviewer
- strategy operator
- post-period analyst

Time orientation:

- full sample
- major drawdown window
- recovery window
- sideways-volatility window
- recent rolling windows

## Core View Families

### A. Portfolio State View

This should visualize the operating state over time:

- `Core-Only`
- `Expansion-Carry`
- `Diversification-Carry`
- `Stacked Multi-Sleeve`
- `High-Use / Near-Cap`

Preferred form:

- horizontal state ribbon over time
- optional stacked color band under price / equity

Why it matters:

- shows what the system is actually doing
- makes sleeve ecology visible without reading logs

### B. Exposure Stack View

This should visualize:

- `Core exposure`
- `Sleeve #1 exposure`
- `Sleeve #2 exposure`
- `Total exposure`
- `Cap headroom`

Preferred form:

- stacked area for exposure layers
- hard cap line at `3.0x`
- shaded soft bands above `2.0x`, `2.5x`, `2.85x`

Why it matters:

- shows average vs peak exposure immediately
- makes stacked and near-cap behavior obvious

### C. Contribution View

This should visualize:

- cumulative pnl by layer
- rolling `30d` contribution by layer
- rolling `90d` contribution by layer
- phase contribution during `major_drawdown` and `sideways_volatility`

Preferred form:

- cumulative line chart for total contribution
- rolling bar / area panels for short and medium contribution
- phase summary table or compact facet bars

Why it matters:

- shows whether gains are coming from Core, Sleeve #1, or Sleeve #2
- makes the diversification role of `RangeRotation` visible

### D. Path-Burden View

This should visualize:

- equity curve
- underwater curve
- days since equity high
- rolling `180d` max DD
- trailing `3m` cluster loss
- trailing `6m` cluster loss

Preferred form:

- vertically aligned path-burden strip
- one shared time axis

Why it matters:

- turns abstract burden into something operators can read quickly
- shows whether current pain is routine or unusually persistent

### E. Activation / Overlap View

This should visualize:

- Sleeve #1 active periods
- Sleeve #2 active periods
- overlap periods
- stacked-state duration distribution

Preferred form:

- binary activation raster by sleeve
- overlap stripe
- histogram of contiguous overlap duration

Why it matters:

- shows when sleeves are independent
- shows when stacking is common or rare

## Recommended Page Structure

### Page 1: Dashboard

- state ribbon
- exposure stack
- equity + underwater
- rolling `30d` contribution
- key stat tiles

### Page 2: Contribution Diagnostics

- cumulative pnl by layer
- rolling `90d` contribution
- contribution by regime window

### Page 3: Path And Overlap Diagnostics

- days since equity high
- rolling `180d` max DD
- trailing `3m / 6m` cluster loss
- sleeve activation / overlap map
- overlap duration histogram

## Direct Answers

1. Highest-priority charts:
   - state ribbon
   - exposure stack with cap line
   - equity + underwater
   - rolling contribution by sleeve
   - activation / overlap map

2. Quick-glance dashboard:
   - latest state
   - exposure layers
   - cap headroom
   - current drawdown
   - days since high
   - recent sleeve contribution

3. Deeper diagnostics:
   - cumulative pnl decomposition
   - rolling contribution panels
   - drawdown / cluster-loss strip
   - overlap duration distribution

4. Practical trading review priority:
   - current state
   - current exposure
   - current burden
   - recent contribution mix
   - stacked / near-cap persistence

5. Visuals to omit:
   - low-value decorative regime charts
   - duplicate contribution views at too many horizons
   - policy-heavy governance diagrams on the dashboard
   - dense factor-level research visuals that do not help operators
