# ATRVT H90 Audition

## Scope

- Mainline not changed.
- This audition only revisits the ATR vol-targeting layer after fixing the ATR alignment bug.
- Core side is held fixed at the current combo structure:
  - `EMA250` sell-side
  - stable `close3`
  - high-churn `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the stricter gate earlier

## Default

| Candidate | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgExp% | AvgS1Scale | AvgS2Scale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current combo base: 180d med / 0.35-1.50 both | 2946.79 | 2.574 | -28.41 | -16.38 | -16.25 | 19.0 | 94.41 | 1.018 | 1.018 |
| Challenger: 90d med / 0.35-1.50 both | 3114.74 | 2.762 | -27.02 | -16.73 | -16.31 | 19.0 | 94.98 | 1.013 | 1.013 |
| Reserve: S1 90d med / S2 base | 3023.76 | 2.730 | -27.05 | -17.07 | -16.74 | 18.2 | 94.56 | 1.013 | 1.018 |

## Readout

- Current combo base replay: `Return 2946.79% / Calmar 2.574 / MaxDD -28.41%`.
- H90 challenger: `Return 3114.74% / Calmar 2.762 / MaxDD -27.02%`.
- Reserve asym candidate: `Return 3023.76% / Calmar 2.730 / MaxDD -27.05%`.
- H90 vs base default delta: `dReturn +167.95pp / dCalmar +0.188 / dMaxDD +1.39pp`.
- H90 vs base stress delta: `dCalmar +0.189`.
- H90 vs base harsh delta: `dCalmar +0.171`.

## W06 / W11

- W06 `DD/Exp`: base `-46.9%` -> H90 `-44.0%`.
- W06 median scales: base `S1 1.130 / S2 1.130` -> H90 `S1 1.165 / S2 1.165`.
- W11 avg exposure: base `1.016` -> H90 `0.980`.
- W11 median scales: base `S1 1.108 / S2 1.108` -> H90 `S1 1.072 / S2 1.072`.

## Annual Starts

- H90 vs base: Calmar better `6/7`, MaxDD better `7/7`, Return better `4/7`.