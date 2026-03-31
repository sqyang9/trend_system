# Risk-Off Re-Entry Signal Parameter Audit

- Scope: first-layer signal parameter audit only.
- Architecture locked: `Formal Portfolio = Core + ConstAddOn[1.00x] + RangeRotation`.
- Semantics locked: full-stack cash-like Risk-Off; when Risk-Off is active, `Core + Sleeve #1 + Sleeve #2` all flatten.
- This audit isolates three dimensions rather than moving sell-side and re-entry together.

## Formal Baseline

- Return `1591.16%`
- Calmar `1.008`
- MaxDD `-57.08%`

## Default Ranking By Family

### h4_length

| Name | Return% | Calmar | MaxDD% | Worst3m | Worst6m | AvgTotalExp% | RiskOffActive% | dReturn vs Formal | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H4RSI14_10_EMA220 | 2799.57 | 1.487 | -48.26 | -24.38 | -31.81 | 97.49 | 39.18 | +1208.41pp | +0.479 | +8.82pp |
| H4RSI18_10_EMA220 | 2181.57 | 1.298 | -50.28 | -24.38 | -38.23 | 95.85 | 40.82 | +590.41pp | +0.291 | +6.80pp |
| H4RSI10_10_EMA220 | 3232.05 | 1.225 | -61.77 | -42.02 | -55.29 | 103.79 | 32.88 | +1640.89pp | +0.217 | -4.68pp |

- Winner: `H4RSI14_10_EMA220`

### h4_threshold

| Name | Return% | Calmar | MaxDD% | Worst3m | Worst6m | AvgTotalExp% | RiskOffActive% | dReturn vs Formal | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H4RSI14_10_EMA220 | 2799.57 | 1.487 | -48.26 | -24.38 | -31.81 | 97.49 | 39.18 | +1208.41pp | +0.479 | +8.82pp |
| H4RSI14_8_EMA220 | 2181.57 | 1.298 | -50.28 | -24.38 | -38.23 | 95.85 | 40.82 | +590.41pp | +0.291 | +6.80pp |
| H4RSI14_6_EMA220 | 2181.57 | 1.298 | -50.28 | -24.38 | -38.23 | 95.85 | 40.82 | +590.41pp | +0.291 | +6.80pp |
| H4RSI14_12_EMA220 | 3366.33 | 1.286 | -59.69 | -42.22 | -52.26 | 102.86 | 33.81 | +1775.17pp | +0.278 | -2.61pp |

- Winner: `H4RSI14_10_EMA220`

### sell_ema_h4_10

| Name | Return% | Calmar | MaxDD% | Worst3m | Worst6m | AvgTotalExp% | RiskOffActive% | dReturn vs Formal | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H4RSI14_10_EMA200 | 2772.70 | 1.699 | -42.08 | -19.10 | -24.76 | 98.11 | 39.35 | +1181.54pp | +0.692 | +15.00pp |
| H4RSI14_10_EMA250 | 2746.30 | 1.658 | -42.97 | -16.67 | -23.36 | 96.42 | 39.04 | +1155.14pp | +0.651 | +14.12pp |
| H4RSI14_10_EMA220 | 2799.57 | 1.487 | -48.26 | -24.38 | -31.81 | 97.49 | 39.18 | +1208.41pp | +0.479 | +8.82pp |
| H4RSI14_10_EMA120 | 1466.99 | 1.158 | -48.02 | -20.50 | -31.57 | 92.37 | 40.54 | -124.17pp | +0.150 | +9.06pp |

- Winner: `H4RSI14_10_EMA200`

### sell_ema_weekly30

| Name | Return% | Calmar | MaxDD% | Worst3m | Worst6m | AvgTotalExp% | RiskOffActive% | dReturn vs Formal | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WRSI14_30_EMA250 | 2505.61 | 1.933 | -35.60 | -14.70 | -19.89 | 95.90 | 39.56 | +914.45pp | +0.926 | +21.48pp |
| WRSI14_30_EMA200 | 2550.46 | 1.887 | -36.72 | -14.23 | -24.16 | 97.54 | 39.91 | +959.30pp | +0.880 | +20.36pp |
| WRSI14_30_EMA220 | 2722.96 | 1.747 | -40.66 | -15.26 | -27.29 | 96.94 | 39.73 | +1131.80pp | +0.739 | +16.42pp |
| WRSI14_30_EMA120 | 1497.41 | 1.324 | -42.34 | -20.39 | -21.54 | 92.82 | 40.09 | -93.76pp | +0.317 | +14.74pp |

- Winner: `WRSI14_30_EMA250`

### weekly_length

| Name | Return% | Calmar | MaxDD% | Worst3m | Worst6m | AvgTotalExp% | RiskOffActive% | dReturn vs Formal | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WRSI14_30_EMA220 | 2722.96 | 1.747 | -40.66 | -15.26 | -27.29 | 96.94 | 39.73 | +1131.80pp | +0.739 | +16.42pp |
| WRSI18_30_EMA220 | 2169.79 | 1.296 | -50.28 | -24.38 | -38.23 | 94.45 | 42.22 | +578.63pp | +0.288 | +6.80pp |
| WRSI10_30_EMA220 | 2372.44 | 1.195 | -56.44 | -37.39 | -46.95 | 101.39 | 35.29 | +781.28pp | +0.187 | +0.64pp |

- Winner: `WRSI14_30_EMA220`

### weekly_threshold

| Name | Return% | Calmar | MaxDD% | Worst3m | Worst6m | AvgTotalExp% | RiskOffActive% | dReturn vs Formal | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WRSI14_30_EMA220 | 2722.96 | 1.747 | -40.66 | -15.26 | -27.29 | 96.94 | 39.73 | +1131.80pp | +0.739 | +16.42pp |
| WRSI14_25_EMA220 | 2169.79 | 1.296 | -50.28 | -24.38 | -38.23 | 94.45 | 42.22 | +578.63pp | +0.288 | +6.80pp |
| WRSI14_20_EMA220 | 2169.79 | 1.296 | -50.28 | -24.38 | -38.23 | 94.45 | 42.22 | +578.63pp | +0.288 | +6.80pp |
| WRSI14_35_EMA220 | 2218.16 | 1.245 | -52.76 | -33.47 | -39.43 | 103.56 | 33.12 | +627.00pp | +0.238 | +4.32pp |

- Winner: `WRSI14_30_EMA220`

## Stress Check On Family Winners

| Winner | Stress dReturn vs Formal | Stress dCalmar vs Formal | Stress dMaxDD vs Formal |
| --- | --- | --- | --- |
| H4RSI14_10_EMA220 | +1354.81pp | +0.518 | +9.11pp |
| H4RSI14_10_EMA220 | +1354.81pp | +0.518 | +9.11pp |
| H4RSI14_10_EMA200 | +1321.16pp | +0.742 | +15.38pp |
| WRSI14_30_EMA250 | +1048.64pp | +0.964 | +21.36pp |
| WRSI14_30_EMA220 | +1254.84pp | +0.778 | +16.55pp |
| WRSI14_30_EMA220 | +1254.84pp | +0.778 | +16.55pp |

## Conclusion

- Weekly threshold winner: `WRSI14_30_EMA220`
- Weekly length winner: `WRSI14_30_EMA220`
- 4h threshold winner: `H4RSI14_10_EMA220`
- 4h length winner: `H4RSI14_10_EMA220`
- Sell-side EMA winner with Weekly30 re-entry fixed: `WRSI14_30_EMA250`
- Sell-side EMA winner with 4H10 re-entry fixed: `H4RSI14_10_EMA200`

- Parameter interpretation should stay layered:
  - first judge re-entry threshold and period
  - then judge sell-side EMA separately with re-entry fixed
  - do not cross-search these dimensions together