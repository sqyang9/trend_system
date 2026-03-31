# Exposure Engine E2 Dynamic Schedule Audit

## Final Judgment

- Best dynamic candidate: `Core+DynamicExposure[trend_90dma_2state]`
- Stage conclusion: 1.00x constant sleeve remains the efficient frontier

## Dynamic Candidate Table

| Candidate | Family | TotalReturn | MaxDD | Calmar | Ulcer | dRet vs Const1x | dMaxDD vs Const1x | ReturnRetention | Exp delta vs Const1x | WF strict | Driver |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Core+DynamicExposure[portfolio_dd_2state] | portfolio drawdown / recovery state | 1172.38% | -66.32% | 0.761 | 32.07 | -158.62pp | -2.62pp | 88.08% | -3.58pp | 0.33 | mostly exposure suppression |
| Core+DynamicExposure[portfolio_dd_3state] | portfolio drawdown / recovery state | 1066.16% | -67.60% | 0.716 | 33.13 | -264.83pp | -3.90pp | 80.10% | -7.34pp | 0.67 | mostly exposure suppression |
| Core+DynamicExposure[trend_90dma_2state] | simple BTC trend background | 1240.93% | -64.76% | 0.799 | 31.40 | -90.06pp | -1.07pp | 93.23% | -1.77pp | 0.00 | mostly exposure suppression |
| Core+DynamicExposure[addon_quality_90d_2state] | recent AddOn contribution quality | 1202.11% | -64.88% | 0.787 | 31.38 | -128.88pp | -1.19pp | 90.32% | -3.26pp | 0.00 | mostly exposure suppression |

## Best Candidate Audit

- Family: simple BTC trend background
- Rule: {'type': 'trend_90dma_2state', 'full_weight': 1.0, 'reduced_weight': 0.75}
- State mix: {'full': 75.0, 'trend_reduced': 25.0}
- dReturn vs Const1x: -90.06pp
- dMaxDD vs Const1x: -1.07pp
- dCalmar vs Const1x: -0.038
- Return retention vs Const1x: 93.23%
- Avg exposure delta vs Const1x: -1.77pp
- Stress delta vs same scheme: Return +4.60pp, MaxDD +0.22pp

## Reference Set

- CoreOnly TotalReturn / MaxDD: 860.94% / -77.04%
- Core+BinaryAddOn TotalReturn / MaxDD: 965.43% / -72.63%
- Core+ConstAddOn[1.00x] TotalReturn / MaxDD: 1330.99% / -63.70%

## Direct Answer

Can any dynamic schedule truly improve on the 1.00x constant sleeve, or is constant full deployment already the efficient frontier? No. Best dynamic candidate Core+DynamicExposure[trend_90dma_2state] still fails to clear the 1.00x constant sleeve on the full decision bar. It delivers dReturn -90.06pp and dMaxDD -1.07pp versus Core+ConstAddOn[1.00x], so constant full deployment remains the efficient frontier for now.