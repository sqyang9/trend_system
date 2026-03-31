# Sleeve 3 Complementarity Hypotheses

## Objective

This file records the portfolio-level hypotheses that should be tested in `Phase T2`.

The comparison target is not standalone beauty. It is incremental usefulness on top of:

- `Core BTC holding + ConstAddOn[1.00x] + RangeRotation`

## Existing Two-Sleeve Map

### Sleeve #1: `ConstAddOn[1.00x]`

- ecology: breakout / expansion
- job: main gain sleeve
- likely weak when:
  - move quality is damaged
  - post-reset structure is messy
  - breakout impulse is absent

### Sleeve #2: `RangeRotation`

- ecology: range rotation / chop diversification
- job: drawdown / sideways-volatility / dull path helper
- likely weak when:
  - old range structure is already broken
  - market is in rebuild mode rather than oscillation mode
  - transition is too directional for chop, but too late / messy for breakout

## T2 Hypotheses By Candidate

### `reset_base_reacceptance`

Hypothesis:

- adds value in the zone between “violent reset is over” and “clean breakout expansion has returned”
- should overlap only moderately with Sleeve #1 and less with Sleeve #2
- should help shorten underwater exit path rather than dominate bull expansion

What would count as success:

- positive portfolio delta on top of the current two-sleeve stack
- visible improvement in recovery-transition segments
- acceptable overlap with Sleeve #1 and Sleeve #2

Main failure mode:

- turns out to be just a slower breakout sleeve with worse timing

### `failed_breakdown_acceptance`

Hypothesis:

- adds value when downside continuation fails and BTC re-enters prior value
- should be more orthogonal to Sleeve #1 than any upside breakout cousin
- should help in dislocation aftermath where Sleeve #2 may still be too early or too range-dependent

What would count as success:

- positive contribution in major dislocation windows
- useful active windows while Sleeve #1 is flat / late
- portfolio help in underwater-repair phases

Main failure mode:

- becomes a narrative-only reversal sleeve with weak return-source quality

### `dislocation_repricing_rebuild`

Hypothesis:

- adds value in messy post-shock normalization where the market is rebuilding rather than rotating
- should improve path smoothness after the worst structural damage
- should have distinct clustering from both existing sleeves

What would count as success:

- broad enough contribution across multiple post-shock episodes
- modest overlap with the current sleeves
- portfolio help in long underwater segments

Main failure mode:

- too broad and fuzzy, with no robust trigger ecology

### `trend_drift_persistence`

Hypothesis:

- adds value during accepted slow uptrend carry after expansion energy fades
- should complement Sleeve #1 if it captures the “middle of the move” rather than the breakout
- should complement Sleeve #2 by participating in directional drift rather than box rotation

What would count as success:

- positive layering on dull-but-directional periods
- contribution broad enough to offset likely bull-overlap concerns
- clear distinction from breakout timing

Main failure mode:

- collapses into a weaker version of Sleeve #1 and ends up redundant

## T2 Prioritization Logic

### First test

`reset_base_reacceptance`

Why:

- highest relevance to the remaining path burden
- cleanest distinction from both existing sleeves
- best balance between structural clarity and portfolio need

### Second test

`failed_breakdown_acceptance`

Why:

- strongest alternate ecology if the portfolio still needs post-dislocation help

### Third test

`dislocation_repricing_rebuild`

Why:

- highest potential path value, but also the highest risk of vague definition

### Fourth test

`trend_drift_persistence`

Why:

- potentially useful, but most exposed to redundancy with Sleeve #1

## Immediate Non-Starters For T2

Do not test these as Sleeve #3 candidates:

- breakout cousins
- squeeze-release cousins
- breakout grading / repair wrappers
- range-rotation micro-variants
- reclaim wrappers that are just renamed versions of rejected `pullback_reclaim_continuation`
- failed-breakout timing repairs that are still breakout ecology in disguise
