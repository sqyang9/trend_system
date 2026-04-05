# Working Baseline

## Official Baseline

- Primary strategy: BTC long-only trend system
- Mainline: `squeeze_release_20`
- Current `research_optimal`: `lb20_stop3.2_trail5.0_beoff`
- Official structure: `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- Adopted Risk-Off overlay:
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the high-churn gate earlier
  - override `Weekly RSI(14) <= 30 hold`
- Adopted sleeve scaling:
  - `S1 + S2 ATR vol-targeting`
- Approved hard total exposure cap: `3.0x`
- Legacy reference: `Core BTC holding + Binary AddOn overlay`

This is the working baseline because:

- `ConstAddOn[1.00x]` cleared the deployment-grade robustness audit and became the new default baseline
- `RangeRotation` cleared second-sleeve discovery and promotion audit as official `Sleeve #2`
- the hard total exposure cap audit confirmed `3.0x` as the approved governance cap
- the reopened Risk-Off successor study and later volatility-proxy defect branch jointly cleared structure screening, adoption audit, final qualification promotion, and the later `ATRVT + HV85 force` promotion into the full official mainline

## Default Research Tuple

- `next_bar_open`
- `legacy_bar_extrema`
- `midpoint`
- `full_model`

## Stress And Gate Tuple

- `live_runner_next_5m_close`
- `segment_path_same_bar`
- `pessimistic`
- `full_model`

This tuple is used for stress and gate checks only. It is not the default research tuple.

## Launch Status

- `launch_optimal = LAUNCH_GO`
- Old `LAUNCH_NO_GO` was inherited from the single-mother Gatekeeper V2 process and is superseded for the current adopted formal mainline.
- Current `LAUNCH_GO` is based on the adopted portfolio-level mainline:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - `S1 + S2 ATR vol-targeting`
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the high-churn gate earlier
  - override `Weekly RSI(14) <= 30 hold`
  - validated under `default`, `stress`, and `harsher friction`

## Adoption Closure

- Full-stack cash-like Risk-Off was screened and rejected.
- Core-only Risk-Off completed:
  - `default`
  - `stress`
  - `harsher friction`
  adoption-style audit.
- Final adopted version:
  - `Formal + ATRVT_S1S2 + EMA250_CLOSE3_HC23_STRICT_BREAKOUT4_HV85FORCE`
  - default result:
    - `Return 2980.07%`
    - `Calmar 3.040`
    - `MaxDD -24.16%`
  - stress result:
    - `Return 3098.95%`
    - `Calmar 3.118`
    - `MaxDD -23.89%`
  - harsher friction result:
    - `Return 2804.78%`
    - `Calmar 2.911`
    - `MaxDD -24.67%`
- Prior overlay-level promotion milestone retained:
  - `Formal + EMA250_CLOSE3_HC23_STRICT_BREAKOUT4`
  - `Return 2459.02% / Calmar 2.352 / MaxDD -29.06%`

## Archived Directions

- old core-only Risk-Off line: directionally valid, execution-aligned, promotion frozen, re-entry deep dive completed and re-frozen, archived
- full-stack cash-like Risk-Off overlay: tested, rejected, closed
- `compression_breakout -> exhaustion / compound repair`: promising-but-not-promotable archive
- old `v85` long+short: retired
- Bear short sleeve: inactive

Archived directions are part of repository history, not part of the working baseline.

## Closed Single-Sleeve Lines

- AddOn grading repair line is archived and closed
- Exposure Engine `E2 / E3` single-sleeve dynamic timing line is closed
- Do not resume threshold repair or single-sleeve timing on top of `ConstAddOn[1.00x]`

## Current Portfolio State

- `Sleeve #1`: `ConstAddOn[1.00x]`
- `Sleeve #2`: `RangeRotation`
- `Risk-Off overlay`: core-only
- adopted sell-side: `EMA250`
- adopted stable re-entry: `close3`
- adopted high-churn re-entry: `strict EMA50 + breakout_4`
- adopted high-churn forcing: `HV percentile >= 85`
- adopted override re-entry: `Weekly RSI(14) <= 30 hold`
- adopted default posture from layer-2 audit:
  - `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- adopted sleeve scaling:
  - `S1 + S2 ATR vol-targeting`
- superseded prior default posture:
  - `Core 0.75 / Sleeve1 1.25 / Sleeve2 1.00`
- `RangeRotation` role: drawdown / sideways-volatility / chop diversification
- `RangeRotation` is not a recovery helper
- approved governance cap: `3.0x`
- `2.5x` remains fallback only if governance later rejects `3.0x`

## Current-Time Entry Guidance

- Latest audited live state:
  - `core_full_s1_0_s2_0`
  - `Core 1.00 / Sleeve1 0.00 / Sleeve2 0.00 / Total 1.00`
- Current-time onboarding audit conclusion:
  - preferred method: `immediate_full`
  - not preferred:
    - `staged_30_60`
    - `wait_next_switch`
- Reason:
  - in historical analogs of the current state, immediate full deployment had the best average Calmar and the best near-term participation.

## Warmup Guidance

- Full-history prewarm is not required for practical startup.
- Recommended startup warmup:
  - `12m` preferred
  - `6m` acceptable
- Not recommended:
  - `3m` warmup only
- Interpretation:
  - shorter warmup windows can still work, but `3m` becomes unstable on hard starts and should not be treated as production-ready startup posture.

## ETH Transfer Readout

- ETH transfer of the adopted BTC mainline was tested as a separate `1h exec / 4h signal` audit.
- Result:
  - ETH standalone transfer is directionally valid versus ETH buy-and-hold
  - but quality is materially weaker than BTC
  - `BTC flat -> ETH switch` does not improve the BTC adopted mainline and is rejected
- Therefore ETH is not part of the current working baseline.

## Isolated Regime Detector Readout

- Independent `regime_detector_research` was tested as an isolated reserve line.
- Current readout:
  - `SoftOffOnly` beats the adopted baseline on:
    - `Return`
    - `Calmar`
    - `MaxDD`
  - `SoftOff + S1 lock` beats the adopted baseline more clearly on the same three headline metrics.
- But both also worsen:
  - `Worst3m`
  - `Worst6m`
  - `RecoveryDays`
- `S2 tightened stop` was tested and materially gave back most of the earlier advantage.
- Therefore the regime line is:
  - directionally valid
  - worth preserving as a lightweight reserve research branch
  - not promoted into the working baseline

## Isolated Gravity Penalty Readout

- Independent `gravity_penalty_research` tested dynamic sleeve downscaling when price is extremely stretched above `EMA250`.
- Current best probe:
  - `GP12_R5_X0.5`
- Readout:
  - return improves
  - but `Calmar` does not improve enough
  - `MaxDD`, `Worst3m`, and `Worst6m` are slightly worse
- Therefore gravity penalty remains:
  - directionally interesting
  - reserve only
  - not promoted into the working baseline

## Isolated S2 Time / Progress Stop Readout

- Independent `s2_time_stop_research` was reopened and corrected.
- Important correction:
  - the original `range_mid_20` timeout thesis was invalid under native adopted `S2`
  - corrected test instead used a post-entry progress milestone:
    - if `S2` fails to reach `entry + 1.4 ATR` within `N` 4h bars, force exit at deadline close
- Replay alignment outcome:
  - corrected `ReplayControlNative` is effectively identical to the adopted baseline
  - therefore the branch is now valid for judgment
- Result:
  - `TS8 / TS12 / TS16` all fail to beat the adopted baseline
  - best candidate `ProgressTS16` still loses on:
    - `Return`
    - `Calmar`
    - `MaxDD`
- Therefore this branch is:
  - tested
  - corrected
  - rejected
  - not part of the working baseline

## Module Refinement First-Pass Readout

- Independent `module_refinement_research` was opened to test small isolated module improvements before any deeper audit.
- First-pass screened:
  - `core_slope_significance_filter`
  - `s1_momentum_gate_tightening`
  - `s2_divergence_confirmation`
- Result:
  - none showed a clear edge over the adopted baseline
  - all three are first-pass rejected
- Interpretation:
  - the current adopted mainline does not appear to be missing an obvious local cleanup refinement

## Live Operating Layer

- Implemented outputs:
  - state panel
  - live decision memo
  - startup / onboarding playbook
  - fixed-frequency live status runner
- Current live readout at the latest audited bar:
  - `Portfolio state = Core-Only`
  - `core Risk-Off state = full`
  - `Total exposure = 1.00`
  - `Cap headroom = 2.00x`
  - `ATR scale = 1.00`
  - `HV percentile = 92.0`
  - `Instability source = hv_force`
  - `Governance alert = Observe`
- Fixed-frequency status runner:
  - `live_operating_layer/mainline_live_status.py`
  - cadence: every `4h` bar close
  - inputs:
    - `account_equity`
    - `current_notional`
  - outputs:
    - current state
    - target exposure
    - target notional
    - rebalance instruction
- These outputs translate research conclusions into daily operating language and should be used before inventing any new overlay heuristics.

## Current Eligible Forward Work

- live monitoring / reporting / dashboard extension
- deployment implementation and automation packaging
- higher-layer multi-sleeve portfolio architecture

## Volatility Proxy Promotion Readout

- `system_defect_research` opened from the two system defects revealed by `W06` and `W11`.
- That branch is no longer only reserve research: its combined winner is now promoted into the current official mainline.

Promoted additions:

- `S1 + S2 ATR vol-targeting`
- `HV percentile >= 85 -> force high-churn core qualification`

Current official mainline reference:

- `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- official launch-audit readout:
  - `Return 2980.07%`
  - `Calmar 3.040`
  - `MaxDD -24.16%`

System-defect interpretation:

- `ATR` sizing is the adopted system-level answer to the `W06` defect family
- `HV percentile` is the adopted background detector for the `W11` defect family
- `P1` still does not justify standalone promotion by itself, but it is now adopted as part of the combined package

## Closed Discovery Readout

- `SLEEVE3_DISCOVERY_RESET` is closed for now.
- No promotable `Sleeve #3` was found against the current adopted mainline.
- Screened and rejected:
  - `post_dislocation_repricing_climb`
  - `failed_breakdown_reversal_acceptance`
  - `reset_base_reacceptance_v2`
- `slow_drift_trend_persistence` was not promoted and the line was closed before further extension.

## Research Boundary

- Do not change the mother strategy without explicit revalidation.
- Do not reopen the old core-only Risk-Off promotion line or same-line re-entry repair without a genuinely new hypothesis.
- Do not reopen rejected full-stack cash-like Risk-Off as if it were still competitive.
- Do not cite optimistic gate-simulation results such as the superseded `v115` full-stack audit as final evidence.
- Use the adopted core-only `EMA250 + stable close3 + HC23 strict breakout_4 + HV85 force + Weekly RSI30 override` line as the canonical Risk-Off reference.
- Do not return to the old `v85` long+short main line.
- Do not reopen `compression_breakout` repair as an active line.
- Do not reopen single-sleeve Exposure Engine `E2 / E3` timing research.
- Do not reopen breakout grading / cap / downgrade micro-repair.
- Do not repackage breakout near-cousins as new sleeves.
- Do not resume broad brute-force search.
- Keep the locked execution tuples unchanged unless explicitly reapproved.
- Do not revive the rejected ETH switch line as if it were an active portfolio extension.
- Do not describe `ATR` sleeve scaling or `HV` forcing as reserve-only background indicators anymore; they are now part of the adopted mainline.
- Do not treat the isolated `regime_detector_research` reserve branch as an adopted module unless a new promotion audit is explicitly completed.
- Do not treat first-pass rejected `module_refinement_research` branches as open candidates.
- Do not treat corrected-but-rejected `S2` time/progress stop as an active refinement line.
