# Portfolio Layer-2 Weight Audit

- Scope: second-layer composition audit on the adopted mainline.
- Fixed signal layer:
  - `Core + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - override `Weekly RSI(14) <= 30 hold`
- Method:
  - default runs compare a focused set of posture candidates around the current `1.0 / 1.0 / 1.0` mix
  - finalists are then checked under `stress` and `harsher friction`
  - this is a portfolio-layer composition audit, not a new signal-layer parameter search

## Current Default

- `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- default: `Return 2878.61%`, `Calmar 2.854`, `MaxDD -25.41%`
- worst clusters: `3m -15.78%`, `6m -16.22%`
- recovery days: `14.7`
- avg / peak exposure: `92.75% / 300.00%`

## Best Balanced Candidate

- `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- default: `Return 2878.61%`, `Calmar 2.854`, `MaxDD -25.41%`
- worst clusters: `3m -15.78%`, `6m -16.22%`
- recovery days: `14.7`
- avg / peak exposure: `92.75% / 300.00%`

## Top Table

| Rank | Core | Sleeve1 | Sleeve2 | Return% | Calmar | MaxDD% | Worst6m | RecoveryDays | AvgExp% | PeakExp% | Stress? | Harsh? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.00 | 1.00 | 1.00 | 2878.61 | 2.854 | -25.41 | -16.22 | 14.7 | 92.75 | 300.00 | Y | Y |
| 2 | 1.00 | 0.75 | 1.25 | 2826.14 | 2.821 | -25.53 | -15.52 | 61.0 | 89.41 | 300.00 | Y | Y |
| 3 | 1.25 | 1.00 | 0.75 | 3350.66 | 2.800 | -27.37 | -16.61 | 43.8 | 103.80 | 300.00 | Y | Y |
| 4 | 1.00 | 1.00 | 0.75 | 2813.56 | 2.792 | -25.75 | -16.55 | 43.8 | 89.82 | 275.00 | Y | Y |
| 5 | 1.25 | 0.75 | 1.00 | 3298.19 | 2.751 | -27.70 | -16.10 | 61.2 | 100.45 | 300.00 | N | N |
| 6 | 1.00 | 0.75 | 1.00 | 2761.09 | 2.733 | -26.12 | -15.85 | 61.0 | 86.47 | 275.00 | N | N |
| 7 | 1.00 | 1.25 | 0.75 | 2931.08 | 2.600 | -28.08 | -16.88 | 19.0 | 96.10 | 300.00 | N | N |
| 8 | 0.75 | 1.00 | 1.25 | 2406.55 | 2.568 | -26.40 | -15.68 | 19.0 | 81.71 | 300.00 | N | N |

## Readout

- Current default sweet-spot answer: Yes.
- The most useful second-layer changes are mild posture shifts, not a redesign of the signal layer.
- The main tradeoff remains return vs path efficiency under the approved 3.0x cap envelope.
- Plot: `PORTFOLIO_LAYER2_WEIGHT_PLOTS.html`
- Full table: `PORTFOLIO_LAYER2_WEIGHT_TABLE.csv`