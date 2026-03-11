# BTC Long-Only Trend Mother Report

- Recommended: LAUNCH_NO_GO under current Gatekeeper V2
- Compared with old v85: structurally better as a clean BTC trend mother, and now the only active primary research line
- Suitable for first live launch: not under current official gate profile
- Main risk: this line is credible and healthy, but still cannot be claimed to independently beat BTC buy-and-hold
- New daily default research tuple: next_bar_open + legacy_bar_extrema + midpoint + full_model

## Design

- New mother is long-only, 4H breakout-follow trend, no short symmetry, no partial TP.
- Entry is causal at next_bar_open under the calibrated intrabar model.
- Exit is slow trailing with structure-plus-volatility stop, deliberately biased toward holding large BTC trend legs.
- Relative to old v85, this line removes score-stacking and shifts toward low-frequency, high payoff-ratio trend capture.

## Baseline Candidates

### donchian_55_chandelier
- rules: 55-bar breakout, EMA200 regime, positive EMA slope, mild ADX filter, slow chandelier trail.
- stats: Return 263.69%, CAGR 23.05%, Sharpe 0.691, MaxDD -41.72%, PF 1.664, Trades 64
- vs B&H: return delta -592.47pp, Sharpe delta -0.059, Calmar delta -0.015
- holding continuity: avg hold 58.5 bars, median 47.1, top10 winner contribution 75.8%
- gate summary: {"baseline_gate": false, "yearly": false, "rolling_oos": false, "regime": true, "cost_stress": false, "slippage_stress": true, "execution_mode_stress": true, "intrabar_path_stress": true, "live_safety_check": true}

### quality_breakout_40
- rules: 40-bar breakout plus bar quality confirmation, EMA200 trend filter, no partial profit taking, slower hybrid trail.
- stats: Return 94.83%, CAGR 11.31%, Sharpe 0.451, MaxDD -46.09%, PF 1.370, Trades 86
- vs B&H: return delta -761.33pp, Sharpe delta -0.299, Calmar delta -0.322
- holding continuity: avg hold 30.0 bars, median 27.4, top10 winner contribution 63.9%
- gate summary: {"baseline_gate": false, "yearly": true, "rolling_oos": true, "regime": true, "cost_stress": false, "slippage_stress": false, "execution_mode_stress": true, "intrabar_path_stress": true, "live_safety_check": true}

### squeeze_release_20
- rules: Squeeze release plus 20-bar breakout inside a bullish EMA200 regime, designed to enter expansion after compression.
- stats: Return 303.39%, CAGR 25.12%, Sharpe 0.777, MaxDD -34.49%, PF 1.677, Trades 56
- vs B&H: return delta -552.77pp, Sharpe delta 0.027, Calmar delta 0.161
- holding continuity: avg hold 59.3 bars, median 40.4, top10 winner contribution 79.4%
- gate summary: {"baseline_gate": false, "yearly": true, "rolling_oos": true, "regime": true, "cost_stress": true, "slippage_stress": true, "execution_mode_stress": true, "intrabar_path_stress": true, "live_safety_check": true}

## Local Plateau

- Local neighborhood was centered on `squeeze_release_20`, because it dominated the baseline set on Sharpe, Calmar and gate stability.
- Prior plateau leader: lookback 20, adx_min 10.0, init_stop_atr 3.4, trail_atr_mult 5.0: Return 461.92%, Sharpe 0.926, MaxDD -34.49%
- Upgraded local variant: `lb20_stop3.2_trail5.0_beoff`: Return 470.51%, CAGR 32.28%, Sharpe 0.933, MaxDD -34.49%, PF 1.947, Trades 56
- Plateau conclusion: the mother is not a razor-edge peak. Best region remains squeeze-release with lookback around 20-22, stop ATR around 3.2-3.4, trail ATR around 5.0.

## Buy-And-Hold

- New research optimal vs B&H return delta: -385.65pp
- New research optimal vs B&H CAGR delta: -11.44pp
- New research optimal vs B&H Sharpe delta: 0.183
- New research optimal vs B&H Calmar delta: 0.369
- Interpretation: this remains closer to a lower-beta trend overlay with better risk-adjusted efficiency than buy-and-hold, not yet a standalone BTC return winner.

## Holding Continuity

- New research optimal avg hold: 61.7 4H bars
- New research optimal median hold: 40.4 4H bars
- New research optimal top10 winner contribution: 81.6%
- Interpretation: this mother still makes money through a small number of large winners, consistent with a real trend-following process rather than a fragmented scalping profile.

## Gatekeeper V2

- New research optimal full-size gate summary: {"baseline_gate": false, "yearly": true, "rolling_oos": true, "regime": true, "cost_stress": true, "slippage_stress": true, "execution_mode_stress": true, "intrabar_path_stress": true, "live_safety_check": true}
- New research optimal 35% gate summary: {"baseline_gate": false, "yearly": true, "rolling_oos": true, "regime": true, "cost_stress": true, "slippage_stress": true, "execution_mode_stress": true, "intrabar_path_stress": true, "live_safety_check": true}
- Important finding: conservative launch sizing passes yearly / rolling_oos / regime / cost_stress / slippage_stress / execution_mode_stress / intrabar_path_stress / live_safety_check.
- At 35% sizing the main remaining blocker is the legacy baseline_gate trade-count threshold, not a system safety or stress failure.
- At full-size research sizing baseline_gate failure is not only trade count, because MaxDD still misses the -30% cap.

## Conclusion

- launch_optimal: LAUNCH_NO_GO under current official Gatekeeper V2
- research_optimal: `lb20_stop3.2_trail5.0_beoff`
- default research tuple: next_bar_open + legacy_bar_extrema + midpoint + full_model
- stress/gate tuple only: live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model
- next step: keep only this long-only line as the primary mother and continue local optimization around this variant; do not return to old v85 long+short as the main research branch
