# Working Baseline

## Active Research Line

- Primary line: BTC long-only trend mother built on `squeeze_release_20`.
- Old `v85` long+short is retired as a non-primary reference line and is no longer the main research object.

## Current Research Optimal

- Current `research_optimal`: `lb20_stop3.2_trail5.0_beoff`
- Interpretation: this is the current best local variant on the new long-only mother, not a return-dominant replacement for BTC buy-and-hold.

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

This tuple is kept for stress and Gatekeeper V2 only. It is not the default research tuple.

## Launch Status

- Current `launch_optimal`: `LAUNCH_NO_GO`
- At `35%` sizing, all non-baseline Gatekeeper V2 checks pass.
- The main remaining blocker at `35%` sizing is the legacy `baseline_gate` trade-count threshold, which does not fit a low-frequency trend mother.

## Important Guardrail

- At full-size research sizing, `baseline_gate` failure is not only a trade-count issue because max drawdown still misses the `-30%` cap.
- Do not describe the system as "only missing trade count" in full-size research mode.

## Research Boundary

- Continue only on `squeeze_release_20 / lb20_stop3.2_trail5.0_beoff`.
- Only do local optimization around breakout lookback, initial stop, trail multiplier, and highly restrained break-even checks.
- Do not return to the old `v85` long+short main line.
- Do not resume broad brute-force search.
