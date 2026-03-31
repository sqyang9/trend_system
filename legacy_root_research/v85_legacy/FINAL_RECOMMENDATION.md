# Final Recommendation

- Recommended: LAUNCH_NO_GO
- Primary research line: BTC long-only trend mother on `squeeze_release_20`
- Current research_optimal: `lb20_stop3.2_trail5.0_beoff`
- Suitable for first live launch: NO
- Main risk: the line is credible and healthy, but still cannot be described as an independent BTC buy-and-hold winner

## Locked Working Baseline

- Old `v85` long+short is no longer the main research object.
- Default research tuple is `next_bar_open + legacy_bar_extrema + midpoint + full_model`.
- `live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model` is retained only for stress and Gatekeeper V2.
- Launch remains `LAUNCH_NO_GO`.

## Research Optimal

- Variant: `lb20_stop3.2_trail5.0_beoff`
- Stats: Return 470.51%, CAGR 32.28%, Sharpe 0.933, MaxDD -34.49%, PF 1.947, Trades 56
- Interpretation: this is the strongest current local variant on the long-only mother, with improved return and risk-adjusted metrics versus the prior base.

## Launch Status

- 35% sizing gate summary: baseline_gate false, yearly true, rolling_oos true, regime true, cost_stress true, slippage_stress true, execution_mode_stress true, intrabar_path_stress true, live_safety_check true
- Main blocker at 35% sizing: the legacy `baseline_gate` trade-count threshold is mismatched for a low-frequency trend mother.
- This is not a system safety failure and not a non-baseline stress failure.

## Guardrail

- At full-size research sizing, `baseline_gate` failure is not only a trade-count problem because max drawdown still misses the `-30%` cap.
- Do not describe the system as "only missing trade count" in full-size research mode.

## Direct Answers

1. Current main research line: BTC long-only `squeeze_release_20 / lb20_stop3.2_trail5.0_beoff`
2. Current launch conclusion: `LAUNCH_NO_GO`
3. Current default research tuple: `next_bar_open + legacy_bar_extrema + midpoint + full_model`
4. Current stress/gate tuple: `live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model`
5. Next research boundary: continue only with local optimization on this line; do not return to old v85 long+short and do not resume broad brute-force search
