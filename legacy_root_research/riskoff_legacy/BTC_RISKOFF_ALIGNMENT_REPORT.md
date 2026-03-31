# BTC Risk-Off Alignment Report

## Final Judgment

- This round is alignment validation, not new exploration.
- Main answer: YES. In the aligned default-tuple framework, AddOn + Risk-Off still beats AddOn-only for the locked narrow candidate set.
- Evidence level: aligned but preliminary
- Baseline promotion: NO. The module is now aligned, but this is still not enough to rewrite the locked working baseline.
- Preferred aligned candidate: Core+AddOnOverlay+RO_EMA220_FLAT

## Formal Implementation Path

- Overlay sleeve is imported from the locked, committed AddOnOverlay artifact under the default tuple.
- This round does not re-optimize or restage the overlay sleeve.
- Risk-Off core is rebuilt in a causal simulator: signal at 4h close t, execution at t+1 open by default, or at the first 5m close of t+1 for the conservative stress check.
- Core trades pay commission and slippage; there is no same-bar hindsight rebalance.

## Locked Risk-Off Candidates

- `RO_EMA200_FLAT`
- `RO_EMA220_FLAT`
- `RO_EMA200_TO35`

## Default-Tuple Aligned Results

| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Exposure% | dRet vs AddOn | dCAGR | dSharpe | dCalmar | dMaxDD improve |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B&H | 856.16 | 43.73 | 0.750 | 0.568 | -77.04 | 100.0 | -104.91 | -2.42 | -0.041 | -0.068 | -4.45 |
| Core+AddOnOverlay | 961.07 | 46.15 | 0.791 | 0.636 | -72.60 | 108.8 | +0.00 | +0.00 | +0.000 | +0.000 | +0.00 |
| Core+AddOnOverlay+RO_EMA200_FLAT | 1319.64 | 53.15 | 1.007 | 1.048 | -50.73 | 67.7 | +358.57 | +7.00 | +0.216 | +0.412 | +21.86 |
| Core+AddOnOverlay+RO_EMA220_FLAT | 1626.59 | 58.04 | 1.068 | 1.097 | -52.90 | 67.7 | +665.52 | +11.89 | +0.277 | +0.461 | +19.69 |
| Core+AddOnOverlay+RO_EMA200_TO35 | 1317.88 | 53.12 | 0.977 | 0.907 | -58.54 | 82.1 | +356.82 | +6.97 | +0.185 | +0.272 | +14.06 |

## Minimal Formal Validation

- Core+AddOnOverlay: yearly pass=False, positive_year_ratio=0.62, worst_year=-59.21%, rolling pass=False, avg_sharpe=0.173, positive_ratio=0.50
- Core+AddOnOverlay+RO_EMA200_FLAT: yearly pass=False, positive_year_ratio=0.62, worst_year=-41.53%, rolling pass=False, avg_sharpe=0.235, positive_ratio=0.50
- Core+AddOnOverlay+RO_EMA220_FLAT: yearly pass=False, positive_year_ratio=0.62, worst_year=-43.76%, rolling pass=False, avg_sharpe=0.306, positive_ratio=0.50
- Core+AddOnOverlay+RO_EMA200_TO35: yearly pass=False, positive_year_ratio=0.62, worst_year=-47.68%, rolling pass=False, avg_sharpe=0.117, positive_ratio=0.50

## Sensitivity

- Cost sensitivity, AddOn-only: Return +0.11pp, Sharpe +0.000, MaxDD improve +0.00pp
- Cost sensitivity, preferred Risk-Off: Return -329.95pp, Sharpe -0.065, MaxDD improve -1.68pp
- Execution sensitivity, AddOn-only: Return -0.48pp, Sharpe -0.000, MaxDD improve -0.02pp
- Execution sensitivity, preferred Risk-Off: Return +80.03pp, Sharpe +0.014, MaxDD improve -0.11pp

## Causality Audit

- Default-mode causality violations: 0
- Stress-mode causality violations: 0

## Exploratory Comparison

- Preferred candidate return delta vs exploratory: -270.20pp
- Preferred candidate maxdd delta vs exploratory: -1.39pp
- Interpretation: Small deltas mean the exploratory result was directionally reliable. Large negative deltas would mean the exploratory allocation simulation overstated the edge.

## Final Call

- Risk-Off remains supported after alignment and is worth continuing to validate, but the repository baseline should stay unchanged for now.
- Bear Short status: Not advanced in this round; remains outside the formal baseline decision.