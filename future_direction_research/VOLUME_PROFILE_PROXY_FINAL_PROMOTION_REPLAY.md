# Volume-Profile Proxy Final Promotion Replay

- Challenger: `vp_lb60_ea50_vr120`.
- This replay uses the implemented shared `S1 gate` contract, not the old manual research path.
- Current locked mainline remains unchanged unless this replay clears promotion standard.

## Scenario Readout

| Scenario | Return% | Sharpe | Calmar | MaxDD% | dReturn | dSharpe | dCalmar | dMaxDD Improve | Cand | Pass | PassRate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | 3388.35 | 1.385 | 3.192 | -23.81 | +180.09pp | +0.053 | +0.346 | +2.38pp | 57 | 47 | 82.5% |
| stress | 3514.31 | 1.395 | 3.251 | -23.68 | +180.09pp | +0.052 | +0.345 | +2.32pp | 57 | 47 | 82.5% |
| harsh_friction | 3187.34 | 1.352 | 3.021 | -24.61 | +189.37pp | +0.054 | +0.365 | +2.76pp | 57 | 47 | 82.5% |

## Annual Starts

| Start | dReturn | dSharpe | dCalmar | dMaxDD Improve |
| --- | ---: | ---: | ---: | ---: |
| 2020 | +38.07pp | +0.036 | +0.302 | +2.38pp |
| 2021 | +7.62pp | +0.019 | +0.026 | +0.14pp |
| 2022 | +5.74pp | +0.031 | +0.051 | +0.49pp |
| 2023 | +5.62pp | +0.041 | +0.088 | +0.61pp |
| 2024 | +5.75pp | +0.055 | +0.126 | +0.61pp |
| 2025 | +2.51pp | +0.073 | +0.108 | +0.52pp |
| 2026 | +1.18pp | +0.150 | +0.403 | +0.31pp |
- Annual wins: Return 7/7, Sharpe 7/7, Calmar 7/7, MaxDD 7/7.

## Freeze-Date OOS

| Split | dReturn | dSharpe | dCalmar | dMaxDD Improve |
| --- | ---: | ---: | ---: | ---: |
| wf_2023_plus | +5.62pp | +0.041 | +0.088 | +0.61pp |
| wf_2025_plus | +2.51pp | +0.073 | +0.108 | +0.52pp |

## Verdict

- Promotion standard for replacement:
  - positive on default / stress / harsh
  - annual starts mostly positive
  - freeze-date OOS positive
  - implemented replay aligned with earlier research