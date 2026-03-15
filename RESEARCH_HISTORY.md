# Research History

## Stage 1: Core Trend Strategy

The current BTC system started from the long-only mother line built on `squeeze_release_20`.

- Strategy role: low-frequency BTC trend-following system
- Current `research_optimal`: `lb20_stop3.2_trail5.0_beoff`
- Signal idea: wait for compression, then enter a breakout release inside a bullish higher-timeframe trend regime
- Trend logic: price above long EMA, positive EMA slope, mild ADX confirmation, acceptable breakout bar quality
- Trade template: a small number of trend entries, few trades, large winners, exits driven mainly by ATR trailing rather than fixed profit taking
- Execution design: signal observed on completed 4h bar, position change modeled under the locked execution tuple rather than idealized same-bar assumptions

This line replaced the old `v85` long+short line as the primary research object because it behaved more like a real BTC trend mother and less like a fragile multi-leg backtest artifact.

## Stage 2: Execution Alignment

The repository then separated default research from stress validation.

Default execution tuple:

- `next_bar_open`
- `legacy_bar_extrema`
- `midpoint`
- `full_model`

Stress / gate tuple:

- `live_runner_next_5m_close`
- `segment_path_same_bar`
- `pessimistic`
- `full_model`

Execution alignment was validated by:

- keeping bar-level causality explicit
- modeling entry and exit timing on the next execution event rather than current-bar hindsight
- rerunning key modules under the stress tuple
- keeping stress/gate conclusions separate from default-tuple research conclusions

This alignment step is the main reason later portfolio-layer conclusions were split into `exploratory`, `aligned but preliminary`, and promotable states instead of being treated as equal by default.

## Stage 3: AddOn Overlay

After the mother line stabilized, the system was reframed as an overlay on top of BTC buy-and-hold.

Structure:

- Core BTC holding
- Binary AddOn trend sleeve

Binary AddOn overlay means:

- hold the BTC core continuously
- add an extra trend sleeve when the validated long-only signal is active

Relative to pure BTC buy-and-hold, the committed overlay integration result showed:

- Return `960.72%` vs `856.16%`
- CAGR `46.14%` vs `43.73%`
- Sharpe `0.791` vs `0.750`
- Calmar `0.636` vs `0.568`
- MaxDD `-72.61%` vs `-77.04%`

This is why `Core BTC holding + Binary AddOn overlay` became the locked baseline structure.

## Stage 4: Risk-Off Research Line

Risk-Off was explored as a portfolio module, then aligned, then repeatedly tested for promotion.

Key structures tested:

- EMA200 / EMA210 / EMA220 regime triggers
- flat core exits
- two-stage exits
- re-entry timing repairs

The line progressed through:

- exploratory allocation study
- execution-aligned validation
- core-off-weight study
- promotion v1
- promotion v2
- narrow re-entry checks

Final result:

- directionally valid
- execution-aligned
- promotion frozen

Why promotion failed:

- the line helped on downside control
- the EMA200-220 family behaved like a stable plateau, not a single lucky point
- but bull / recovery opportunity cost remained too large
- even the best late repair candidate, `RO_EMA220_REENTRY_CLOSE_HOLD_3`, still failed to remove promotion blockers

Risk-Off therefore became an archived direction, not an active baseline module.

## Stage 5: AddOn Grading

Once Risk-Off was frozen, active extension research shifted to smarter AddOn sizing.

Current grading line:

- `Core + GradedAddOn[compression_breakout]`

Features:

- `compression_quality`
- `squeeze_count`
- `breakout_distance_atr`

Base tier weights:

- `weak = 0.25`
- `base = 0.35`
- `strong = 0.50`

Key result:

- full sample vs binary AddOn: `+14.41pp Return`, `+0.001 Sharpe`, `-0.002 Calmar`, `-0.72pp MaxDD improvement`
- OOS: `strict win ratio = 1.00`, `avg delta Return = +4.52pp`, `avg delta Sharpe = +0.035`, `avg delta Calmar = +0.202`

Status:

- promising
- not promotable yet

The main blocker is still slight MaxDD degradation versus the binary AddOn baseline.

## Latest Conclusion

The repository is currently in this state:

- locked baseline: `Core BTC holding + Binary AddOn overlay`
- archived direction: Risk-Off promotion line
- active extension line: AddOn grading on `compression_breakout`

No new baseline has replaced the binary AddOn structure yet.
