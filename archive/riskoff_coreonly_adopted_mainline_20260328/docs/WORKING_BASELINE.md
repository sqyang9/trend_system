# Working Baseline

## Official Baseline

- Primary strategy: BTC long-only trend system
- Mainline: `squeeze_release_20`
- Current `research_optimal`: `lb20_stop3.2_trail5.0_beoff`
- Official structure: `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- Adopted Risk-Off overlay:
  - sell-side `EMA250`
  - re-entry `Weekly RSI(14) <= 30 hold`
- Approved hard total exposure cap: `3.0x`
- Legacy reference: `Core BTC holding + Binary AddOn overlay`

This is the working baseline because:

- `ConstAddOn[1.00x]` cleared the deployment-grade robustness audit and became the new default baseline
- `RangeRotation` cleared second-sleeve discovery and promotion audit as official `Sleeve #2`
- the hard total exposure cap audit confirmed `3.0x` as the approved governance cap
- the reopened Risk-Off successor study cleared structure screening, full adoption audit, and sell-side EMA replacement audit with the core-only `EMA250 + Weekly RSI30 hold` overlay

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

- `launch_optimal = LAUNCH_NO_GO`
- At `35%` sizing, non-baseline gates pass, but the legacy baseline gate remains mismatched with a low-frequency trend mother.
- At full-size research sizing, baseline failure is not only a trade-count issue because MaxDD still exceeds the strict cap.

## Adoption Closure

- Full-stack cash-like Risk-Off was screened and rejected.
- Core-only Risk-Off completed:
  - `default`
  - `stress`
  - `harsher friction`
  adoption-style audit.
- Final adopted version:
  - `Formal + WRSI14_30_EMA250`
  - default result:
    - `Return 2720.25%`
    - `Calmar 2.024`
    - `MaxDD -35.07%`
  - stress result:
    - `Return 2876.60%`
    - `Calmar 2.089`
    - `MaxDD -34.70%`
  - harsher friction result:
    - `Return 2454.40%`
    - `Calmar 1.860`
    - `MaxDD -36.73%`
- Weekly branch decision:
  - `EMA250` replaced `EMA220`
- 4h branch decision:
  - `EMA200` replaced `EMA220` inside that branch
- Secondary non-primary reference:
  - `Formal + H4RSI14_10_EMA200`

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
- adopted re-entry: `Weekly RSI(14) <= 30 hold`
- `RangeRotation` role: drawdown / sideways-volatility / chop diversification
- `RangeRotation` is not a recovery helper
- approved governance cap: `3.0x`
- `2.5x` remains fallback only if governance later rejects `3.0x`

## Current Eligible Forward Work

- new orthogonal `Sleeve #3` discovery
- higher-layer multi-sleeve portfolio architecture
- governance / deployment implementation work

## Research Boundary

- Do not change the mother strategy without explicit revalidation.
- Do not reopen the old core-only Risk-Off promotion line or same-line re-entry repair without a genuinely new hypothesis.
- Do not reopen rejected full-stack cash-like Risk-Off as if it were still competitive.
- Do not cite optimistic gate-simulation results such as the superseded `v115` full-stack audit as final evidence.
- Use the adopted core-only `EMA250 + Weekly RSI30 hold` line as the canonical Risk-Off reference.
- Do not return to the old `v85` long+short main line.
- Do not reopen `compression_breakout` repair as an active line.
- Do not reopen single-sleeve Exposure Engine `E2 / E3` timing research.
- Do not reopen breakout grading / cap / downgrade micro-repair.
- Do not repackage breakout near-cousins as new sleeves.
- Do not resume broad brute-force search.
- Keep the locked execution tuples unchanged unless explicitly reapproved.
