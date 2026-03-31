# AddOn Grading Archive

## Base Grading Line

Current grading archive is centered on:

- `Core + GradedAddOn[compression_breakout]`

Features:

- `compression_quality`
- `squeeze_count`
- `breakout_distance_atr`

Base weights:

- `weak = 0.25`
- `base = 0.35`
- `strong = 0.50`

## Why This Line Mattered

The grading line was the first active extension that improved OOS behavior without changing the mother strategy.

Promotion validation result versus binary AddOn:

- full sample: `+14.41pp Return`, `+0.001 Sharpe`, `-0.002 Calmar`, `-0.72pp MaxDD improvement`
- OOS: `strict win ratio = 1.00`, `avg delta Return = +4.52pp`, `avg delta Sharpe = +0.035`, `avg delta Calmar = +0.202`

This made the line clearly promising, but not promotable.

## Promotion Blocker

Main blocker:

- MaxDD remained slightly worse than the binary AddOn baseline

So the line had:

- good OOS behavior
- acceptable execution stability
- but insufficient drawdown improvement for promotion

## Narrow Repair Attempt

The narrow repair pass only allowed internal grading tweaks.

Best repair candidate:

- `repair_strong048`

Meaning:

- keep weak and base unchanged
- reduce strong tier from `0.50` to `0.48`

Result versus binary AddOn:

- `+10.50pp Return`
- `-0.000 Sharpe`
- `-0.003 Calmar`
- `-0.76pp MaxDD improvement`
- OOS remained strong: `strict win ratio = 0.67`, `avg delta Return = +4.37pp`, `avg delta Sharpe = +0.032`, `avg delta Calmar = +0.187`

Conclusion:

- repair preserved much of the OOS edge
- repair still failed to remove MaxDD degradation

## Regime-Cap Side Study

A later narrow regime-cap modulation study was also attempted.

Outcome:

- not promotable
- reduced exposure but did not solve the real problem
- ranking stayed below both binary AddOn and uncapped graded AddOn

## Final Status

AddOn grading is:

- promising
- active extension line
- not promotable yet

It remains the only active extension line that is still worth continuing under the locked baseline framework.
