# Volume-Profile Proxy Strengthening Fast Audit

- Scope: fast strengthening around the current winner plus an implemented-parity spot-check.
- Boundary: current official mainline remains unchanged.
- Strengthened winner: `vp_lb60_ea50_vr120`.

## Implemented Parity Spot-Check

- Manual research path winner `vp_lb60_ea50_vr120` default:
  - `Return 3321.25% / Sharpe 1.386 / Calmar 3.209 / MaxDD -23.81%`
- Shared-contract implemented replay for the same gate:
  - `Return 3321.25% / Sharpe 1.386 / Calmar 3.209 / MaxDD -23.81%`
- Parity delta:
  - `dReturn +0.00pp / dSharpe +0.000 / dCalmar +0.000 / dMaxDDImprove -0.00pp`

## Scenario Readout

| Scenario | Candidate | Return% | Sharpe | Calmar | MaxDD% | dReturn | dSharpe | dCalmar | dMaxDD Improve |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| default | vp_lb60_ea50_vr120 | 3321.25 | 1.386 | 3.209 | -23.81 | +141.34pp | +0.049 | +0.337 | +2.38pp |
| default | vp_lb60_ea35_vr110 | 3259.83 | 1.375 | 3.184 | -23.83 | +79.93pp | +0.038 | +0.313 | +2.36pp |
| harsh_friction | vp_lb60_ea50_vr120 | 3120.69 | 1.353 | 3.035 | -24.61 | +154.07pp | +0.051 | +0.357 | +2.76pp |
| harsh_friction | vp_lb60_ea35_vr110 | 3044.00 | 1.340 | 3.005 | -24.63 | +77.38pp | +0.038 | +0.326 | +2.74pp |
| stress | vp_lb60_ea50_vr120 | 3440.08 | 1.396 | 3.267 | -23.68 | +141.34pp | +0.048 | +0.336 | +2.32pp |
| stress | vp_lb60_ea35_vr110 | 3378.67 | 1.386 | 3.243 | -23.70 | +79.93pp | +0.038 | +0.312 | +2.30pp |

## Annual Starts

| Start | dReturn | dSharpe | dCalmar | dMaxDD Improve |
| --- | ---: | ---: | ---: | ---: |
| 2020 | +1.30pp | +0.032 | +0.292 | +2.38pp |
| 2021 | +2.25pp | +0.014 | +0.014 | +0.14pp |
| 2022 | +2.95pp | +0.023 | +0.038 | +0.49pp |
| 2023 | +2.48pp | +0.030 | +0.067 | +0.61pp |
| 2024 | +3.59pp | +0.041 | +0.098 | +0.61pp |
| 2025 | +1.30pp | +0.041 | +0.062 | +0.52pp |
| 2026 | +0.11pp | -0.000 | +0.016 | +0.31pp |

## Freeze-Date OOS

| Split | dReturn | dSharpe | dCalmar | dMaxDD Improve |
| --- | ---: | ---: | ---: | ---: |
| wf_2023_plus | +2.48pp | +0.030 | +0.067 | +0.61pp |
| wf_2025_plus | +1.30pp | +0.041 | +0.062 | +0.52pp |

## Verdict

- If the current winner still dominates after the parity spot-check, it remains the reserve front-runner.
- If the looser neighbor wins on default but loses on stress/harsh or OOS, it should not replace the current reserve winner.