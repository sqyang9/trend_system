# Formal Mainline Launch Audit

## Decision

- Launch status for the current adopted mainline: `LAUNCH_GO`.
- Current mainline:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - override `Weekly RSI(14) <= 30 hold`

## Why Old `LAUNCH_NO_GO` Is Superseded

- The old `LAUNCH_NO_GO` was inherited from the single-mother Gatekeeper V2 process.
- That blocker was a legacy baseline-gate mismatch for a low-frequency trend mother, not a later portfolio-level adoption failure.
- The current formal mainline is a later adopted multi-layer portfolio and should be judged by its own adoption evidence.

## Evidence

- default: `Return 2878.61%`, `Calmar 2.854`, `MaxDD -25.41%`
- stress: `Return 3011.58%`, `Calmar 2.967`, `MaxDD -24.84%`
- harsher friction: `Return 2659.65%`, `Calmar 2.643`, `MaxDD -26.64%`

## Readout

- The adopted mainline remains clearly superior to the prior formal baseline across default, stress, and harsher friction.
- The structure question is closed: core-only Risk-Off retained, full-stack rejected.
- No remaining promotion blocker inside the adopted mainline prevents launch-go status at the repository baseline level.