# SQUEEZE20 Positioning Report

## Conclusion

- Final judgment: Better Defined As High-Quality Overlay (Path B)
- Current research_optimal: `lb20_stop3.2_trail5.0_beoff`
- Why: The line keeps strong risk-adjusted behavior and healthier drawdown structure, but the allowed neighborhood only offers incremental absolute-return improvement. That is not enough to materially change the gap to BTC buy-and-hold.
- Continue pushing toward independent main strategy: False
- Recommended framing now: high-quality trend overlay

## Neighborhood Summary

| Variant | Return% | CAGR% | Sharpe | Calmar | MaxDD% | PF | Trades | dRet | dCAGR | dSharpe | dCalmar | dMaxDD | BH gap shrinks? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lb20_stop3.1_trail5.0_beoff | 472.78 | 32.37 | 0.935 | 0.939 | -34.49 | 1.955 | 56 | +2.27 | +0.08 | +0.002 | +0.002 | +0.00 | yes |
| lb20_stop3.2_trail5.0_beoff | 470.51 | 32.28 | 0.933 | 0.936 | -34.49 | 1.947 | 56 | +0.00 | +0.00 | +0.000 | +0.000 | +0.00 | no |
| lb20_stop3.3_trail5.0_beoff | 466.55 | 32.14 | 0.930 | 0.932 | -34.49 | 1.938 | 56 | -3.96 | -0.15 | -0.003 | -0.004 | +0.00 | no |
| lb21_stop3.1_trail5.0_beoff | 458.74 | 31.84 | 0.927 | 0.923 | -34.49 | 1.922 | 56 | -11.77 | -0.44 | -0.006 | -0.013 | +0.00 | no |
| lb21_stop3.2_trail5.0_beoff | 456.52 | 31.76 | 0.925 | 0.921 | -34.49 | 1.915 | 56 | -13.99 | -0.53 | -0.008 | -0.015 | -0.00 | no |
| lb21_stop3.3_trail5.0_beoff | 452.66 | 31.61 | 0.922 | 0.917 | -34.49 | 1.906 | 56 | -17.85 | -0.67 | -0.012 | -0.020 | +0.00 | no |
| lb22_stop3.1_trail5.0_beoff | 449.60 | 31.49 | 0.920 | 0.913 | -34.49 | 1.907 | 56 | -20.91 | -0.79 | -0.014 | -0.023 | +0.00 | no |
| lb22_stop3.2_trail5.0_beoff | 447.42 | 31.41 | 0.918 | 0.911 | -34.49 | 1.900 | 56 | -23.09 | -0.88 | -0.016 | -0.025 | +0.00 | no |

## Buy-And-Hold Positioning

- Base vs B&H return gap: -385.65pp
- Base vs B&H CAGR gap: -11.44pp
- Best raw challenger vs B&H return gap change: +2.27pp
- Best raw challenger vs B&H CAGR gap change: +0.08pp
- Best raw challenger keeps risk-adjusted edge vs B&H: True

## Gate Stability Check

- Base non-baseline gate summary: {"baseline_gate": false, "yearly": true, "rolling_oos": true, "regime": true, "cost_stress": true, "slippage_stress": true, "execution_mode_stress": true, "intrabar_path_stress": true, "live_safety_check": true}
- `lb20_stop3.1_trail5.0_beoff` full-size gate summary: {"baseline_gate": false, "yearly": true, "rolling_oos": true, "regime": true, "cost_stress": true, "slippage_stress": true, "execution_mode_stress": true, "intrabar_path_stress": true, "live_safety_check": true}
- `lb20_stop3.1_trail5.0_beoff` 35% gate summary: {"baseline_gate": false, "yearly": true, "rolling_oos": true, "regime": true, "cost_stress": true, "slippage_stress": true, "execution_mode_stress": true, "intrabar_path_stress": true, "live_safety_check": true}
- `lb20_stop3.3_trail5.0_beoff` full-size gate summary: {"baseline_gate": false, "yearly": true, "rolling_oos": true, "regime": true, "cost_stress": true, "slippage_stress": true, "execution_mode_stress": true, "intrabar_path_stress": true, "live_safety_check": true}

## Recommendation

- Main call: Formally treat the line as a high-quality overlay unless a later local improvement materially shrinks the BTC buy-and-hold gap.
- Next step: Stop treating marginal local improvements as evidence of imminent main-strategy status; future work should only continue if it can materially reduce the BTC buy-and-hold gap without degrading the current risk structure.
- Break-even side check: not tested; no raw candidate cleared the evidence threshold for a restrained break-even side check