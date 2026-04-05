# Pre-Mainline ATRVT H60 Landing Audit

## Verdict

- Signal layer: `GO`
- Landing readiness: `NO_GO` without shared ATRVT parameterization, official document repair, and freeze-date clarification
- Promotion recommendation: `HOLD_AFTER_WALKFORWARD`

## What Changed

- This is not a new Core-gate study.
- Core side remains fixed at the corrected combo structure:
  - `EMA250` sell-side
  - stable `close3`
  - high-churn `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the stricter gate earlier
- The only promoted delta under review is the ATRVT reference horizon:
  - repaired current shared path: `180d median / 0.35-1.50`
  - first refinement winner: `90d median / 0.35-1.50`
  - current strongest challenger: `60d median / 0.35-1.50`

## Promotion Evidence

- Repaired current combo base replay:
  - `Return 2946.79% / Calmar 2.574 / MaxDD -28.41%`
- `ATRVT H90`:
  - `Return 3114.74% / Calmar 2.762 / MaxDD -27.02%`
- `ATRVT H60`:
  - `Return 3327.75% / Calmar 2.988 / MaxDD -25.59%`

### H60 vs repaired current combo base

- `dReturn +380.96pp`
- `dCalmar +0.414`
- `dMaxDD +2.83pp`

### H60 vs H90

- `dReturn +213.01pp`
- `dCalmar +0.226`
- `dMaxDD +1.44pp`
- stress `dCalmar +0.227`
- harsh `dCalmar +0.207`

### W06 / W11

- `W06 DD/Exp`
  - repaired base `-46.9%`
  - `H90 -44.0%`
  - `H60 -40.9%`
- `W11` average exposure
  - repaired base `1.016`
  - `H90 0.980`
  - `H60 0.976`

### Annual starts

- `H60` vs `H90`
  - Calmar better `5/7`
  - MaxDD better `7/7`
  - Return better `4/7`

### Walk-forward

- `fit_W01-W06 -> validate_W07-W13`
  - `180d`: `190.80% / 1.739 / -22.58%`
  - `H90`: `179.63% / 1.665 / -22.56%`
  - `H60`: `166.26% / 1.587 / -22.36%`
- `fit_W01-W09 -> validate_W10-W13`
  - `180d`: `43.98% / 1.062 / -22.19%`
  - `H90`: `44.23% / 1.125 / -21.05%`
  - `H60`: `43.51% / 1.159 / -20.12%`
- Expanding stitched OOS for the train-selected winner:
  - `163.62% / 1.569 / -22.36%`

Source:
- `system_defect_research/ATRVT_H60_WALKFORWARD_AUDIT.md`

Sources:
- `system_defect_research/ATRVT_H60_AUDITION.md`
- `system_defect_research/ATRVT_H90_AUDITION.md`

## Integrity Check Status

- No second fully-empty promoted layer has been found after the ATR fix.
- Current verified state:
  - `ATRVT` now truly changes sleeve scaling
  - `HV85` truly changes instability classification
  - high-churn qualification truly changes Core weights
- Therefore the next blocker is not signal validity.
- The blocker is implementation contract and canonical document repair.

Source:
- `system_defect_research/PROMOTION_INTEGRITY_RECHECK.md`

## Landing Blockers

1. Shared ATR background is still hard-coded to the old `180d median` contract.
   - `volatility_background.py` still exposes:
     - `PCTL_LOOKBACK_BARS = 180 * 6`
     - `ATR_SCALE_MIN = 0.35`
     - `ATR_SCALE_MAX = 1.50`
   - `build_volatility_background()` still cannot express canonical adopted ATRVT spec fields such as:
     - `atr_ref_days`
     - `atr_ref_stat`
     - `atr_scale_min`
     - `atr_scale_max`

2. Formal mainline path still treats ATRVT as an on/off flag, not an adopted spec.
   - `v123_formal_launch_and_layer2_weight_audit.py` currently supports:
     - `atr_vol_target_s1`
     - `atr_vol_target_s2`
   - It cannot currently encode:
     - `60d median`
     - future alternate clips
     - future asymmetric `S1 / S2` ATRVT

3. Live, dashboard, and atlas still cannot identify which ATRVT regime is adopted.
   - Current surfaces can report:
     - `atr_scale`
     - `hv_pct_180d`
   - They cannot yet report the adopted ATRVT contract itself, such as:
     - `atrvt_label`
     - `atr_ref_days`
     - `atr_ref_stat`
     - `atr_scale_band`

4. Official mainline docs are still stale after the ATR fix.
   - The old combo-promotion headlines that assumed the broken ATRVT path should not be treated as canonical.
   - The corrected repaired baseline is now:
     - `2956.62% / 2.601 / -28.15%`
   - Promotion to `H60` must therefore be treated as:
     - corrected baseline repair
     - plus new ATRVT upgrade

5. `H60` is not yet a clean freeze-date winner.
   - It is the strongest full-sample ATRVT candidate.
   - But in the earlier validation split `W07-W13`, both `180d` and `H90` validate better on return and Calmar.
   - Therefore `H60` is currently:
     - a strong full-sample and annual-start challenger
     - but not yet a clean walk-forward promotion winner

## Implementation Scope Required Before Promotion

1. Parameterize shared ATRVT in `volatility_background.py`.
   - Replace hidden module defaults with explicit config inputs.

2. Thread ATRVT config through the formal stack.
   - `v123_formal_launch_and_layer2_weight_audit.py`
   - live package
   - dashboard snapshot layer
   - historical atlas
   - reproduction scripts

3. Expose ATRVT spec identity in operator-facing payloads.
   - Suggested canonical fields:
     - `atrvt_label`
     - `atr_ref_days`
     - `atr_ref_stat`
     - `atr_scale_min`
     - `atr_scale_max`

4. Repair official documents and reproduction anchors together.
   - `official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md`
   - `official_mainline/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md`
   - `official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md`
   - `ACTIVE_MAINLINE_STATUS.md`
   - `WORKING_BASELINE.md`
   - `memory.md`
   - archive snapshot

## Practical Conclusion

- `ATRVT H60` is now the strongest full-sample ATRVT candidate in the corrected lineage.
- But it is not yet strong enough to skip the OOS caution layer.
- Current interpretation should therefore be:
  - `180d`: corrected current baseline
  - `H90`: cleaner promotion sibling
  - `H60`: higher-upside, lower-freeze-confidence challenger
- The correct next step is not immediate promotion.
- The correct next step is:
  - parameterize the shared ATRVT contract once
  - keep `180d / 90d / 60d` as explicit comparable modes
  - then run one final promotion decision audit that weighs:
    - full-sample economics
    - annual starts
    - walk-forward credibility
