# Formal Mainline Launch Audit

## Decision

- Launch status for the current adopted mainline: `LAUNCH_GO`.
- Current mainline:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - sell-side `EMA250`
  - re-entry `Weekly RSI(14) <= 30 hold`

## Why Old `LAUNCH_NO_GO` Is Superseded

- The old `LAUNCH_NO_GO` was inherited from the single-mother Gatekeeper V2 process.
- That blocker was a legacy baseline-gate mismatch for a low-frequency trend mother, not a later portfolio-level adoption failure.
- The current formal mainline is a later adopted multi-layer portfolio and should be judged by its own adoption evidence.

## Evidence

- default: `Return 2705.88%`, `Calmar 2.021`, `MaxDD -35.06%`
- stress: `Return 2862.36%`, `Calmar 2.086`, `MaxDD -34.69%`
- harsher friction: `Return 2440.06%`, `Calmar 1.856`, `MaxDD -36.71%`

## Readout

- The adopted mainline remains clearly superior to the prior formal baseline across default, stress, and harsher friction.
- The structure question is closed: core-only Risk-Off retained, full-stack rejected.
- No remaining promotion blocker inside the adopted mainline prevents launch-go status at the repository baseline level.