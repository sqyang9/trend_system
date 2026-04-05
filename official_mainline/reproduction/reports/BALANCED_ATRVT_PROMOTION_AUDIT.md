# Balanced ATRVT Promotion Audit

## Scope

- Mainline not changed.
- This audit focuses on balanced ATRVT candidates, not the economics-only `H45/H60` tail.
- Goal: find a promotion-grade contract with better robustness and still meaningful default gains.

## Default / Stress / Harsh

| Candidate | Scenario | Return% | Calmar | MaxDD% | W06 DD/Exp | W11 AvgExp |
| --- | --- | --- | --- | --- | --- | --- |
| 180d med / 0.35-1.50 both | default | 2946.79 | 2.574 | -28.41 | -46.9% | 1.016 |
| 180d med / 0.35-1.50 both | stress | 3065.20 | 2.631 | -28.20 | -46.3% | 1.018 |
| 180d med / 0.35-1.50 both | harsh_friction | 2767.68 | 2.407 | -29.69 | -47.9% | 1.018 |
| 90d med / 0.35-1.50 both | default | 3114.74 | 2.762 | -27.02 | -44.0% | 0.980 |
| 90d med / 0.35-1.50 both | stress | 3233.12 | 2.820 | -26.83 | -43.5% | 0.982 |
| 90d med / 0.35-1.50 both | harsh_friction | 2913.41 | 2.579 | -28.24 | -45.1% | 0.982 |
| 90d med / 0.35-1.25 both | default | 3078.77 | 2.926 | -25.40 | -45.0% | 0.964 |
| 90d med / 0.35-1.25 both | stress | 3197.15 | 2.990 | -25.20 | -44.5% | 0.965 |
| 90d med / 0.35-1.25 both | harsh_friction | 2888.05 | 2.733 | -26.56 | -46.1% | 0.965 |
| S1 180d / S2 60d | default | 3119.82 | 2.716 | -27.50 | -44.3% | 1.001 |
| S1 180d / S2 60d | stress | 3238.21 | 2.773 | -27.30 | -43.8% | 1.003 |
| S1 180d / S2 60d | harsh_friction | 2914.99 | 2.535 | -28.74 | -45.5% | 1.003 |
| S1 90d / S2 60d | default | 3196.79 | 2.873 | -26.23 | -42.7% | 0.978 |
| S1 90d / S2 60d | stress | 3315.15 | 2.932 | -26.04 | -42.3% | 0.980 |
| S1 90d / S2 60d | harsh_friction | 2984.06 | 2.680 | -27.42 | -43.9% | 0.980 |

## Annual Starts Vs Corrected 180d Baseline

- `S1 90d / S2 60d`: Return better `5/7`, Calmar better `6/7`, MaxDD better `7/7`.
- `S1 180d / S2 60d`: Return better `5/7`, Calmar better `7/7`, MaxDD better `7/7`.

## Freeze-Date Validation

| Candidate | Split | Validate Return% | Validate Calmar | Validate MaxDD% |
| --- | --- | --- | --- | --- |
| 180d med / 0.35-1.50 both | fit_W01_W06_validate_W07_W13 | 190.80 | 1.739 | -22.58 |
| 180d med / 0.35-1.50 both | fit_W01_W09_validate_W10_W13 | 43.98 | 1.062 | -22.19 |
| 90d med / 0.35-1.50 both | fit_W01_W06_validate_W07_W13 | 179.63 | 1.665 | -22.56 |
| 90d med / 0.35-1.50 both | fit_W01_W09_validate_W10_W13 | 44.23 | 1.125 | -21.05 |
| 90d med / 0.35-1.25 both | fit_W01_W06_validate_W07_W13 | 177.64 | 1.660 | -22.45 |
| 90d med / 0.35-1.25 both | fit_W01_W09_validate_W10_W13 | 43.36 | 1.095 | -21.22 |
| S1 180d / S2 60d | fit_W01_W06_validate_W07_W13 | 181.07 | 1.758 | -21.49 |
| S1 180d / S2 60d | fit_W01_W09_validate_W10_W13 | 45.09 | 1.144 | -21.07 |
| S1 90d / S2 60d | fit_W01_W06_validate_W07_W13 | 174.12 | 1.661 | -22.11 |
| S1 90d / S2 60d | fit_W01_W09_validate_W10_W13 | 44.70 | 1.159 | -20.62 |

## Decision Readout

- Corrected baseline `180d`: `Return 2946.79% / Calmar 2.574 / MaxDD -28.41%`.
- Balanced candidate `S1 90d / S2 60d`: `Return 3196.79% / Calmar 2.873 / MaxDD -26.23%`.
- Robust candidate `S1 180d / S2 60d`: `Return 3119.82% / Calmar 2.716 / MaxDD -27.50%`.
- Reference sibling `H90`: `Return 3114.74% / Calmar 2.762 / MaxDD -27.02%`.
- Reference sibling `H90 0.35-1.25`: `Return 3078.77% / Calmar 2.926 / MaxDD -25.40%`.

## Verdict

- `S1 90d / S2 60d` is the best balanced candidate in this set: it keeps a large part of the H60 economics, improves W06 and W11 exposure, and still beats the corrected `180d` baseline on freeze-date average.
- `S1 180d / S2 60d` is the most robustness-first contract, but its default upside is too modest relative to `S1 90d / S2 60d`.
- Promotion verdict for `S1 90d / S2 60d`: `GO_TO_LANDING_AUDIT`.
- Implementation note: if promoted, keep `atrvt_s1_ref_days` and `atrvt_s2_ref_days` explicit in the shared contract so the tuning surface remains small and governed.
