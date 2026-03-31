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
  - re-entry `Weekly RSI(14) <= 30 hold`
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
- `launch_optimal` remains `LAUNCH_NO_GO`.
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
  - canonical adopted version: `Formal + WRSI14_30_EMA250`
  - weekly branch winner: `EMA250` over `EMA220`
  - 4h branch winner: `EMA200` over `EMA220`
  - non-primary 4h reference: `H4RSI14_10_EMA200`
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
  - re-entry `Weekly RSI(14) <= 30 hold`
- Current eligible forward directions:
  - new orthogonal `Sleeve #3`
  - higher-layer multi-sleeve portfolio architecture
  - governance / deployment implementation work

## Research Boundaries

- Continue only on `squeeze_release_20 / lb20_stop3.2_trail5.0_beoff` unless the user explicitly changes the baseline.
- Do not return to old `v85` long+short as the main line.
- Do not reopen the old core-only Risk-Off promotion line or same-line re-entry repair unless a genuinely new hypothesis is explicitly authorized.
- Do not reopen rejected full-stack cash-like Risk-Off as if it were still live.
- Do not cite the optimistic `v115` full-stack gate simulation as final evidence.
- Use the adopted core-only `EMA250 + Weekly RSI30 hold` line as the canonical Risk-Off reference.
- Do not reopen `compression_breakout` repair as if it were still an active line.
- Do not reopen single-sleeve dynamic timing research on top of `ConstAddOn[1.00x]`.
- Do not reopen breakout grading / cap / downgrade micro-repair.
- Do not keep iterating on rejected second-sleeve families unless a genuinely new family definition is explicitly authorized.
- Do not repackage breakout near-cousins as new sleeves.
- Do not reopen broad brute-force parameter search.
- Do not add many new filters just to improve backtest optics.
- Do not switch the default execution tuple back to a harsher stress tuple or to a more idealized tuple without explicitly documenting the change.

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
  - re-entry `Weekly RSI(14) <= 30 hold`
  - approved hard cap `3.0x`
- Treat `Core BTC holding + Binary AddOn overlay` as legacy reference, not as the active default.
- Preserve archived directions as archive material rather than active workstreams.
- Treat old second-sleeve discovery as completed, not as the active stage.
- Current forward priority should shift to:
  1. new orthogonal `Sleeve #3`
  2. higher-layer multi-sleeve portfolio architecture
  3. governance / deployment implementation work
