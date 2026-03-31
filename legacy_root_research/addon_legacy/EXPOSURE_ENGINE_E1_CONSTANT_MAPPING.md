# Exposure Engine E1 Constant Mapping

## Final Judgment

- Best constant AddOn baseline: `Core+ConstAddOn[1.00x]`
- Binary AddOn positioning: too low
- Dynamic promotion reference: `Core+ConstAddOn[1.00x]`

## Full-Sample Constant Mapping

| Candidate | TotalReturn | CAGR | MaxDD | Calmar | Ulcer | Underwater | RecoveryDays | AvgExposure | dRet vs Binary | dMaxDD vs Binary | WF strict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CoreOnly | 860.94% | 43.84% | -77.04% | 0.569 | 37.80 | 98.1% | 473.0 | 100.00% | -104.48pp | -4.41pp | 0.33 |
| Core+ConstAddOn[0.25x] | 929.88% | 45.45% | -73.96% | 0.615 | 36.11 | 98.1% | 469.0 | 106.28% | -35.54pp | -1.32pp | 0.33 |
| Core+BinaryAddOn | 965.43% | 46.24% | -72.63% | 0.637 | 35.38 | 98.2% | 468.8 | 108.79% | +0.00pp | +0.00pp | 0.00 |
| Core+ConstAddOn[0.50x] | 1028.34% | 47.60% | -70.59% | 0.674 | 34.22 | 98.2% | 468.3 | 112.56% | +62.92pp | +2.05pp | 0.33 |
| Core+ConstAddOn[0.75x] | 1161.09% | 50.26% | -67.11% | 0.749 | 32.22 | 98.3% | 463.8 | 118.84% | +195.66pp | +5.52pp | 0.33 |
| Core+ConstAddOn[1.00x] | 1330.99% | 53.34% | -63.70% | 0.837 | 30.33 | 98.3% | 462.3 | 125.12% | +365.57pp | +8.94pp | 0.33 |

## Archived Repair Reference

- Archived repaired grading line: `Core+CompoundRepair[close30_gate_to_base]`
- TotalReturn: 987.22%
- MaxDD: -73.13%
- Calmar: 0.639

## Best Constant Audit

- Best constant TotalReturn: 1330.99%
- Best constant MaxDD: -63.70%
- Best constant Calmar: 0.837
- Best constant UlcerIndex: 30.33
- Best constant dReturn vs Binary: +365.57pp
- Best constant dMaxDD vs Binary: +8.94pp
- Best constant stress delta: Return +5.21pp, MaxDD +0.21pp

## Direct Answers

1. What is the best constant AddOn exposure baseline? Core+ConstAddOn[1.00x], with TotalReturn 1330.99%, MaxDD -63.70%, Calmar 0.837.
2. Is the current Binary AddOn exposure too low, too high, or near-optimal at the portfolio level? too low.
3. Does any constant exposure candidate dominate on both return and drawdown relative to Core+BinaryAddOn? Yes. Core+ConstAddOn[1.00x] improves both TotalReturn (+365.57pp) and MaxDD (+8.94pp) versus Core+BinaryAddOn.
4. What constant exposure baseline should all future dynamic candidates be required to beat? Core+ConstAddOn[1.00x].