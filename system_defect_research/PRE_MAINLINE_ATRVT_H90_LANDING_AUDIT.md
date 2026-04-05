# Pre-Mainline ATRVT H90 Landing Audit

## Verdict

- Signal layer: `GO`
- Landing readiness: `NO_GO` without implementation and document repair
- Promotion recommendation: `GO_AFTER_REPAIR`

## What Changed

- This audit is not a new Core gate study.
- Core side is held fixed at the current combo structure:
  - `EMA250` sell-side
  - stable `close3`
  - high-churn `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the stricter gate earlier
- The only change is the ATR vol-targeting reference:
  - current shared mainline implementation: `180d median / 0.35-1.50`
  - challenger: `90d median / 0.35-1.50`

## Promotion Evidence

- Current repaired combo base replay:
  - `Return 2946.79% / Calmar 2.574 / MaxDD -28.41%`
- `ATRVT H90` challenger:
  - `Return 3114.74% / Calmar 2.762 / MaxDD -27.02%`
- Default delta vs repaired combo base:
  - `dReturn +167.95pp`
  - `dCalmar +0.188`
  - `dMaxDD +1.39pp`
- Stress delta:
  - `dCalmar +0.189`
- Harsh delta:
  - `dCalmar +0.171`
- `W06 DD/Exp`:
  - base `-46.9%`
  - `H90 -44.0%`
- Annual starts vs repaired combo base:
  - Calmar better `6/7`
  - MaxDD better `7/7`
  - Return better `4/7`

Source: `system_defect_research/ATRVT_H90_AUDITION.md`

## Landing Blockers

1. Shared ATR background is still hard-coded to the old `180d median` spec.
   - `volatility_background.py` exposes only:
     - `PCTL_LOOKBACK_BARS = 180 * 6`
     - `ATR_SCALE_MIN = 0.35`
     - `ATR_SCALE_MAX = 1.50`
   - `build_volatility_background()` has no canonical config surface for:
     - ATR reference horizon
     - ATR reference statistic
     - asymmetric `S1 / S2` scaling
   - As a result, `H90` currently exists only inside research scripts, not the shared mainline API.

2. Formal portfolio path can only toggle ATRVT on or off, not specify which ATRVT spec is adopted.
   - `v123_formal_launch_and_layer2_weight_audit.py` currently uses:
     - `atr_vol_target_s1: True/False`
     - `atr_vol_target_s2: True/False`
   - It cannot encode:
     - `90d median`
     - future alternate clip bands
     - future `S1 / S2` asymmetry

3. Live and dashboard surfaces report the ATR scale value, but not the ATRVT contract.
   - `live_operating_layer/v132_live_operating_layer.py`
   - `live_operating_layer/mainline_live_status.py`
   - `dashboard/signal_layer.py`
   - Current output tells the operator:
     - current `atr_scale`
     - current `hv_pct_180d`
   - It does not tell the operator:
     - which ATRVT regime is active
     - whether the adopted mainline is `180d` or `90d`

4. The previous combo-promotion docs are now known to be stale because the ATR alignment bug is fixed.
   - Earlier promotion headlines that cited `2980.07 / 3.040 / -24.16` should not be treated as canonical anymore.
   - After fixing ATR alignment, the current repaired official replay is:
     - `2956.62% / 2.601 / -28.15%`
   - Promotion to `H90` should therefore be treated as:
     - a repair and replacement of the previous ATRVT wording
     - not a minor additive tweak

## Implementation Scope Required Before Promotion

1. Parameterize shared ATR background.
   - Add canonical ATRVT config fields:
     - `atr_ref_days`
     - `atr_ref_stat`
     - `atr_scale_min`
     - `atr_scale_max`
   - Keep default explicit in code, not hidden in module constants.

2. Thread ATRVT config through the formal mainline stack.
   - `v123_formal_launch_and_layer2_weight_audit.py`
   - live package build
   - atlas generation
   - reproduction scripts

3. Expose ATRVT spec identity in live/dashboard payloads.
   - Example fields:
     - `atrvt_label`
     - `atr_ref_days`
     - `atr_ref_stat`
     - `atr_scale_band`

4. Repair official documents and reproduction anchors together with promotion.
   - `official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md`
   - `official_mainline/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md`
   - `official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md`
   - `ACTIVE_MAINLINE_STATUS.md`
   - `WORKING_BASELINE.md`
   - `memory.md`
   - `archive/...` snapshot

## Practical Conclusion

- `ATRVT H90` is strong enough to deserve promotion work.
- But the next step should not be "just update one number".
- The correct next step is:
  - repair the shared ATRVT implementation contract
  - rerun formal promotion audit under the repaired contract
  - then replace the official mainline package and its archive together
