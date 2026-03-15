# Working Baseline

## Official Baseline

- Primary strategy: BTC long-only trend system
- Mainline: `squeeze_release_20`
- Current `research_optimal`: `lb20_stop3.2_trail5.0_beoff`
- Official structure: `Core BTC holding + Binary AddOn overlay`

This remains the working baseline because it is the only structure that has already improved return, Sharpe, Calmar, and MaxDD versus BTC buy-and-hold in the committed overlay integration result without relying on archived portfolio modules.

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

## Archived Directions

- Risk-Off: directionally valid, execution-aligned, promotion frozen, archived
- old `v85` long+short: retired
- Bear short sleeve: inactive

Archived directions are part of repository history, not part of the working baseline.

## Active Extension Line

- AddOn grading
- lead candidate: `Core + GradedAddOn[compression_breakout]`
- status: promising but not promotable

## Research Boundary

- Do not change the mother strategy without explicit revalidation.
- Do not reopen Risk-Off promotion.
- Do not return to the old `v85` long+short main line.
- Do not resume broad brute-force search.
- Keep the locked execution tuples unchanged unless explicitly reapproved.
