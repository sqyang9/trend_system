# Formal Mainline Launch Audit

## Decision

- Launch status for the current adopted mainline: `LAUNCH_GO`.
- Current mainline:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - `S1 + S2 ATR vol-targeting` enabled via `ATRVT_90D_med_035_150__ATRVT_60D_med_035_150`
    - `S1=ATRVT_90D_med_035_150`
    - `S2=ATRVT_60D_med_035_150`
  - `S1 gate contract = S1_VP_LB60_EA050_VR120`
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the high-churn gate earlier
  - override `Weekly RSI(14) <= 30 hold`

## Why Old `LAUNCH_NO_GO` Is Superseded

- The old `LAUNCH_NO_GO` was inherited from the single-mother Gatekeeper V2 process.
- That blocker was a legacy baseline-gate mismatch for a low-frequency trend mother, not a later portfolio-level adoption failure.
- The current formal mainline is a later adopted multi-layer portfolio and should be judged by its own adoption evidence.

## Evidence

- default: `Return 3321.25%`, `Calmar 3.209`, `MaxDD -23.81%`
- stress: `Return 3440.08%`, `Calmar 3.267`, `MaxDD -23.68%`
- harsher friction: `Return 3120.69%`, `Calmar 3.035`, `MaxDD -24.61%`

## Readout

- The adopted mainline remains clearly superior to the prior formal baseline across default, stress, and harsher friction.
- The structure question is closed: core-only Risk-Off retained, full-stack rejected.
- No remaining promotion blocker inside the adopted mainline prevents launch-go status at the repository baseline level.