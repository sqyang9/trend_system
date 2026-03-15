# Promotion Results

## Summary Table

| Line | Role | Key Result | Promotion Outcome |
| --- | --- | --- | --- |
| Binary AddOn | Baseline overlay | Improved return, Sharpe, Calmar, and MaxDD vs BTC buy-and-hold in committed overlay study | Accepted as locked baseline structure |
| AddOn Grading | Active extension line | Strong OOS profile but slight full-sample MaxDD degradation vs Binary AddOn | Not promotable yet |
| Risk-Off | Archived portfolio module | Directionally valid and execution-aligned, but repeated promotion attempts failed | Frozen / archived |

## Binary AddOn

Binary AddOn became the baseline because the committed overlay integration result showed a clean, understandable improvement over BTC buy-and-hold:

- Return `960.72%` vs `856.16%`
- CAGR `46.14%` vs `43.73%`
- Sharpe `0.791` vs `0.750`
- Calmar `0.636` vs `0.568`
- MaxDD `-72.61%` vs `-77.04%`

This is the only structure that has already crossed from research into baseline status.

## AddOn Grading

Lead candidate:

- `Core + GradedAddOn[compression_breakout]`

Promotion validation result:

- full sample vs binary AddOn: `+14.41pp Return`, `+0.001 Sharpe`, `-0.002 Calmar`, `-0.72pp MaxDD improvement`
- OOS: `strict win ratio = 1.00`, `avg delta Return = +4.52pp`, `avg delta Sharpe = +0.035`, `avg delta Calmar = +0.202`

Why promotion failed:

- drawdown was still slightly worse than the binary AddOn baseline
- later narrow repair work preserved much of the OOS edge, but still did not remove the MaxDD degradation

Current status:

- promising
- active extension line
- baseline unchanged

## Risk-Off

Risk-Off produced a valid direction, but never cleared promotion.

What it proved:

- downside protection logic could be built in an execution-aligned way
- EMA200-220 behaved like a plateau, not a single isolated point

What blocked promotion:

- bull / recovery opportunity cost
- repeated failure to combine downside improvement with enough OOS stability
- final narrow repair still failed to remove the blocker

Current status:

- archived
- promotion frozen
- not part of baseline
