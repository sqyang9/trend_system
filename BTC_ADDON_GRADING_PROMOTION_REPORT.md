# BTC AddOn Grading Promotion Report

## Final Judgment

- Promotion candidate answer: NO. Compression-breakout grading does not yet clear promotion-candidate validation.
- Preferred structure: Core+GradedAddOn[compression_breakout]
- Baseline decision: Keep baseline unchanged
- Active extension line decision: Keep AddOn grading as the active extension line

## Baseline Alignment

- Default tuple: next_bar_open + legacy_bar_extrema + midpoint + full_model
- Baseline drift vs committed artifact: Return +4.71pp, Sharpe +0.001, Calmar +0.001, MaxDD improve -0.02pp

## Full-Sample Comparison

| System | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Exposure% | dRet vs Binary | dSharpe | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BTC_BuyAndHold | 860.94 | 43.84 | 0.751 | 0.569 | -77.04 | 100.0 | -104.48 | -0.041 | -0.068 | -4.41 |
| Core+BinaryAddOn | 965.43 | 46.24 | 0.792 | 0.637 | -72.63 | 108.8 | +0.00 | +0.000 | +0.000 | +0.00 |
| Core+GradedAddOn[compression_breakout] | 979.83 | 46.56 | 0.793 | 0.635 | -73.35 | 109.6 | +14.41 | +0.001 | -0.002 | -0.72 |

## Walk-Forward OOS

- Strict win ratio: 1.00
- Avg delta Return: +4.52pp
- Avg delta Sharpe: +0.035
- Avg delta Calmar: +0.202

| Test Window | dReturn | dSharpe | dCalmar | dMaxDD | Strict Win |
| --- | --- | --- | --- | --- | --- |
| 2023-01-01 -> 2024-01-01 | +7.54pp | +0.045 | +0.358 | -0.13pp | yes |
| 2024-01-01 -> 2025-01-01 | +4.72pp | +0.043 | +0.212 | +0.48pp | yes |
| 2025-01-01 -> 2026-01-01 | +1.29pp | +0.017 | +0.037 | +1.28pp | yes |

## Time-Slice Diagnostics

| Slice | dReturn | dSharpe | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- |
| bull_expansion | +11.15pp | -0.002 | +0.030 | -0.20pp |
| major_drawdown | -0.71pp | +0.005 | -0.001 | -0.72pp |
| recovery_phase | +15.15pp | +0.034 | +0.285 | -0.43pp |
| sideways_volatility | +0.63pp | +0.005 | +0.007 | +0.36pp |

## Exposure Diagnostics

- Avg total exposure delta: +0.81pp
- AddOn activation ratio: baseline 25.1% vs candidate 25.1%
- Avg AddOn size when active: baseline 0.350 vs candidate 0.382
- Trend participation ratio: 1.092
- Accidental leverage flag: no

## Execution Stress

- Stress delta vs default on graded candidate: Return +0.31pp, Sharpe +0.000, Calmar +0.000, MaxDD improve +0.04pp
- Stress ranking stable: yes

## Direct Answers

- On the rebuilt comparison framework, compression-breakout grading does not formally outperform the binary AddOn baseline strongly enough for promotion.
- OOS stability is good: strict win ratio 1.00, avg dReturn +4.52pp, avg dSharpe +0.035, avg dCalmar +0.202.
- The improvement comes from better trend capture with modest size redistribution, not accidental leverage. Average total exposure only moves by +0.81pp and activation frequency stays unchanged at 25.1%.
- No. It cannot be considered a promotion candidate yet because max drawdown still degrades slightly versus the binary baseline.
- Yes. AddOn grading should remain the active extension line, with compression-breakout kept as the lead candidate.
- Yes. Baseline should remain unchanged until a graded sleeve clears promotion criteria without max-drawdown degradation or execution fragility.