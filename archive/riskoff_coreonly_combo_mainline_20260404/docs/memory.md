# Project Memory

## Purpose

This file is the anti-drift memory for the repository.
It records the locked baseline, archived directions, active extension lines, and reproducibility rules.
If future work conflicts with this file, the conflict must be stated explicitly instead of being silently ignored.

## Locked Baseline

- Old `v85` long+short is retired as the primary research line.
- Current primary line is BTC long-only `squeeze_release_20`.
- Current `research_optimal` is `lb20_stop3.2_trail5.0_beoff`.
- Current official structure is `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`.
- Adopted Risk-Off overlay:
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the high-churn gate earlier
  - override `Weekly RSI(14) <= 30 hold`
- Adopted sleeve scaling:
  - `S1 + S2 ATR vol-targeting`
- Approved hard total exposure cap is `3.0x`.
- `2.5x` is fallback only if governance later tightens, not a superior frontier.
- Binary AddOn is legacy reference only.
- Default research tuple is:
  - `next_bar_open`
  - `legacy_bar_extrema`
  - `midpoint`
  - `full_model`
- Stress/gate tuple is:
  - `live_runner_next_5m_close`
  - `segment_path_same_bar`
  - `pessimistic`
  - `full_model`
- `launch_optimal` is now `LAUNCH_GO` for the adopted formal mainline.
- The long-only line is a high-quality BTC trend overlay, not a confirmed standalone BTC buy-and-hold replacement.

## Archived Research

- old core-only Risk-Off:
  - directionally valid
  - execution-aligned
  - promotion frozen
  - core re-entry deep dive completed
  - staged restoration closed
  - full-restoration variants improved understanding but did not beat `RO_EMA220_REENTRY_CLOSE_HOLD_3`
  - line re-frozen
  - archived and not part of the baseline
- new full-stack Risk-Off / re-entry adoption branch:
  - explicitly distinct from the archived core-only line
  - architecture: normal `Core + Sleeve #1 + Sleeve #2`, Risk-Off state flattens all three to cash-like
  - screened against core-only structure and rejected
  - closed
- adopted core-only Risk-Off overlay:
  - structure winner over full-stack
  - default / stress / harsher-friction adoption audit completed
  - prior overlay-level adoption milestone:
    - `Formal + EMA250_CLOSE3_HC23_STRICT_BREAKOUT4`
  - overlay-level adopted readout:
    - `Return 2459.02%`
    - `Calmar 2.352`
    - `MaxDD -29.06%`
  - later full-portfolio promoted package:
    - `Formal + ATRVT_S1S2 + EMA250_CLOSE3_HC23_STRICT_BREAKOUT4_HV85FORCE`
    - `Return 2980.07%`
    - `Calmar 3.040`
    - `MaxDD -24.16%`
- layer-2 portfolio weight audit:
  - adopted default posture is `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
  - prior `Core 0.75 / Sleeve1 1.25 / Sleeve2 1.00` posture is superseded
- current-time entry audit:
  - latest live state is `core_full_s1_0_s2_0`
  - preferred onboarding method is `immediate_full`
  - staged or wait-for-switch entry is not preferred in the current state analog
- startup warmup audit:
  - `12m` warmup is preferred
  - `6m` warmup is acceptable
  - `3m` warmup is not production-ready
- ETH transfer / switch audit:
  - ETH standalone transfer is only directionally valid
  - BTC-flat to ETH switch fails to improve the BTC adopted mainline
  - ETH is not an active extension of the baseline
- isolated regime detector research:
  - separate folder: `regime_detector_research`
  - useful layers found:
    - `vol_soft_off`
    - `vol_soft_off + S1 distribution lock`
  - both can beat the adopted baseline on headline metrics in isolated audit
  - but both also worsen medium-path burden (`Worst3m`, `Worst6m`, `RecoveryDays`)
  - `S2 tightened stop` was tested and gives back most of the regime advantage
  - current status:
    - keep as lightweight reserve research
    - not part of the locked baseline
- isolated gravity penalty research:
  - separate folder: `gravity_penalty_research`
  - idea: penalize new `S1` / `S2` entry size when `(close - EMA250) / ATR` is extremely stretched
  - current best probe: `GP12_R5_X0.5`
  - result:
    - higher return
    - but no meaningful improvement in `Calmar`
    - slightly worse `MaxDD`, `Worst3m`, `Worst6m`
  - current status:
    - reserve only
    - not part of the locked baseline
- isolated `S2` time/progress stop research:
  - separate folder: `s2_time_stop_research`
  - original `range_mid` timeout idea was invalid under native adopted `S2`, because `S2B` already requires `close >= range_mid_20`
  - corrected replay was rebuilt using a meaningful post-entry progress test:
    - if `S2` fails to reach `entry + 1.4 ATR` within `N` 4h bars, force exit at the deadline close
  - corrected replay aligns closely with native adopted `S2`
  - result:
    - `TS8 / TS12 / TS16` all fail to beat the adopted baseline
    - best candidate `ProgressTS16` still loses on `Return`, `Calmar`, and `MaxDD`
  - current status:
    - rejected
    - not part of the locked baseline
- isolated volatility proxy system-defect research:
  - separate folder: `system_defect_research`
  - objective:
    - treat `W06` and `W11` as system defect revealers, not as optimization windows
    - test whether background volatility proxies can improve the current official mainline without editing the mainline itself
  - current background proxies:
    - `ATR14`-based sleeve vol-targeting on `4h`
    - `HV percentile` on `4h` as realized-volatility proxy for missing `DVOL / IV` style context
  - current readout:
    - best `P0` result:
      - `S1 + S2 ATR vol-targeting`
      - `Return 3072.90%`
      - `Calmar 3.073`
      - `MaxDD -24.17%`
    - best `P1` result:
      - `HV percentile >= 90 -> force high-churn core qualification`
      - improves `W11` re-entry churn
      - but does not beat the current official mainline by itself on full-sample headline metrics
    - best combined independent probe:
      - `S1 + S2 ATR vol-targeting + HV percentile >= 85 -> force high-churn core qualification`
      - `Return 2995.89%`
      - `Calmar 3.044`
      - `MaxDD -24.17%`
  - current status:
    - promotion audit completed
    - combined package promoted into the official mainline
    - `ATR` and `HV percentile` remain reusable background indicators, but they are no longer reserve-only
- isolated module refinement research:
  - separate folder: `module_refinement_research`
  - objective:
    - test whether small per-module refinements can clearly beat the current adopted mainline before any deeper audit
  - screened and first-pass rejected:
    - `core_slope_significance_filter`
    - `s1_momentum_gate_tightening`
    - `s2_divergence_confirmation`
  - interpretation:
    - current adopted mainline is not easily improved by small local module refinements
    - do not keep iterating on these branches unless a genuinely different formulation is proposed
- live operating layer:
  - state panel exists
  - live decision memo exists
  - startup / onboarding playbook exists
  - fixed-frequency status runner exists: `live_operating_layer/mainline_live_status.py`
  - recommended cadence: every `4h` bar close
  - takes `account_equity` and `current_notional`
  - returns:
    - current state
    - target exposure
    - target notional
    - rebalance instruction
  - use these before inventing new discretionary operating rules
- `compression_breakout -> exhaustion / compound repair`:
  - directionally valid
  - archived as promising-but-not-promotable
  - not an active repair line anymore
- old `v85` long+short:
  - retired as primary research
- Bear short sleeve:
  - inactive

Archived means the line is preserved for reference and audit, but should not be resumed as if it were still an active baseline candidate.

## Closed Single-Sleeve Lines

- AddOn grading repair line is closed and archived.
- Exposure Engine `E2 / E3` dynamic timing line is closed.
- Do not resume threshold tweaking on the current AddOn sleeve.

## Current Discovery Stage

- `SECOND_SLEEVE_DISCOVERY` is completed for this round.
- Completed rejected families:
  - `washout_reversal_reclaim`: rejected
    - orthogonal in timing
    - not usefully complementary
  - `pullback_reclaim_continuation`: rejected
    - too much overlap with the current sleeve
    - no portfolio improvement vs `Const1x`
    - harmful in early recovery window
- Promoted official `Sleeve #2`:
  - `range_rotation_mean_reversion`
  - role: drawdown / sideways-volatility / chop diversification
  - not a recovery helper
  - not a breakout clone
- Current official portfolio is:
  - Core BTC holding
  - `Sleeve #1 = ConstAddOn[1.00x]`
  - `Sleeve #2 = RangeRotation`
- Current official overlay:
  - `core-only Risk-Off`
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the high-churn gate earlier
  - override `Weekly RSI(14) <= 30 hold`
- Current adopted sleeve scaling:
  - `S1 + S2 ATR vol-targeting`
- Current eligible forward directions:
  - live monitoring / reporting / dashboard extension
  - deployment / implementation automation packaging
  - higher-layer multi-sleeve portfolio architecture
- `SLEEVE3_DISCOVERY_RESET` is now closed / rejected for the current baseline:
  - `post_dislocation_repricing_climb`: rejected
  - `failed_breakdown_reversal_acceptance`: rejected
  - `reset_base_reacceptance_v2`: rejected
  - `slow_drift_trend_persistence`: not advanced; line closed

## Research Boundaries

- Continue only on `squeeze_release_20 / lb20_stop3.2_trail5.0_beoff` unless the user explicitly changes the baseline.
- Do not return to old `v85` long+short as the main line.
- Do not reopen the old core-only Risk-Off promotion line or same-line re-entry repair unless a genuinely new hypothesis is explicitly authorized.
- Do not reopen rejected full-stack cash-like Risk-Off as if it were still live.
- Do not cite the optimistic `v115` full-stack gate simulation as final evidence.
- Use the adopted core-only `EMA250 + stable close3 + HC23 strict breakout_4 + HV85 force + Weekly RSI30 override` line as the canonical Risk-Off reference.
- Do not reopen `compression_breakout` repair as if it were still an active line.
- Do not reopen single-sleeve dynamic timing research on top of `ConstAddOn[1.00x]`.
- Do not reopen breakout grading / cap / downgrade micro-repair.
- Do not keep iterating on rejected second-sleeve families unless a genuinely new family definition is explicitly authorized.
- Do not repackage breakout near-cousins as new sleeves.
- Do not reopen broad brute-force parameter search.
- Do not add many new filters just to improve backtest optics.
- Do not switch the default execution tuple back to a harsher stress tuple or to a more idealized tuple without explicitly documenting the change.
- Do not treat ETH transfer or BTC-flat-to-ETH switch as part of the active baseline.
- Do not treat `ATR` sleeve scaling or `HV percentile` forcing as optional reserve-only ideas; they are now part of the active baseline contract.
- Do not silently merge `regime_detector_research` into the active baseline; it remains isolated until a future explicit promotion decision.
- Do not reopen first-pass rejected `module_refinement_research` branches as if they were still active candidates.
- Do not reopen corrected-but-rejected `S2` time/progress stop as if it were still undecided.

## Reproducibility Rules

1. Final claims must be reproducible from committed code and committed result files.
2. Bar-level logic must be causal.
   - Signals may use information available at bar `t` close.
   - Position changes and PnL realization must start from bar `t+1` or from the explicitly modeled execution event.
3. If a study does not use the default execution-aligned framework, it must be labeled `exploratory` and must not be presented as equal in status to engine-backed strategy results.
4. Full-sample winner selection is allowed only for exploration.
   - It is not enough for formal promotion of a new module, system structure, or default parameter.
5. Default-tuple strategy studies and stress/gate studies must remain clearly separated.
6. If a new module is introduced at the portfolio layer, its implementation path must be stated explicitly:
   - execution-aligned engine-backed
   - or simplified allocation simulation
7. If the simplified path is used, assumptions and limitations must be written into the report, not hidden.

## Development Principles

- First verify structure, then tune parameters.
- Prefer low-frequency, explainable, auditable logic.
- Keep modules simple enough that each one has a clear job.
- Add parameter analysis only when it is needed to test robustness, not as the main research method.
- Do not let one attractive backtest overturn a locked baseline without an explicit revalidation step.

## Future Research Directions

- Keep the adopted baseline locked at:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - override `Weekly RSI(14) <= 30 hold`
  - approved hard cap `3.0x`
- Treat `Core BTC holding + Binary AddOn overlay` as legacy reference, not as the active default.
- Preserve archived directions as archive material rather than active workstreams.
- Treat old second-sleeve discovery as completed, not as the active stage.
- Current forward priority should shift to:
  1. higher-layer multi-sleeve portfolio architecture
  2. governance / deployment implementation work
