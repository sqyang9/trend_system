# Pre-Mainline Landing Audit

## Scope

- Candidate under landing audit: `high churn -> strict AND breakout_4`
- Standing reference: `state-aware strict`
- Mainline reference: `baseline close3`
- This is a landing audit only. No mainline implementation changes are included here.

## Findings

### P0: Mainline governance docs still describe the wrong re-entry rule

- The official status docs still say the adopted Risk-Off re-entry is `Weekly RSI(14) <= 30 hold`, not the actual current `close3 + weekly override` state machine.
- Evidence:
  - [ACTIVE_MAINLINE_STATUS.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/ACTIVE_MAINLINE_STATUS.md#L6) states `re-entry Weekly RSI(14) <= 30 hold`.
  - [WORKING_BASELINE.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/WORKING_BASELINE.md#L9) and [WORKING_BASELINE.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/WORKING_BASELINE.md#L42) say the same.
  - But [v121_coreonly_riskoff_sellside_ema_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v121_coreonly_riskoff_sellside_ema_audit.py#L92) restores from `flat` on `close_count >= 3`, while weekly RSI is only an override branch at [v121_coreonly_riskoff_sellside_ema_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v121_coreonly_riskoff_sellside_ema_audit.py#L95).
- Why this matters:
  - If the challenger is promoted without first fixing the canonical wording, the repo will continue to have three incompatible “truths”: governance docs, runtime docs, and actual state logic.
  - That is a release-blocking audit/governance issue, not a cosmetic doc issue.

### P1: Dashboard and live status are coupled to the old naming contract and will misreport the promoted rule unless updated in the same change set

- The dashboard snapshot builds the live core target by importing `build_target()` from `v121` and passing the old weekly spec label.
- Evidence:
  - [dashboard/signal_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/dashboard/signal_layer.py#L38) imports `build_indicators, build_target`.
  - [dashboard/signal_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/dashboard/signal_layer.py#L85) calls `build_target(...)` with `reentry_family = "weekly_rsi_hold"`.
  - [v123_formal_launch_and_layer2_weight_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v123_formal_launch_and_layer2_weight_audit.py#L34) still defines `ADOPTED_SPEC` as `WRSI14_30_EMA250`, and [v123_formal_launch_and_layer2_weight_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v123_formal_launch_and_layer2_weight_audit.py#L78) uses it to build the core target for the whole formal portfolio stack.
  - Live playbook text still says weekly-RSI re-entry at [v132_live_operating_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/v132_live_operating_layer.py#L387).
- Why this matters:
  - If only `v121` is changed, the runtime semantics may update, but the surrounding modules will still describe the wrong rule family.
  - Promotion therefore needs one coordinated package, not a one-file patch.

### P1: The promoted challenger introduces a new transient `armed` state in high-churn environments, but current live/dashboard presentation has no concept for it

- The landing candidate is not just “stricter close3”; it adds a qualification phase in high-churn sub-environments.
- Evidence:
  - [v166_state_aware_hybrid_final_audition.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/v166_state_aware_hybrid_final_audition.py#L239) defines `highly_unstable` as `flips30 >= 2 and flips60 >= 3`.
  - In [v166_state_aware_hybrid_final_audition.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/v166_state_aware_hybrid_final_audition.py#L318), high-churn `close3 + strict` moves to `armed`, not `normal`.
  - In [v166_state_aware_hybrid_final_audition.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/v166_state_aware_hybrid_final_audition.py#L341), `armed` can fail back to `flat` after `candidate.window_bars`.
  - In [v166_state_aware_hybrid_final_audition.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/v166_state_aware_hybrid_final_audition.py#L349), re-entry only completes if price closes above the armed trigger high.
- Why this matters:
  - Current live outputs only expose `core_riskoff_state` and `riskoff_active`, which are exposure-level summaries. They do not expose “qualified but not yet full” semantics.
  - Without a display contract for `armed`, operators will see a flat core but have no explanation for why `close3` did not re-enter.

### P2: The adopted-spec identifiers are now historically misleading and should not be reused unchanged for the promoted rule

- The repository still uses `WRSI14_30_EMA250` as the adopted-spec identity in several mainline-facing places, even though the actual normal re-entry logic is already `close3`.
- Evidence:
  - [v123_formal_launch_and_layer2_weight_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v123_formal_launch_and_layer2_weight_audit.py#L34)
  - [ACTIVE_MAINLINE_STATUS.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/ACTIVE_MAINLINE_STATUS.md#L13)
- Why this matters:
  - Reusing the same adopted identifier for a materially different rule will destroy audit traceability.
  - Promotion needs a new canonical name and a one-paragraph semantic definition.

## Promotion Candidate

- Candidate rule: `high churn -> strict AND breakout_4`
- Stable environment:
  - `3 consecutive 4h closes > EMA250` -> full re-entry
- High-churn environment:
  - `3 consecutive 4h closes > EMA250`
  - `EMA50 > EMA250`
  - `EMA50 slope > 0`
  - then enter a 4-bar qualification window
  - full re-entry only if a later close breaks above the `close3` trigger bar high
- Weekly override:
  - `weekly_rsi30_hold` remains an override path and is unchanged
- High-churn definition:
  - trailing `30d` core flips `>= 2`
  - trailing `60d` core flips `>= 3`

## Why It Is Eligible For Mainline Promotion

- The final audition passed against both mainline and the standing strict reference.
- Evidence:
  - [STATE_AWARE_HYBRID_FINAL_AUDITION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/STATE_AWARE_HYBRID_FINAL_AUDITION.md#L15): default `Return 2459.02%`, `Calmar 2.352`, `MaxDD -29.06%`
  - [STATE_AWARE_HYBRID_FINAL_AUDITION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/STATE_AWARE_HYBRID_FINAL_AUDITION.md#L23): challenger beats mainline in `default / stress / harsh`
  - [STATE_AWARE_HYBRID_FINAL_AUDITION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/STATE_AWARE_HYBRID_FINAL_AUDITION.md#L33): high-churn quick re-FLAT `14d / 30d` improves to `31.8% / 54.5%`
  - [STATE_AWARE_HYBRID_FINAL_AUDITION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/STATE_AWARE_HYBRID_FINAL_AUDITION.md#L49): recent two windows short-cycle counts do not regress vs strict
  - [STATE_AWARE_HYBRID_FINAL_AUDITION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/STATE_AWARE_HYBRID_FINAL_AUDITION.md#L56): annual-start robustness remains credible despite weaker `2025-01-01` and `2026-01-01` offsets

## Minimal Implementation Touch List

- State machine source:
  - [v121_coreonly_riskoff_sellside_ema_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v121_coreonly_riskoff_sellside_ema_audit.py)
- Formal portfolio bundle that consumes the adopted core target:
  - [v123_formal_launch_and_layer2_weight_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v123_formal_launch_and_layer2_weight_audit.py)
- Dashboard signal snapshot:
  - [dashboard/signal_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/dashboard/signal_layer.py)
- Live operating docs/text:
  - [live_operating_layer/v132_live_operating_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/v132_live_operating_layer.py)
  - [ACTIVE_MAINLINE_STATUS.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/ACTIVE_MAINLINE_STATUS.md)
  - [WORKING_BASELINE.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/WORKING_BASELINE.md)

## Required Landing Decisions Before Merge

- Canonical naming:
  - choose a new adopted-spec name; do not keep `WRSI14_30_EMA250`
- Runtime semantics:
  - decide whether `armed` is only an internal transient or a first-class live status
- Live/UI wording:
  - decide how to explain “high churn qualification pending” in dashboard and live memo
- Audit contract:
  - decide which report becomes the new canonical adoption reference after promotion

## Recommended Merge Order

1. Update canonical docs and adopted naming first.
2. Update the core state machine and the formal bundle together.
3. Update dashboard/live text in the same change set.
4. Re-run one parity audit that reproduces the promoted candidate numbers from the final audition.

## Pre-Merge Verification Checklist

- Reproduce the promoted candidate metrics under `default`, `stress`, and `harsh`.
- Confirm sell-side logic is unchanged.
- Confirm `weekly_rsi30_hold` still functions as override, not normal recovery.
- Confirm high-churn detection uses the same trailing flip definition as the audit.
- Confirm `armed -> RE` and `armed -> QUALIFY_FAIL` counts match research expectations on the default sample.
- Confirm dashboard event readout does not silently relabel `armed` as ordinary flat.
- Confirm live playbook and active status docs no longer mention weekly-RSI-only re-entry.

## Landing Verdict

- Signal verdict: `GO`
- Landing-governance verdict: `CONDITIONAL_GO`

Reason:

- The challenger has already cleared the economic and robustness bar.
- The remaining blockers are implementation-contract blockers: naming, documentation truth, and live/dashboard semantics.
- Those blockers are straightforward, but they should be fixed in the same promotion package rather than after the merge.
