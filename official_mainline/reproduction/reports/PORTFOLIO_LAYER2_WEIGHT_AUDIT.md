# Portfolio Layer-2 Weight Audit

- Scope: second-layer composition audit on the adopted mainline.
- Fixed signal layer:
  - `Core + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - `S1 + S2 ATR vol-targeting` enabled via `ATRVT_90D_med_035_150__ATRVT_60D_med_035_150`
  - `S1 gate contract = S1_VP_LB60_EA050_VR120`
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
- default: `Return 3321.25%`, `Calmar 3.209`, `MaxDD -23.81%`
- worst clusters: `3m -16.68%`, `6m -16.14%`
- recovery days: `36.0`
- avg / peak exposure: `92.84% / 400.00%`

## Best Balanced Candidate

- `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- default: `Return 3321.25%`, `Calmar 3.209`, `MaxDD -23.81%`
- worst clusters: `3m -16.68%`, `6m -16.14%`
- recovery days: `36.0`
- avg / peak exposure: `92.84% / 400.00%`

## Top Table

| Rank | Core | Sleeve1 | Sleeve2 | Return% | Calmar | MaxDD% | Worst6m | RecoveryDays | AvgExp% | PeakExp% | Stress? | Harsh? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.00 | 1.00 | 1.00 | 3321.25 | 3.209 | -23.81 | -16.14 | 36.0 | 92.84 | 400.00 | Y | Y |
| 2 | 0.75 | 1.00 | 1.25 | 2452.04 | 2.975 | -22.95 | -15.74 | 43.5 | 79.50 | 300.00 | Y | Y |
| 3 | 1.00 | 1.25 | 0.75 | 2983.16 | 2.932 | -25.06 | -16.95 | 8.7 | 93.32 | 300.00 | Y | Y |
| 4 | 0.75 | 1.00 | 1.00 | 2387.00 | 2.917 | -23.17 | -16.13 | 35.8 | 76.56 | 275.00 | Y | Y |
| 5 | 0.75 | 1.25 | 1.00 | 2530.25 | 2.874 | -24.04 | -16.55 | 11.3 | 82.32 | 300.00 | N | N |
| 6 | 1.00 | 0.75 | 1.25 | 2826.74 | 2.861 | -25.18 | -15.56 | 61.7 | 87.66 | 300.00 | N | N |
| 7 | 1.00 | 1.00 | 0.75 | 2839.91 | 2.855 | -25.27 | -16.61 | 43.5 | 87.56 | 275.00 | N | N |
| 8 | 1.25 | 1.00 | 0.75 | 3357.86 | 2.849 | -26.92 | -16.67 | 43.8 | 101.49 | 300.00 | N | N |

## Readout

- Current default sweet-spot answer: Yes.
- The most useful second-layer changes are mild posture shifts, not a redesign of the signal layer.
- The main tradeoff remains return vs path efficiency under the approved 3.0x cap envelope.
- Plot: `PORTFOLIO_LAYER2_WEIGHT_PLOTS.html`
- Full table: `PORTFOLIO_LAYER2_WEIGHT_TABLE.csv`