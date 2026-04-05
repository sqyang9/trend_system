# Portfolio Layer-2 Weight Audit

- Scope: second-layer composition audit on the adopted mainline.
- Fixed signal layer:
  - `Core + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - `S1 + S2 ATR vol-targeting` enabled
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the high-churn gate earlier
  - override `Weekly RSI(14) <= 30 hold`
- Method:
  - default runs compare a focused set of posture candidates around the current `1.0 / 1.0 / 1.0` mix
  - finalists are then checked under `stress` and `harsher friction`
  - this is a portfolio-layer composition audit, not a new signal-layer parameter search

## Current Default

- `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- default: `Return 2980.07%`, `Calmar 3.040`, `MaxDD -24.16%`
- worst clusters: `3m -16.13%`, `6m -15.63%`
- recovery days: `43.5`
- avg / peak exposure: `92.57% / 300.00%`

## Best Balanced Candidate

- `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- default: `Return 2980.07%`, `Calmar 3.040`, `MaxDD -24.16%`
- worst clusters: `3m -16.13%`, `6m -15.63%`
- recovery days: `43.5`
- avg / peak exposure: `92.57% / 300.00%`

## Top Table

| Rank | Core | Sleeve1 | Sleeve2 | Return% | Calmar | MaxDD% | Worst6m | RecoveryDays | AvgExp% | PeakExp% | Stress? | Harsh? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.00 | 1.00 | 1.00 | 2980.07 | 3.040 | -24.16 | -15.63 | 43.5 | 92.57 | 300.00 | Y | Y |
| 2 | 1.00 | 0.75 | 1.25 | 2749.54 | 2.792 | -25.53 | -15.51 | 61.0 | 89.22 | 300.00 | Y | Y |
| 3 | 1.25 | 1.00 | 0.75 | 3254.92 | 2.771 | -27.37 | -16.63 | 43.8 | 103.56 | 300.00 | Y | Y |
| 4 | 1.00 | 1.00 | 0.75 | 2736.97 | 2.763 | -25.75 | -16.56 | 43.8 | 89.64 | 275.00 | Y | Y |
| 5 | 1.25 | 0.75 | 1.00 | 3202.45 | 2.722 | -27.70 | -16.10 | 61.2 | 100.22 | 300.00 | N | N |
| 6 | 1.00 | 0.75 | 1.00 | 2684.50 | 2.705 | -26.12 | -15.85 | 61.0 | 86.29 | 275.00 | N | N |
| 7 | 1.00 | 1.25 | 0.75 | 2854.48 | 2.575 | -28.08 | -16.90 | 19.0 | 95.92 | 300.00 | N | N |
| 8 | 0.75 | 1.00 | 1.25 | 2349.11 | 2.544 | -26.40 | -15.67 | 19.0 | 81.57 | 300.00 | N | N |

## Readout

- Current default sweet-spot answer: Yes.
- The most useful second-layer changes are mild posture shifts, not a redesign of the signal layer.
- The main tradeoff remains return vs path efficiency under the approved 3.0x cap envelope.
- Plot: `PORTFOLIO_LAYER2_WEIGHT_PLOTS.html`
- Full table: `PORTFOLIO_LAYER2_WEIGHT_TABLE.csv`