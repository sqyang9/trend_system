# Volatility Proxy Combo Audition

## Scope

- Mainline not changed.
- This is the dedicated audition for the integrated volatility-proxy combo:
  - `ATR vol-targeting on S1+S2`
  - `HV percentile >= 85% -> force high-churn core gate`
- Comparison set is intentionally tight:
  - current mainline replay
  - strongest single-defect economic fix `P0 only`
  - integrated challenger `Combo`

## Canonical Baseline

- Official mainline headline remains `Return 2878.61% / Calmar 2.854 / MaxDD -25.41%`.
- Local replay baseline inside this audition engine is `Return 2893.89% / Calmar 2.854 / MaxDD -25.46%`.

## Default

| System | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgTotalExp% |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current mainline replay | 2893.89 | 2.854 | -25.46 | -15.78 | -16.23 | 14.7 | 92.75 |
| Reference: P0 ATR vol-targeting on S1+S2 | 3072.90 | 3.073 | -24.17 | -16.11 | -15.64 | 43.5 | 92.75 |
| Challenger: Combo ATR VT + HV85 HC gate | 2995.89 | 3.044 | -24.17 | -16.13 | -15.63 | 43.5 | 92.57 |

## Delta Vs Mainline Replay

| Scenario | dReturn | dCalmar | dMaxDD |
| --- | --- | --- | --- |
| Default | +102.00pp | +0.191 | +1.29pp |
| Stress | +87.81pp | +0.155 | +0.99pp |
| Harsh friction | +145.99pp | +0.273 | +2.02pp |

## Delta Vs P0 Reference

| Scenario | dReturn | dCalmar | dMaxDD |
| --- | --- | --- | --- |
| Default | -77.00pp | -0.028 | +0.00pp |
| Stress | -76.42pp | -0.028 | +0.00pp |
| Harsh friction | -66.81pp | -0.025 | +0.00pp |

## Defect Windows

| System | W06 DD/Exp | W06 MaxDD% | W11 Entries | W11 Quick14 | W11 Quick30 | W11 AvgExp |
| --- | --- | --- | --- | --- | --- | --- |
| Current mainline replay | -49.5% | -23.13 | 4 | 50.0% | 75.0% | 0.929 |
| Reference: P0 ATR vol-targeting on S1+S2 | -47.4% | -22.15 | 4 | 50.0% | 75.0% | 0.929 |
| Challenger: Combo ATR VT + HV85 HC gate | -47.4% | -22.15 | 3 | 33.3% | 66.7% | 0.920 |

## Recent Windows

| System | 2024-12~2025-06 short14/30 | 2025-06~2025-12 short14/30 |
| --- | --- | --- |
| Current mainline replay | 4 entries, 50.0% / 75.0% | 3 entries, 66.7% / 66.7% |
| Reference: P0 ATR vol-targeting on S1+S2 | 4 entries, 50.0% / 75.0% | 3 entries, 66.7% / 66.7% |
| Challenger: Combo ATR VT + HV85 HC gate | 3 entries, 33.3% / 66.7% | 3 entries, 66.7% / 66.7% |

## Churn

| System | Full RE | Median Days | Quick14 | Quick30 | HC Quick14 | HC Quick30 |
| --- | --- | --- | --- | --- | --- | --- |
| Current mainline replay | 38 | 19.0 | 44.7% | 60.5% | 31.8% | 54.5% |
| Reference: P0 ATR vol-targeting on S1+S2 | 38 | 19.0 | 44.7% | 60.5% | 31.8% | 54.5% |
| Challenger: Combo ATR VT + HV85 HC gate | 37 | 19.2 | 43.2% | 59.5% | 32.0% | 52.0% |

## Annual Starts

- Combo vs mainline replay: Calmar better `6/7`, MaxDD better `7/7`, Return better `5/7`.
- Combo vs P0 reference: Calmar better `1/7`, MaxDD better `4/7`, Return better `1/7`.

## Readout

- Relative to the current mainline replay, Combo is clearly positive: default `Return 2995.89% / Calmar 3.044 / MaxDD -24.17%`, versus baseline `Return 2893.89% / Calmar 2.854 / MaxDD -25.46%`.
- Relative to `P0 only`, Combo gives back some portfolio economics: default `dReturn -77.00pp`, `dCalmar -0.028`, `dMaxDD +0.00pp`.
- The compensation is that Combo also repairs P1: W11 entries `4 -> 3`, quick14 `50.0% -> 33.3%`, while P0-only leaves W11 unchanged.
- Combo is therefore not the strongest pure-return candidate, but it is the strongest candidate that improves both P0 and P1 at the same time.

## Verdict

- As a replacement for the current mainline: `GO_TO_PROMOTION_AUDIT`.
- As a challenger against `P0 only`: `CONDITIONAL_GO`.
- The condition is strategic, not statistical: choose Combo if the next promotion round is explicitly about fixing both system defects in one package; choose P0 only if the round is strictly about maximizing portfolio economics.