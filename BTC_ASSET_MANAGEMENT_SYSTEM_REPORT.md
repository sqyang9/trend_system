# BTC Asset Management System Report

## Final Conclusion

- Recommended structure: Core+AddOnOverlay+RiskOff
- Main judgment: Upgrade from AddOn-only to AddOn + Risk-Off. Do not promote Bear Short into the default system.
- Keep AddOnOverlay unchanged: YES
- Risk-Off module value: YES
- Bear Short sleeve value: LOW / NOT WORTH DEFAULT INCLUSION
- Better than plain B&H as an asset-management framework: YES

## Module Roles

- Module A `AddOnOverlay`: keep the already validated long-only trend sleeve unchanged as the return-enhancing leg.
- Module B `Risk-Off Overlay`: reduce core BTC exposure only when the long-term regime is clearly broken, with low-frequency state changes.
- Module C `Bear Short Sleeve`: only activate in high-confidence bearish/crash states as an extreme-downside hedge, not as a symmetric all-weather short strategy.

## Module Candidates

### Risk-Off Candidates

- B1_TrendBreakRiskOff_ema200_flat: Return 1574.98%, CAGR 57.27%, Sharpe 1.058, Calmar 1.168, MaxDD -49.03%, avg core exposure 58.9%, state changes 223
- B1_TrendBreakRiskOff_ema220_flat: Return 1896.79%, CAGR 61.78%, Sharpe 1.112, Calmar 1.199, MaxDD -51.51%, avg core exposure 58.9%, state changes 203
- B1_TrendBreakRiskOff_ema200_to35: Return 1505.87%, CAGR 56.21%, Sharpe 1.012, Calmar 0.978, MaxDD -57.45%, avg core exposure 73.3%, state changes 223
- B2_TrendVolRiskOff_ema200_to35: Return 1036.45%, CAGR 47.77%, Sharpe 0.848, Calmar 0.669, MaxDD -71.44%, avg core exposure 94.7%, state changes 120
- B3_StructureBreakRiskOff_flat: Return 909.90%, CAGR 45.00%, Sharpe 0.795, Calmar 0.640, MaxDD -70.26%, avg core exposure 97.1%, state changes 418

### Bear Short Candidates

- C1_BreakdownQualityShort: Return 1879.84%, CAGR 61.56%, Sharpe 1.103, Calmar 1.186, MaxDD -51.89%, active 2.02%, state changes 394
- C2_CrashSleeveShort: Return 1888.29%, CAGR 61.67%, Sharpe 1.101, Calmar 1.190, MaxDD -51.81%, active 0.50%, state changes 66
- C3_ConfirmedBreakShort: Return 1900.46%, CAGR 61.83%, Sharpe 1.109, Calmar 1.212, MaxDD -50.99%, active 0.75%, state changes 96

## Parameter Analysis

### Risk-Off Grid

| EMA Len | Off Weight | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Avg Core Exposure% | State Changes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 180 | 0.00 | 1179.20 | 50.61 | 0.983 | 1.014 | -49.90 | 58.9 | 261 |
| 180 | 0.35 | 1250.33 | 51.92 | 0.968 | 0.897 | -57.87 | 73.3 | 261 |
| 180 | 0.50 | 1228.53 | 51.53 | 0.936 | 0.841 | -61.28 | 79.5 | 261 |
| 200 | 0.00 | 1574.98 | 57.27 | 1.058 | 1.168 | -49.03 | 58.9 | 223 |
| 200 | 0.35 | 1505.87 | 56.21 | 1.012 | 0.978 | -57.45 | 73.3 | 223 |
| 200 | 0.50 | 1416.48 | 54.78 | 0.968 | 0.898 | -61.02 | 79.5 | 223 |
| 220 | 0.00 | 1896.79 | 61.78 | 1.112 | 1.199 | -51.51 | 58.9 | 203 |
| 220 | 0.35 | 1699.79 | 59.10 | 1.046 | 1.009 | -58.58 | 73.3 | 203 |
| 220 | 0.50 | 1554.93 | 56.97 | 0.993 | 0.921 | -61.83 | 79.5 | 203 |

### Bear Short Grid

| Lookback | Short Weight | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Active% | State Changes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 42 | 0.20 | 1898.46 | 61.80 | 1.111 | 1.205 | -51.27 | 0.80 | 104 |
| 42 | 0.25 | 1898.79 | 61.80 | 1.110 | 1.207 | -51.21 | 0.80 | 104 |
| 42 | 0.35 | 1899.35 | 61.81 | 1.109 | 1.209 | -51.11 | 0.80 | 104 |
| 63 | 0.20 | 1898.38 | 61.80 | 1.111 | 1.206 | -51.25 | 0.78 | 102 |
| 63 | 0.25 | 1898.69 | 61.80 | 1.110 | 1.207 | -51.19 | 0.78 | 102 |
| 63 | 0.35 | 1899.21 | 61.81 | 1.109 | 1.210 | -51.08 | 0.78 | 102 |
| 84 | 0.20 | 1899.09 | 61.81 | 1.111 | 1.207 | -51.20 | 0.75 | 96 |
| 84 | 0.25 | 1899.58 | 61.81 | 1.111 | 1.209 | -51.13 | 0.75 | 96 |
| 84 | 0.35 | 1900.46 | 61.83 | 1.109 | 1.212 | -50.99 | 0.75 | 96 |

## Combination Results

| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | PF | Net Exposure% | Gross Exposure% | dRet vs B&H | dRet vs AddOn | dMaxDD vs B&H | dMaxDD vs AddOn |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B&H | 856.16 | 43.73 | 0.750 | 0.568 | -77.04 | 1.024 | 100.0 | 100.0 | +0.00 | -104.56 | +0.00 | -4.43 |
| Core+AddOnOverlay | 960.72 | 46.14 | 0.791 | 0.636 | -72.61 | 1.027 | 108.8 | 108.8 | +104.56 | +0.00 | +4.43 | +0.00 |
| Core+RiskOff | 1792.22 | 60.39 | 1.082 | 1.114 | -54.21 | 1.067 | 58.9 | 58.9 | +936.07 | +831.50 | +22.83 | +18.40 |
| Core+AddOnOverlay+RiskOff | 1896.79 | 61.78 | 1.112 | 1.199 | -51.51 | 1.069 | 67.7 | 67.7 | +1040.63 | +936.07 | +25.53 | +21.10 |
| Core+AddOnOverlay+RiskOff+BearShort | 1900.46 | 61.83 | 1.109 | 1.212 | -50.99 | 1.069 | 67.5 | 68.0 | +1044.31 | +939.74 | +26.05 | +21.62 |

## Bear And Risk Windows

| Window | B&H | Core+AddOnOverlay | Core+RiskOff | Core+AddOnOverlay+RiskOff | Core+AddOnOverlay+RiskOff+BearShort |
| --- | --- | --- | --- | --- | --- |
| covid_crash_2020 | -14.67 | -10.24 | -6.24 | -2.18 | -2.57 |
| china_deleveraging_2021 | -28.76 | -26.97 | -1.92 | -1.77 | -2.53 |
| bear_2022 | -64.65 | -59.22 | -45.06 | -42.25 | -41.78 |
| ftx_shock | -13.03 | -10.75 | -11.38 | -10.31 | -9.91 |

## Interpretation

- Risk-Off assessment: Risk-Off adds real asset-management value. Even after charging simple one-way turnover costs, the trend-break regime family materially improves return, CAGR, Sharpe, Calmar, and max drawdown versus both pure BTC buy-and-hold and AddOn-only. The result is not a single-point fluke: EMA 200-220 with full risk-off all stay in the same strong plateau.
- Bear Short assessment: Bear Short helps only at the margin. Across the tested neighborhood, the incremental lift over AddOn + Risk-Off stays tiny: only a few total-return points and less than 1 percentage point of max-drawdown improvement. That is too small to justify the extra operational and research complexity right now.
- Final structure call: As a BTC asset-management framework, the strongest current structure is a three-part stack with only two active defaults: keep the proven AddOnOverlay sleeve, add a low-frequency Risk-Off core allocation rule, and leave Bear Short as an optional research sleeve rather than part of the production default. This gives a cleaner improvement path than either plain B&H or AddOn-only.

## Research Boundary

- The AddOnOverlay signal itself was not modified.
- Default execution tuple stayed at `next_bar_open + legacy_bar_extrema + midpoint + full_model`.
- Risk-Off and Bear Short were tested as simple, explainable low-frequency modules with small parameter neighborhoods only.

## Parameter And Cost Assumptions

- research_optimal: `lb20_stop3.2_trail5.0_beoff`
- default tuple: `next_bar_open + legacy_bar_extrema + midpoint + full_model`
- stress/gate tuple only: `live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model`
- core risk-off one-way cost assumption: 0.11% of changed notional
- bear short one-way cost assumption: 0.16% of changed notional