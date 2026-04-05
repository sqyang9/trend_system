# ATRVT H60 Walk-Forward Audit

- Scope: corrected ATRVT lineage only.
- Comparison set:
  - `180d median / 0.35-1.50 both`
  - `90d median / 0.35-1.50 both`
  - `60d median / 0.35-1.50 both`

## Split Summary

| Split | Train Winner | Winner Val Return% | Winner Val Calmar | H60 Val Return% | H60 Val Calmar | H90 Val Return% | H90 Val Calmar | 180d Val Return% | 180d Val Calmar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fit_W01_W06_validate_W07_W13 | 60d med / 0.35-1.50 both | 166.26 | 1.587 | 166.26 | 1.587 | 179.63 | 1.665 | 190.80 | 1.739 |
| fit_W01_W09_validate_W10_W13 | 60d med / 0.35-1.50 both | 43.51 | 1.159 | 43.51 | 1.159 | 44.23 | 1.125 | 43.98 | 1.062 |

## OOS Readout

- Fixed OOS `W07-W13`: 180d `190.80% / 1.739 / -22.58%`.
- Fixed OOS `W07-W13`: 90d `179.63% / 1.665 / -22.56%`.
- Fixed OOS `W07-W13`: 60d `166.26% / 1.587 / -22.36%`.
- Expanding stitched OOS: `163.62% / 1.569 / -22.36%`.

## Interpretation

- This audit asks whether `H60` still survives freeze-date style evaluation, not whether it is the best in-sample default screen point.
- If `H60` keeps winning or tying on the validation side, promotion credibility rises materially.