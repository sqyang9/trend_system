# System Re-Entry Qualification Upgrade

- Scope: system-level upgrade candidates for choppy-downtrend false re-entry defense.
- Stable environment remains `close3`.
- Upgrade focus: add an earlier `unstable` tier before current `highly_unstable` tier, and lightly test breakout-window length.

## Default Summary

| Candidate | Return% | Calmar | MaxDD% | W11 Entries | W11 quick14 | W11 quick30 | HC quick14 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current mainline | 2893.89 | 2.854 | -25.46 | 4 | 50.0% | 75.0% | 31.8% |
| Unstable 1/3 strict; HC 2/3 breakout4 | 2893.89 | 2.854 | -25.46 | 4 | 50.0% | 75.0% | 31.8% |
| Unstable 1/2 strict; HC 2/3 breakout4 | 2779.42 | 2.842 | -25.18 | 4 | 50.0% | 75.0% | 35.7% |
| Unstable 1/2 strict; HC 2/4 breakout4 | 2657.28 | 2.689 | -26.17 | 4 | 50.0% | 75.0% | 30.4% |
| Unstable 1/2 strict; HC 2/3 breakout3 | 2660.44 | 2.413 | -29.18 | 4 | 50.0% | 75.0% | 34.6% |

## Stress / Harsh

| Candidate | Stress Calmar | Stress MaxDD% | Harsh Calmar | Harsh MaxDD% |
| --- | --- | --- | --- | --- |
| Current mainline | 2.968 | -24.89 | 2.643 | -26.70 |
| Unstable 1/2 strict; HC 2/3 breakout4 | 2.930 | -24.81 | 2.631 | -26.40 |
| Unstable 1/3 strict; HC 2/3 breakout4 | 2.968 | -24.89 | 2.643 | -26.70 |
| Unstable 1/2 strict; HC 2/3 breakout3 | 2.512 | -28.47 | 2.278 | -30.00 |
| Unstable 1/2 strict; HC 2/4 breakout4 | 2.794 | -25.59 | 2.487 | -27.41 |

## Readout

- Current mainline default: Return `2893.89%`, Calmar `2.854`, MaxDD `-25.46%`.
- Best W11-oriented candidate in this screen: `Unstable 1/2 strict; HC 2/4 breakout4` with W11 entries `4`, quick14 `50.0%`, HC quick14 `30.4%`.
- This screen asks whether the current one-tier high-churn gate should become a two-tier qualification system.