# Portfolio Layer-2 Weight Audit

- Scope: second-layer composition audit on the adopted mainline.
- Fixed signal layer:
  - `Core + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - sell-side `EMA250`
  - re-entry `Weekly RSI(14) <= 30 hold`
- Method:
  - default runs compare a focused set of posture candidates around the current `1.0 / 1.0 / 1.0` mix
  - finalists are then checked under `stress` and `harsher friction`
  - this is a portfolio-layer composition audit, not a new signal-layer parameter search

## Current Default

- `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- default: `Return 2705.88%`, `Calmar 2.021`, `MaxDD -35.06%`
- worst clusters: `3m -14.84%`, `6m -19.41%`
- recovery days: `327.7`
- avg / peak exposure: `97.52% / 300.00%`

## Best Balanced Candidate

- `Core 0.75 / Sleeve1 1.25 / Sleeve2 1.00`
- default: `Return 2329.48%`, `Calmar 2.129`, `MaxDD -31.45%`
- worst clusters: `3m -15.48%`, `6m -17.12%`
- recovery days: `19.7`
- avg / peak exposure: `88.63% / 300.00%`

## Top Table

| Rank | Core | Sleeve1 | Sleeve2 | Return% | Calmar | MaxDD% | Worst6m | RecoveryDays | AvgExp% | PeakExp% | Stress? | Harsh? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.75 | 1.25 | 1.00 | 2329.48 | 2.129 | -31.45 | -17.12 | 19.7 | 88.63 | 300.00 | Y | Y |
| 2 | 0.75 | 1.00 | 1.25 | 2277.00 | 2.095 | -31.68 | -16.97 | 350.8 | 85.29 | 300.00 | Y | Y |
| 3 | 1.00 | 1.25 | 0.75 | 2758.35 | 2.050 | -34.81 | -19.00 | 327.2 | 100.87 | 300.00 | Y | Y |
| 4 | 0.75 | 1.00 | 1.00 | 2211.96 | 2.034 | -32.26 | -17.37 | 327.5 | 82.35 | 275.00 | Y | Y |
| 5 | 1.00 | 1.00 | 1.00 | 2705.88 | 2.021 | -35.06 | -19.41 | 327.7 | 97.52 | 300.00 | Y | Y |
| 6 | 1.00 | 0.75 | 1.25 | 2653.41 | 1.992 | -35.31 | -19.84 | 350.8 | 94.17 | 300.00 | N | N |
| 7 | 1.25 | 1.00 | 0.75 | 3134.75 | 1.977 | -37.85 | -21.43 | 327.2 | 109.76 | 300.00 | N | N |
| 8 | 1.00 | 1.00 | 0.75 | 2640.83 | 1.960 | -35.83 | -19.87 | 327.2 | 94.59 | 275.00 | N | N |

## Readout

- Current default sweet-spot answer: No.
- The most useful second-layer changes are mild posture shifts, not a redesign of the signal layer.
- The main tradeoff remains return vs path efficiency under the approved 3.0x cap envelope.
- Plot: `PORTFOLIO_LAYER2_WEIGHT_PLOTS.html`
- Full table: `PORTFOLIO_LAYER2_WEIGHT_TABLE.csv`