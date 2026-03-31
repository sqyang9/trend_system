# Sleeve 3 Discovery Reset Candidates

## Scope

- Formal default portfolio:
  - `Core BTC holding`
  - `Sleeve #1 = ConstAddOn[1.00x]`
  - `Sleeve #2 = RangeRotation`
  - `core-only Risk-Off overlay`
  - sell-side `EMA250`
  - re-entry `Weekly RSI(14) <= 30 hold`
- This round resets `Sleeve #3` discovery against the current adopted mainline.
- Goal: find a genuinely new `Sleeve #3` ecology.

## Current Remaining Environment Gaps

The current formal stack already covers:

- breakout / expansion capture
- drawdown / sideways-volatility / chop diversification
- core-level downside carry control with early oversold restoration

The most likely remaining gaps are:

1. `post_dislocation_recovery_transition`
2. `failed_downside_then_reacceptance`
3. `slow accepted grind-up after damage`

These are distinct from:

- `Sleeve #1` breakout impulse
- `Sleeve #2` chop rotation
- `Risk-Off` defensive overlay

## Candidate Families

| Priority | Family | What It Captures | Why It Is Not Sleeve #1 | Why It Is Not Sleeve #2 | Why It Is Not Risk-Off |
| --- | --- | --- | --- | --- | --- |
| 1 | `post_dislocation_repricing_climb` | After a major break or shock, market shifts from panic / dislocation into orderly repricing and multi-bar climb. | Not breakout-impulse dependent; should not need expansion-bar quality. | Not an inventory-rotation sleeve inside a stable range. | Not a defensive overlay; it is a participation sleeve after damage. |
| 2 | `failed_breakdown_reversal_acceptance` | Downside continuation fails, value is reclaimed, then accepted over multiple bars before participation. | Not upside expansion ecology. | Not lower-range oscillation or box-edge harvesting. | It is a re-entry participation ecology, not a risk-reduction state machine. |
| 3 | `reset_base_reacceptance_v2` | Market rebuilds a base after structural damage, then re-accepts above that rebuilt base. | It enters after reset and rebuild, not at first breakout release. | It acts after the old range has been broken and rebuilt, not while rotating inside a healthy range. | It is not about flatting exposure; it is about recovered acceptance. |
| 4 | `slow_drift_trend_persistence` | Slow, low-drama, accepted directional carry after the explosive phase is already over. | Not a breakout sleeve because it does not depend on compression / release or initial impulse. | Not a chop sleeve because it needs one-sided persistence rather than oscillation. | Not a risk-control overlay; it adds carry rather than removing exposure. |

## Why These Families Are Worth Testing

### `post_dislocation_repricing_climb`

- Most directly attacks the current stack's remaining path problem.
- It can matter where:
  - `Risk-Off` finished the defense job
  - `Sleeve #2` no longer has a chop edge
  - `Sleeve #1` still has not seen a clean expansion trigger
- This is the cleanest first test of a genuinely different recovery-transition ecology.

### `failed_breakdown_reversal_acceptance`

- Targets failed downside information, which the current stack does not explicitly monetize as a sleeve.
- Could help in the earliest post-damage acceptance windows without collapsing into pure oversold re-entry logic.
- Different failure mode from both `Sleeve #1` and `Sleeve #2`.

### `reset_base_reacceptance_v2`

- A refined restart of the older reset idea, but against the new official mainline rather than the older two-sleeve baseline.
- Still plausible for underwater-duration improvement.
- Lower priority because the earlier reset family was only directionally useful, not strong enough.

### `slow_drift_trend_persistence`

- Keeps a door open for an ecology that monetizes low-volatility continuation after the expansion phase.
- Useful only if it proves clearly distinct from breakout timing.
- Lower priority because it can easily collapse into a weaker relative of `Sleeve #1`.

## Direct Answers

1. Current formal portfolio most likely still lacks:
   `post-dislocation recovery transitions`, `failed-downside reacceptance`, and `slow accepted grind-up after damage`.

2. New candidate families:
   `post_dislocation_repricing_climb`, `failed_breakdown_reversal_acceptance`, `reset_base_reacceptance_v2`, `slow_drift_trend_persistence`.

3. Why each is orthogonal:
   each one aims at recovery / rebuild / failed-downside / slow-carry behavior, rather than breakout expansion, chop rotation, or defensive risk reduction.

4. First family to test:
   `post_dislocation_repricing_climb`.

5. Immediate rejection directions:
   breakout cousins, range-rotation cousins, repair wrappers, Risk-Off-in-disguise sleeves, and oversold re-entry sleeves repackaged as sleeve families.

6. One-line judgment:
   `Sleeve #3` should now move toward post-damage participation ecology, not a fourth variant of breakout, chop, or overlay timing.
