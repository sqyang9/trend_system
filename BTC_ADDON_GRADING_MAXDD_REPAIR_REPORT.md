# BTC AddOn Grading MaxDD Repair Report

## Final Judgment

- Repair answer: NO. No repaired grading candidate clears promotion-candidate validation.
- Best repair candidate: Core+AdjustedGradedAddOn[repair_strong048]
- Baseline decision: Keep baseline unchanged
- Extension-line decision: Keep AddOn grading as active extension line

## Baseline Alignment

- Binary AddOn drift vs committed artifact: Return +4.71pp, Sharpe +0.001, Calmar +0.001, MaxDD improve -0.02pp
- Original graded drift vs committed promotion result: Return +0.00pp, Sharpe +0.000, Calmar +0.000, MaxDD improve +0.00pp

## Candidate Table

| Candidate | dRet vs Binary | dSharpe | dCalmar | dMaxDD | WF strict | WF dRet | WF dSharpe | WF dCalmar | WF dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core+AdjustedGradedAddOn[repair_strong045] | +4.71 | -0.002 | -0.006 | -0.83 | 0.67 | +4.15 | +0.028 | +0.165 | +0.33 |
| Core+AdjustedGradedAddOn[repair_strong048] | +10.50 | -0.000 | -0.003 | -0.76 | 0.67 | +4.37 | +0.032 | +0.187 | +0.46 |
| Core+AdjustedGradedAddOn[repair_top30] | +13.88 | +0.001 | -0.002 | -0.69 | 0.33 | +2.67 | +0.020 | +0.127 | +0.41 |
| Core+AdjustedGradedAddOn[repair_top30_strong045] | +4.38 | -0.002 | -0.006 | -0.81 | 0.67 | +2.91 | +0.018 | +0.114 | +0.24 |
| Core+AdjustedGradedAddOn[repair_breakout110] | -3.86 | -0.003 | -0.006 | -0.54 | 0.33 | +2.37 | +0.012 | +0.054 | +0.04 |
| Core+AdjustedGradedAddOn[repair_breakout110_strong048] | -5.20 | -0.004 | -0.007 | -0.61 | 0.33 | +2.51 | +0.012 | +0.059 | +0.02 |

## Best Candidate Time-Slice Diagnostics

| Slice | dReturn | dSharpe | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- |
| bull_expansion | +10.02pp | -0.003 | +0.018 | -0.24pp |
| major_drawdown | -0.76pp | +0.006 | -0.001 | -0.76pp |
| recovery_phase | +14.93pp | +0.031 | +0.271 | -0.44pp |
| sideways_volatility | +0.59pp | +0.005 | +0.006 | +0.26pp |

## Best Candidate Exposure Diagnostics

- Avg total exposure delta vs binary: +0.60pp
- AddOn activation ratio: binary 25.1% vs candidate 25.1%
- Avg AddOn size when active: binary 0.350 vs candidate 0.374
- Accidental leverage flag: no

## Execution Stress

- Stress delta on best repair candidate: Return +0.33pp, Sharpe +0.000, Calmar +0.000, MaxDD improve +0.04pp

## Direct Answers

- Core+AdjustedGradedAddOn[repair_strong048] does not outperform the binary AddOn baseline strongly enough after the narrow MaxDD repair pass.
- OOS stability remains strong: strict win ratio 0.67, avg dReturn +4.37pp, avg dSharpe +0.032, avg dCalmar +0.187.
- No. MaxDD degradation remains; best full-sample dMaxDD is -0.76pp.
- No. The repaired candidate still cannot become a promotion candidate.
- No. Baseline should stay unchanged while AddOn grading remains the active extension line.