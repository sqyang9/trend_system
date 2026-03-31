# Multi-Sleeve Chart Priority

## Priority Framework

Charts should be prioritized by operator usefulness, not by visual completeness.

Use three levels:

- `P1`: must-have
- `P2`: should-have
- `P3`: optional only if the first two levels are already clean

## P1: Must-Have Charts

### 1. Portfolio State Ribbon

Why:

- fastest way to answer what state the portfolio is in

Questions answered:

- core only or sleeves active?
- stacked or single-sleeve?
- near-cap or not?

### 2. Exposure Stack With Cap Line

Why:

- makes layered exposure and cap usage obvious

Questions answered:

- how much exposure comes from each layer?
- how close is the portfolio to `3.0x`?

### 3. Equity Curve + Underwater Curve

Why:

- the first path-burden chart

Questions answered:

- what is the realized path?
- how deep is the current burden?

### 4. Rolling 30d Contribution By Layer

Why:

- shows who is driving the current portfolio

Questions answered:

- is Core carrying?
- is Sleeve #1 driving gains?
- is Sleeve #2 offsetting pain?

### 5. Days Since Equity High

Why:

- simple and intuitive burden gauge

Questions answered:

- is the portfolio in a routine pullback or a long recovery wait?

## P2: Should-Have Charts

### 6. Rolling 90d Contribution By Layer

Why:

- smooths short-term noise and shows medium-horizon contribution mix

### 7. Rolling 180d Max DD

Why:

- shows recent path roughness better than headline max DD alone

### 8. Trailing 3m / 6m Cluster Loss

Why:

- captures pain clustering directly

### 9. Sleeve Activation / Overlap Map

Why:

- shows whether sleeves are acting independently or stacking persistently

### 10. Contribution By Phase Window

Why:

- shows what each layer did in:
  - `major_drawdown`
  - `sideways_volatility`
  - `recovery_phase`

## P3: Optional Charts

### 11. Overlap Duration Histogram

Use only if overlap behavior is operationally important.

### 12. Cap-Utilization Duration Distribution

Use only if high-use / pre-breach persistence becomes operationally relevant.

### 13. Sleeve Contribution Scatter

For example:

- `Sleeve #1 contribution` vs `Sleeve #2 contribution`

Useful only for deeper review, not for routine monitoring.

## Minimum Viable Chart Set

The minimum viable chart set is:

1. portfolio state ribbon
2. exposure stack with hard cap line
3. equity curve
4. underwater curve
5. rolling `30d` contribution by layer
6. days since equity high

This is the smallest set that still answers:

- what state are we in?
- how much are we exposed?
- who is contributing?
- how heavy is current path burden?

## Deliberately Omit

The following should be left out unless a later implementation round proves they are needed:

- breakout-repair lineage visuals
- rejected sleeve family comparison charts
- old Risk-Off comparison dashboards
- dense governance threshold heatmaps
- multi-page policy diagrams
- highly granular trade-level expectancy plots
- duplicate contribution panels for too many horizons

These add noise faster than they add operational clarity.

## Direct Answers

1. Highest-priority charts:
   - state ribbon
   - exposure stack
   - equity + underwater
   - rolling `30d` contribution
   - days since high

2. Quick-glance dashboard:
   - P1 only

3. Deeper diagnostic layer:
   - P2 plus selected P3

4. Most important for practical trading review:
   - current state
   - exposure layering
   - current path burden
   - recent contribution mix
   - overlap persistence

5. Unnecessary visuals:
   - frozen-line history charts
   - policy-heavy governance visuals
   - redundant horizon duplication
