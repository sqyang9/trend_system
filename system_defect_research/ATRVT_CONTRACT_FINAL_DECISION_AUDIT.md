# ATRVT Contract Final Decision Audit

## Scope

- Mainline not changed.
- This audit compares the three now-parameterized ATRVT contracts on the same shared implementation surface.
- Core structure is held fixed:
  - stable `close3`
  - high-churn `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces high-churn earlier

## Default / Stress / Harsh

| Candidate | Scenario | Return% | Calmar | MaxDD% | Worst6m | RecoveryDays | W06 DD/Exp | W11 AvgExp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current corrected baseline: 180d med / 0.35-1.50 both | default | 2946.79 | 2.574 | -28.41 | -16.25 | 19.0 | -46.9% | 1.016 |
| Current corrected baseline: 180d med / 0.35-1.50 both | stress | 3065.20 | 2.631 | -28.20 | -16.01 | 19.0 | -46.3% | 1.018 |
| Current corrected baseline: 180d med / 0.35-1.50 both | harsh_friction | 2767.68 | 2.407 | -29.69 | -17.02 | 19.3 | -47.9% | 1.018 |
| Balanced challenger: 90d med / 0.35-1.50 both | default | 3114.74 | 2.762 | -27.02 | -16.31 | 19.0 | -44.0% | 0.980 |
| Balanced challenger: 90d med / 0.35-1.50 both | stress | 3233.12 | 2.820 | -26.83 | -16.08 | 19.0 | -43.5% | 0.982 |
| Balanced challenger: 90d med / 0.35-1.50 both | harsh_friction | 2913.41 | 2.579 | -28.24 | -17.12 | 19.3 | -45.1% | 0.982 |
| Economics-first challenger: 60d med / 0.35-1.50 both | default | 3327.75 | 2.988 | -25.59 | -16.22 | 19.3 | -40.9% | 0.976 |
| Economics-first challenger: 60d med / 0.35-1.50 both | stress | 3446.07 | 3.047 | -25.40 | -16.01 | 19.2 | -40.4% | 0.978 |
| Economics-first challenger: 60d med / 0.35-1.50 both | harsh_friction | 3101.55 | 2.786 | -26.75 | -17.04 | 19.3 | -42.0% | 0.978 |

## Annual Starts Vs Corrected 180d Baseline

- `90d` vs `180d`: Return better `4/7`, Calmar better `6/7`, MaxDD better `7/7`.
- `60d` vs `180d`: Return better `4/7`, Calmar better `5/7`, MaxDD better `7/7`.

## Freeze-Date Walk-Forward

| Split | Candidate | Train Calmar | Validate Return% | Validate Calmar | Validate MaxDD% | Selected By Train |
| --- | --- | --- | --- | --- | --- | --- |
| fit_W01_W06_validate_W07_W13 | Current corrected baseline: 180d med / 0.35-1.50 both | 4.174 | 190.80 | 1.739 | -22.58 | no |
| fit_W01_W06_validate_W07_W13 | Balanced challenger: 90d med / 0.35-1.50 both | 4.643 | 179.63 | 1.665 | -22.56 | no |
| fit_W01_W06_validate_W07_W13 | Economics-first challenger: 60d med / 0.35-1.50 both | 5.244 | 166.26 | 1.587 | -22.36 | yes |
| fit_W01_W09_validate_W10_W13 | Current corrected baseline: 180d med / 0.35-1.50 both | 3.415 | 43.98 | 1.062 | -22.19 | no |
| fit_W01_W09_validate_W10_W13 | Balanced challenger: 90d med / 0.35-1.50 both | 3.675 | 44.23 | 1.125 | -21.05 | no |
| fit_W01_W09_validate_W10_W13 | Economics-first challenger: 60d med / 0.35-1.50 both | 4.002 | 43.51 | 1.159 | -20.12 | yes |

## Decision

- Corrected current baseline `180d`: `Return 2946.79% / Calmar 2.574 / MaxDD -28.41%`.
- `90d` is the balanced challenger: `Return 3114.74% / Calmar 2.762 / MaxDD -27.02%`.
- `60d` is the economics-first challenger: `Return 3327.75% / Calmar 2.988 / MaxDD -25.59%`.

## Verdict

- `60d` is the strongest full-sample economics contract, and it also improves W06 burden materially.
- But `60d` is not a clean freeze-date winner: in the early split `W01-W06 -> W07-W13`, both `180d` and `90d` validate better.
- `90d` is a more balanced sibling, but it still does not dominate the corrected `180d` baseline on the earliest freeze-date split.
- Promotion verdict: `HOLD_CURRENT_180D`.
- Reserve ranking: `90d` first, `60d` second if the goal is freeze-date credibility; `60d` first if the goal is pure economics exploration.
