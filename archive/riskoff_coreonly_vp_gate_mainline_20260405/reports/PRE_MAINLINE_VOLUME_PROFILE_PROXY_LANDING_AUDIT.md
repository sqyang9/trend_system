# Pre-Mainline Volume-Profile Proxy Landing Audit

- Scope: landing-readiness audit for `vp_lb60_ea50_vr120`.
- Boundary: current official mainline remains unchanged.
- Signal verdict: `GO`
- Landing readiness: `NO_GO` without implementation
- Promotion recommendation: `GO_AFTER_IMPLEMENTATION`

## Locked Challenger

- Candidate: `vp_lb60_ea50_vr120`
- Meaning:
  - `lookback = 60 bars`
  - `HVN escape = 0.50 ATR`
  - `volume ratio20 = 1.20`
- Role:
  - apply a `volume-profile proxy gate` only to `S1`
  - current `Core` and `S2` remain unchanged

## Why It Is Promotion-Worthy

- Default:
  - `3321.25 / Sharpe 1.386 / Calmar 3.209 / MaxDD -23.81`
  - vs current official mainline:
    - `dReturn +141.34pp`
    - `dSharpe +0.049`
    - `dCalmar +0.337`
    - `dMaxDD +2.38pp`
- Stress and harsh both also improve.
- Annual starts:
  - Return `7/7` better
  - Sharpe `6/7` better
  - Calmar `7/7` better
  - MaxDD `7/7` better
- Freeze-date OOS:
  - `wf_2023_plus` positive on return / Sharpe / Calmar / MaxDD
  - `wf_2025_plus` positive on return / Sharpe / Calmar / MaxDD

## Main Landing Blockers

1. `S1` has no canonical gate contract yet.
   - Current formal path only knows sleeve weights and ATRVT scaling.
   - It does not know how to express:
     - `S1 gate enabled`
     - `vp lookback`
     - `vp escape atr`
     - `vp volume ratio`
   - So the adopted posture surface cannot currently carry this candidate.

2. Formal replay has no shared `S1 gate reason` trace.
   - The current bundle exposes:
     - `Core` gate state
     - `ATRVT` scales
     - `HV` / instability state
   - But not:
     - `S1 candidate seen`
     - `S1 blocked by vp gate`
     - `S1 passed vp gate`
   - Without this trace, promotion would be hard to debug and hard to audit.

3. Live/dashboard schema would silently under-explain behavior.
   - Current live and dashboard surfaces expose:
     - `core_reentry_gate`
     - `core_instability_state`
     - `atr_scale_s1 / atr_scale_s2`
   - They do not expose any `S1 gate` context.
   - If promoted as-is, operators would see fewer `S1` activations with no explanation.

4. Historical atlas cannot show `vp-blocked` zones or events.
   - The atlas currently marks:
     - `Core FLAT spans`
     - `high churn` amber bands
     - `S1/S2` entry/exit events
   - It does not mark where an `S1` breakout was seen but blocked by the `vp gate`.
   - That makes visual post-mortem incomplete.

## Required Implementation Surface

### 1. Shared Formal Contract

Add a canonical `S1 gate` contract in the formal path, parallel to the current ATRVT contract.

Minimum fields:

- `s1_gate_family`
- `s1_gate_enabled`
- `s1_vp_lookback`
- `s1_vp_escape_atr`
- `s1_vp_volume_ratio`
- `s1_gate_label`

Recommended initial adopted label:

- `S1_VP_LB60_EA050_VR120`

### 2. Bundle / Replay Output

`base_bundle()` / `simulate_weight_combo()` should expose at least:

- `s1_gate_active`
- `s1_gate_pass`
- `s1_gate_reason`
- `s1_vp_hvn_escape_atr`
- `s1_vp_volume_ratio20`

Reason labels should stay simple:

- `pass`
- `fail_hvn_escape`
- `fail_volume_ratio`
- `fail_both`
- `not_applicable`

### 3. Live / Dashboard

Extend live snapshot and dashboard payload with:

- `s1_gate_label`
- `s1_gate_pass`
- `s1_gate_reason`
- `s1_vp_hvn_escape_atr`
- `s1_vp_volume_ratio20`

This is enough for operators to understand why `S1` did or did not engage.

### 4. Atlas

Add one lightweight visual convention:

- mark `vp-blocked S1 candidate bars` with a muted symbol or band

Do not overload the chart.
It only needs to make “breakout seen but filtered” visually legible.

## Non-Blockers

- `Core` path does not need redesign.
- `S2` does not need redesign.
- `HV85` / high-churn logic does not conflict with this candidate.
- Current asymmetric ATRVT contract can remain unchanged.

## Implementation Risk

- Low-to-medium.
- Most work is schema and replay plumbing, not signal invention.
- The main risk is introducing inconsistent `S1 gate` semantics across:
  - formal replay
  - live panel
  - dashboard
  - atlas

## Verdict

- Signal quality: `GO`
- Operational explainability in current mainline stack: `NOT READY`
- Landing verdict: `GO_AFTER_IMPLEMENTATION`

## Recommended Next Step

Do one implementation pass only:

1. add shared `S1 gate` contract
2. wire `vp_lb60_ea50_vr120` into formal replay
3. expose gate reason in live/dashboard
4. add minimal atlas marking
5. then run one final promotion replay before any mainline switch
