# Governance De-Risk Use Cases

## Purpose

This document defines the rare situations in which governance-led temporary de-risking is valid for the approved formal portfolio:

- `Core BTC holding`
- `Sleeve #1 = ConstAddOn[1.00x]`
- `Sleeve #2 = RangeRotation`
- approved hard total exposure cap = `3.0x`

This is not a new trading strategy.
This is not a reopening of the frozen `Risk-Off` line.
This is a portfolio governance intervention taxonomy.

## Design Principle

Governance-led de-risking is valid only when the concern is higher than normal portfolio operation:

- path burden is unusually heavy
- cap pressure is persistent and uncomfortable
- operational stability is impaired
- deployment posture temporarily requires caution

Normal drawdowns, normal sleeve overlap, and ordinary underwater behavior are not sufficient reasons by themselves.

## Valid Governance De-Risk Scenarios

### Scenario 1: `Path-Burden Escalation`

Governance concern:

- drawdown or underwater duration moves into the approved escalation zone
- recent clustered losses indicate that the portfolio is under abnormal practical burden even if strategy logic is unchanged

Why governance may intervene:

- the main portfolio risk at this stage is path burden, not lack of alpha
- governance may choose to temporarily reduce practical deployment stress while preserving the formal research baseline

What may be reduced:

- approved deployment posture
- sleeve layering intensity
- total gross exposure usage within the already-approved architecture

What may not be changed:

- mother strategy
- sleeve signal definitions
- execution tuples
- archived / frozen strategy lines

### Scenario 2: `Cap-Pressure Persistence`

Governance concern:

- the portfolio spends repeated time in `High-Use` or `Pre-Breach` exposure bands
- dual-sleeve stacking persists while path burden is also elevated

Why governance may intervene:

- even without a hard-cap breach, repeated thin cap headroom may be judged operationally uncomfortable
- governance may want to reduce pressure before a formal breach occurs

What may be reduced:

- temporary deployment posture for one or both sleeves
- tolerance for stacked state duration

What may not be changed:

- hard cap definition by stealth
- sleeve activation logic
- any rejected cap-research branch

### Scenario 3: `Operational Instability`

Governance concern:

- live implementation, execution plumbing, reporting, or reconciliation is unstable
- state classification or exposure tracking is temporarily unreliable

Why governance may intervene:

- architecture integrity matters more than forcing full deployment through an unstable operating environment

What may be reduced:

- live deployment posture
- stacked sleeve usage
- incremental sleeve exposure while operations stabilize

What may not be changed:

- strategy logic
- signal logic
- research status of frozen lines

### Scenario 4: `Exceptional Deployment Caution`

Governance concern:

- a non-research oversight body chooses temporary caution due to mandate, mandate transition, capital governance, or implementation rollout phase

Why governance may intervene:

- governance sometimes needs a temporary posture change even when the research stack remains valid

What may be reduced:

- approved live posture
- incremental sleeve usage

What may not be changed:

- research conclusions
- formal portfolio ranking
- archived branch status

## What Is Not A Valid De-Risk Scenario

These do not justify governance-led de-risking by themselves:

- a normal pullback inside the audited burden envelope
- simple discomfort with volatility
- a desire to improve backtest appearance
- a hidden wish to restart `Risk-Off`
- a hidden wish to turn governance alerts into timing signals

## Allowed Reduction Targets

Governance may reduce only deployment posture, not research logic.

Valid reduction targets:

- temporary reduction of `Sleeve #1`
- temporary reduction of `Sleeve #2`
- temporary reduction of both sleeves
- temporary reduction of maximum stacked deployment

Invalid reduction targets:

- modifying the core holding logic
- rewriting sleeve triggers
- inserting a new signal gate
- converting governance review into automated alpha logic

## Intervention Philosophy

The correct interpretation is:

- governance de-risking is a rare deployment overlay
- it is explicit
- it is review-driven
- it is reversible

It is not:

- a covert `Risk-Off` strategy
- a new regime model
- an informal strategy rewrite
