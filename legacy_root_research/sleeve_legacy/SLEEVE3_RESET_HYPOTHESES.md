# Sleeve 3 Reset Complementarity Hypotheses

## Formal Baseline

- `Core BTC holding`
- `Sleeve #1 = ConstAddOn[1.00x]`
- `Sleeve #2 = RangeRotation`
- `core-only Risk-Off overlay`
- sell-side `EMA250`
- re-entry `Weekly RSI(14) <= 30 hold`

## What A Valid Sleeve #3 Must Add

A valid new `Sleeve #3` must do at least one of the following without collapsing into an existing family:

- improve recovery-transition participation after major damage
- improve underwater-duration exit quality
- add a new return source in post-dislocation rebuilding windows
- smooth path behavior in environments that are neither breakout expansion nor chop rotation

## Family Hypotheses

### `post_dislocation_repricing_climb`

Hypothesis:

- After large structural damage, the market often enters a repricing-and-climb phase before clean breakout ecology reappears.
- The current stack can still be under-participative there because:
  - `Risk-Off` already finished the defense job
  - `Sleeve #2` loses edge as rotation fades
  - `Sleeve #1` may still wait for a cleaner impulse setup

Expected complementarity:

- low overlap with `Sleeve #1`
- low overlap with `Sleeve #2`
- strongest help in post-dislocation and early normalized recovery windows

### `failed_breakdown_reversal_acceptance`

Hypothesis:

- Failed downside continuation creates a real directional edge if acceptance persists after reclaim.
- This is not the same as oversold re-entry because it would require market acceptance, not just panic depth.

Expected complementarity:

- meaningful help after bear-trap or exhaustion breakdowns
- more recovery-sensitive than `Sleeve #2`
- less impulse-dependent than `Sleeve #1`

### `reset_base_reacceptance_v2`

Hypothesis:

- The old reset logic may be more useful when judged against the current stronger formal stack, especially if the target problem is now framed as underwater-duration relief rather than generic alpha.

Expected complementarity:

- modest overlap with the current stack
- possible improvement in long underwater exits
- probably smaller or narrower than the top two families

### `slow_drift_trend_persistence`

Hypothesis:

- Some BTC phases are not explosive enough for `Sleeve #1` and not rotational enough for `Sleeve #2`, but still offer slow persistent directional carry.

Expected complementarity:

- possible incremental help in dull but accepted uptrends
- risk of degenerating into a slower breakout cousin

## Priority Readout

Priority for the next T2-style audit:

1. `post_dislocation_repricing_climb`
2. `failed_breakdown_reversal_acceptance`
3. `reset_base_reacceptance_v2`
4. `slow_drift_trend_persistence`

## What Should Stay Excluded

- breakout / squeeze cousins
- breakout grading / repair wrappers
- range-rotation micro-variants
- mean-reversion box-edge cousins
- oversold re-entry families pretending to be sleeves
- governance / risk posture overlays packaged as sleeves
