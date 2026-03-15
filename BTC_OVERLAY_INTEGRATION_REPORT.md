# BTC Overlay Integration Report

## Conclusion

- Best integration mode: AddOnOverlay
- Worth combining with BTC buy-and-hold: YES
- Positioning call: The line is best used as an add-on overlay.
- Single best recommendation: Choose AddOnOverlay if only one integration mode is deployed.
- Paper/live rehearsal: YES, AddOnOverlay is strong enough to justify paper/live rehearsal as an overlay sleeve.

## Core Findings

- SwitchingOverlay cuts max drawdown from -77.04% to -34.49%, but gives up too much absolute return to be the preferred integration.
- AddOnOverlay keeps return close to B&H while improving Sharpe by +0.041 and Calmar by +0.068.
- RiskReductionOverlay delivers the largest drawdown improvement among the always-invested variants, but sacrifices much more absolute return than AddOnOverlay.
- The overlay is materially more valuable as a portfolio module than as an attempted standalone BTC buy-and-hold replacement.

## Metrics

| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | PF | Exposure% | dRet vs B&H | dCAGR | dSharpe | dCalmar | MaxDD Improve |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B&H | 856.16 | 43.73 | 0.750 | 0.568 | -77.04 | 1.024 | 100.0 | +0.00 | +0.00 | +0.000 | +0.000 | +0.00 |
| SwitchingOverlay | 470.51 | 32.28 | 0.933 | 0.936 | -34.49 | 1.104 | 25.1 | -385.65 | -11.44 | +0.183 | +0.369 | +42.56 |
| AddOnOverlay | 960.72 | 46.14 | 0.791 | 0.636 | -72.61 | 1.027 | 108.8 | +104.56 | +2.42 | +0.041 | +0.068 | +4.43 |
| RiskReductionOverlay | 542.56 | 34.84 | 0.828 | 0.690 | -50.52 | 1.038 | 51.3 | -313.59 | -8.89 | +0.078 | +0.122 | +26.52 |

## Yearly Returns

| Year | B&H | Switching | AddOn | RiskReduction |
| --- | --- | --- | --- | --- |
| 2019 | 1.51 | -3.16 | 0.40 | -1.53 |
| 2020 | 300.26 | 144.17 | 345.85 | 194.53 |
| 2021 | 57.71 | 38.97 | 56.77 | 44.64 |
| 2022 | -64.65 | -2.48 | -59.22 | -35.69 |
| 2023 | 155.76 | 38.76 | 130.81 | 67.20 |
| 2024 | 120.96 | 17.61 | 108.44 | 63.45 |
| 2025 | -6.65 | 6.89 | -5.82 | -2.06 |
| 2026 | -22.82 | 0.72 | -21.01 | -13.15 |

## Bear And Risk Windows

| Window | B&H | Switching | AddOn | RiskReduction |
| --- | --- | --- | --- | --- |
| bear_2022 | -64.65 | -2.48 | -59.22 | -35.69 |
| china_deleveraging_2021 | -28.76 | 0.27 | -26.97 | -17.77 |
| ftx_shock | -13.03 | 0.00 | -10.75 | -4.47 |

## Details

- research_optimal: `lb20_stop3.2_trail5.0_beoff`
- default tuple: `next_bar_open + legacy_bar_extrema + midpoint + full_model`
- stress/gate tuple only: `live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model`
- positioning detail: As a portfolio building block, the overlay works best as a trend add-on: it is the only tested integration that improved total return, CAGR, Sharpe, Calmar, and max drawdown versus pure BTC buy-and-hold at the same time. RiskReductionOverlay remains the defensive alternative when drawdown reduction is the first priority.