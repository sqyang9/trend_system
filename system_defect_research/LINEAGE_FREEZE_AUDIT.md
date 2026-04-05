# Lineage Freeze Audit

## Scope

- Mainline not changed.
- This audit decomposes the full promotion lineage into layered frozen checkpoints:
  - `EMA250 + close3`
  - `+ HC strict breakout4`
  - `+ HV85 force`
  - `+ ATRVT`
  - final `combo = HV85 + ATRVT`
- Goal: judge whether the later added layers still look sensible once validation is pushed into later windows.

## Static Freeze Splits

| Split | Selected By Train | Close3 Calmar | Hybrid Calmar | Combo Calmar | Combo dCalmar vs Hybrid |
| --- | --- | --- | --- | --- | --- |
| fit_W01_W06_validate_W07_W13 | Stage 4: + ATRVT on sleeves | 1.595 | 1.625 | 1.624 | -0.000 |
| fit_W01_W09_validate_W10_W13 | Stage 4: + ATRVT on sleeves | 0.902 | 0.913 | 1.041 | +0.128 |

## Validation Deltas Vs Immediate Prior Stage

| Split | Change | dReturn | dCalmar | dMaxDD |
| --- | --- | --- | --- | --- |
| fit_W01_W06_validate_W07_W13 | close3_to_hybrid | -25.92pp | +0.030 | +2.84pp |
| fit_W01_W06_validate_W07_W13 | hybrid_to_hv85 | -7.15pp | -0.048 | -0.00pp |
| fit_W01_W06_validate_W07_W13 | hybrid_to_atrvt | +2.92pp | +0.046 | +0.36pp |
| fit_W01_W06_validate_W07_W13 | hybrid_to_combo | -3.90pp | -0.000 | +0.37pp |
| fit_W01_W09_validate_W10_W13 | close3_to_hybrid | -0.94pp | +0.011 | +0.81pp |
| fit_W01_W09_validate_W10_W13 | hybrid_to_hv85 | -0.53pp | -0.007 | +0.11pp |
| fit_W01_W09_validate_W10_W13 | hybrid_to_atrvt | +4.11pp | +0.132 | +0.89pp |
| fit_W01_W09_validate_W10_W13 | hybrid_to_combo | +3.69pp | +0.128 | +1.01pp |

## Readout

- `W01-W06 -> W07-W13`: training still prefers `hybrid_atrvt`, while combo validates at `Calmar 1.624` versus hybrid `Calmar 1.625`.
- `W01-W09 -> W10-W13`: combo validates at `Calmar 1.041` versus hybrid `Calmar 0.913`.
- This directly tests whether the late layers (`HV85`, `ATRVT`) add or subtract once the earlier lineage is frozen.

## Verdict

- If combo stays close to or above hybrid on the later windows, the late-stage promotion looks credible rather than purely in-sample.
- If combo loses materially to hybrid or close3 after freezing, then the late-stage overlay additions should be treated as more fragile than the earlier lineage.