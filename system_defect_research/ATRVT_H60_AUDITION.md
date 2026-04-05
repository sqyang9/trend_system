# ATRVT H60 Audition

## Scope

- Mainline not changed.
- This audition only revisits the ATR vol-targeting layer after the H90-centered refinement screen.
- Core side is held fixed at the current combo structure:
  - `EMA250` sell-side
  - stable `close3`
  - high-churn `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the stricter gate earlier

## Default

| Candidate | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgExp% | AvgS1Scale | AvgS2Scale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Reference: 180d med / 0.35-1.50 both | 2946.79 | 2.574 | -28.41 | -16.38 | -16.25 | 19.0 | 94.41 | 1.018 | 1.018 |
| Reference: 90d med / 0.35-1.50 both | 3114.74 | 2.762 | -27.02 | -16.73 | -16.31 | 19.0 | 94.98 | 1.013 | 1.013 |
| Challenger: 60d med / 0.35-1.50 both | 3327.75 | 2.988 | -25.59 | -16.89 | -16.22 | 19.3 | 95.10 | 1.014 | 1.014 |

## Readout

- 180d reference: `Return 2946.79% / Calmar 2.574 / MaxDD -28.41%`.
- 90d reference: `Return 3114.74% / Calmar 2.762 / MaxDD -27.02%`.
- 60d challenger: `Return 3327.75% / Calmar 2.988 / MaxDD -25.59%`.
- H60 vs H90 default delta: `dReturn +213.01pp / dCalmar +0.226 / dMaxDD +1.44pp`.
- H60 vs H90 stress delta: `dCalmar +0.227`.
- H60 vs H90 harsh delta: `dCalmar +0.207`.

## W06 / W11

- W06 `DD/Exp`: H90 `-44.0%` -> H60 `-40.9%`.
- W06 median scales: H90 `S1 1.165 / S2 1.165` -> H60 `S1 1.110 / S2 1.110`.
- W11 avg exposure: H90 `0.980` -> H60 `0.976`.
- W11 median scales: H90 `S1 1.072 / S2 1.072` -> H60 `S1 1.078 / S2 1.078`.

## Annual Starts

- H60 vs H90: Calmar better `5/7`, MaxDD better `7/7`, Return better `4/7`.