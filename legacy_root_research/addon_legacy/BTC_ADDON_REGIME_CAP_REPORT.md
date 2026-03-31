# BTC AddOn Regime Cap Report

## Final Judgment

- Regime-cap answer: NO. Regime-capped graded AddOn does not yet clear promotion-candidate validation.
- Best regime-cap candidate: Core+RegimeCappedAddOn[cap_soft]
- Baseline decision: Keep baseline unchanged
- Extension-line decision: Yes. AddOn grading should keep moving toward an exposure-engine style extension line.

## Baseline Alignment

- Binary AddOn drift vs committed artifact: Return +4.71pp, Sharpe +0.001, Calmar +0.001, MaxDD improve -0.02pp
- Graded AddOn drift vs committed promotion result: Return +0.00pp, Sharpe +0.000, Calmar +0.000, MaxDD improve +0.00pp

## Full-Sample Comparison

| Structure | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Exposure% | dRet vs Binary | dSharpe | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core+BinaryAddOn | 965.43 | 46.24 | 0.792 | 0.637 | -72.63 | 108.8 | +0.00 | +0.000 | +0.000 | +0.00 |
| Core+GradedAddOn[compression_breakout] | 979.83 | 46.56 | 0.793 | 0.635 | -73.35 | 109.6 | +14.41 | +0.001 | -0.002 | -0.72 |
| Core+RegimeCappedAddOn[cap_soft] | 953.08 | 45.97 | 0.785 | 0.622 | -73.88 | 108.6 | -12.34 | -0.007 | -0.014 | -1.24 |

## Candidate Table

| Candidate | dRet vs Binary | dSharpe | dCalmar | dMaxDD | WF strict | WF dRet | WF dSharpe | WF dCalmar | WF dMaxDD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core+RegimeCappedAddOn[cap_soft] | -12.34 | -0.007 | -0.014 | -1.24 | 0.33 | +4.35 | +0.019 | +0.123 | -0.20 |
| Core+RegimeCappedAddOn[cap_base] | -24.71 | -0.011 | -0.020 | -1.50 | 0.00 | +4.33 | +0.011 | +0.086 | -0.58 |
| Core+RegimeCappedAddOn[cap_defensive] | -36.44 | -0.015 | -0.026 | -1.76 | 0.00 | +4.34 | +0.004 | +0.051 | -0.96 |

## Time-Slice Diagnostics

| Slice | dReturn | dSharpe | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- |
| bull_expansion | +2.51pp | -0.010 | -0.056 | -0.54pp |
| major_drawdown | -1.24pp | +0.009 | -0.002 | -1.25pp |
| recovery_phase | +17.17pp | +0.012 | +0.095 | -0.87pp |
| sideways_volatility | +0.34pp | +0.005 | +0.004 | -0.31pp |

## Exposure Diagnostics

- Avg total exposure vs binary: -0.15pp
- AddOn activation ratio: binary 25.1% / graded 25.1% / capped 25.1%
- Avg AddOn size when active: graded 0.382 / capped 0.344
- Trend participation ratio vs binary: 0.983
- Accidental leverage flag: no

## Execution Stress

- Stress delta on best capped candidate: Return +0.23pp, Sharpe +0.000, Calmar +0.000, MaxDD improve +0.03pp

## Direct Answers

- Core+RegimeCappedAddOn[cap_soft] does not outperform the binary AddOn baseline strongly enough on the full validation set.
- OOS stability is not preserved: strict win ratio 0.33, avg dReturn +4.35pp, avg dSharpe +0.019, avg dCalmar +0.123.
- The regime cap does not fully remove MaxDD degradation; best full-sample dMaxDD is -1.24pp.
- No. This structure still cannot be considered a promotion candidate.
- Yes. AddOn grading should move toward an exposure-engine design, but only through narrow modulation layers like this one, not by opening new strategy families.