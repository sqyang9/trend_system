# Pre-Mainline Balanced ATRVT Landing Audit

## Scope

- Candidate under audit: `S1 90d / S2 60d`.
- Core side stays fixed:
  - stable `close3`
  - high-churn `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces high-churn earlier
- This audit checks whether the candidate is blocked by signal quality or only by implementation contract gaps.

## Promotion Snapshot

- Candidate: `S1 90d / S2 60d`
- Default: `Return 3196.79% / Calmar 2.873 / MaxDD -26.23%`
- Stress: `Calmar 2.932 / MaxDD -26.04%`
- Harsh: `Calmar 2.680 / MaxDD -27.42%`
- `W06 DD/Exp`: `-42.7%`
- `W11 AvgExp`: `0.978`
- Annual starts vs corrected `180d`:
  - Return better `5/7`
  - Calmar better `6/7`
  - MaxDD better `7/7`
- Freeze-date validation:
  - `W01-W06 -> W07-W13`: `174.12% / 1.661 / -22.11%`
  - `W01-W09 -> W10-W13`: `44.70% / 1.159 / -20.62%`

## Landing Readiness

- Signal layer: `GO`
- Landing readiness: `NO_GO without implementation`
- Promotion recommendation: `GO_AFTER_IMPLEMENTATION`

## Blockers

1. Shared ATRVT contract still assumes one symmetric spec.
   - Current shared path only carries one `atrvt_spec`, one `atr_scale`, and one `atrvt_label`.
   - The candidate needs `atrvt_s1_spec` and `atrvt_s2_spec` to be first-class fields.

2. Formal portfolio path cannot yet replay asymmetric ATRVT from adopted posture.
   - `v123_formal_launch_and_layer2_weight_audit.py` can switch symmetric ATRVT on/off, but it cannot express:
     - `S1 90d med / 0.35-1.50`
     - `S2 60d med / 0.35-1.50`

3. Live/dashboard/atlas currently expose only one ATRVT label.
   - Promotion would otherwise create a reporting mismatch:
     - engine runs asymmetric sleeve scaling
     - UI still reports one symmetric ATRVT contract

## Required Implementation Surface

- Add explicit sleeve-level ATRVT spec fields:
  - `atrvt_s1_ref_days`
  - `atrvt_s1_ref_stat`
  - `atrvt_s1_scale_min`
  - `atrvt_s1_scale_max`
  - `atrvt_s2_ref_days`
  - `atrvt_s2_ref_stat`
  - `atrvt_s2_scale_min`
  - `atrvt_s2_scale_max`
- Add sleeve-level labels:
  - `atrvt_s1_label`
  - `atrvt_s2_label`
- Add sleeve-level live values:
  - `atr_scale_s1`
  - `atr_scale_s2`

## Verdict

- This candidate is blocked by implementation contract shape, not by missing research support.
- If asymmetric ATRVT is wired through shared/mainline/live surfaces cleanly, it is eligible for formal promotion rerun.
