# Portfolio Circuit Breaker Screen

- Scope: system-level crash-defense screen via existing sleeve `daily_loss_limit + cooldown` engine hooks.
- This is still independent research. Mainline not changed.
- Goal: see whether W06-style stop penetration is better handled by sleeve breaker logic than by small ATR-stop tweaks.

## Default Summary

| Candidate | Return% | Calmar | MaxDD% | W06 Return% | W06 MaxDD% | W06 AvgExp | W06 AvgS2Exp | W06 DD/Exp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline | 2893.89 | 2.854 | -25.46 | -7.21 | -23.13 | 0.47 | 0.05 | -49.5% |
| S2-only DLL 1.0% / CD6 | 2893.89 | 2.854 | -25.46 | -7.21 | -23.13 | 0.47 | 0.05 | -49.5% |
| All sleeves DLL 1.0% / CD6 | 2893.89 | 2.854 | -25.46 | -7.21 | -23.13 | 0.47 | 0.05 | -49.5% |
| All sleeves DLL 1.0% / CD9 | 2893.89 | 2.854 | -25.46 | -7.21 | -23.13 | 0.47 | 0.05 | -49.5% |

## Readout

- Baseline W06: MaxDD `-23.13%`, AvgExp `0.47`, DD/Exp `-49.5%`.
- Best W06 candidate in this screen: `Baseline` with MaxDD `-23.13%`, DD/Exp `-49.5%`.
- This first-pass screen is intentionally default-only and W06-centric; if one candidate shows real edge, then it is worth expanding to stress / harsh.