# ATRVT Refinement Screen

- Scope: keep the promoted combo mainline structure fixed, and refine only the ATR vol-targeting layer.
- Core side stays fixed at current combo logic:
  - `EMA250` sell-side
  - stable `close3`
  - high-churn `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the stricter gate earlier
- Only three ATRVT dimensions are tested:
  - reference horizon / statistic
  - clip band
  - `S1 / S2` asymmetry

## Default Summary

| Candidate | Return% | Calmar | MaxDD% | Stress Calmar | Harsh Calmar | W06 DD/Exp | W11 AvgExp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Combo h90: 90d med / 0.35-1.50 both | 3114.74 | 2.762 | -27.02 | 2.820 | 2.579 | -44.0% | 0.980 |
| Combo asym: S1 90d med / S2 base | 3023.76 | 2.730 | -27.05 | 2.789 | 2.551 | -45.1% | 0.993 |
| Combo clip: 180d med / 0.35-1.25 both | 2895.67 | 2.715 | -26.76 | 2.777 | 2.542 | -48.1% | 0.985 |
| Combo h365: 365d med / 0.35-1.50 both | 3038.93 | 2.629 | -28.14 | 2.686 | 2.456 | -46.1% | 1.008 |
| Combo asym: S1 loose / S2 tight | 2927.42 | 2.622 | -27.83 | 2.681 | 2.454 | -47.7% | 1.010 |
| Combo asym: S1 base / S2 tight | 2925.94 | 2.604 | -28.01 | 2.662 | 2.439 | -47.7% | 1.006 |
| Combo clip: 180d med / 0.35-1.75 both | 2967.55 | 2.581 | -28.41 | 2.637 | 2.411 | -46.4% | 1.023 |
| Combo base: 180d med / 0.35-1.50 both | 2946.79 | 2.574 | -28.41 | 2.631 | 2.407 | -46.9% | 1.016 |
| Combo clip: 180d med / 0.25-1.50 both | 2946.55 | 2.574 | -28.41 | 2.631 | 2.407 | -46.9% | 1.016 |
| Combo clip: 180d med / 0.50-1.50 both | 2927.48 | 2.568 | -28.41 | 2.625 | 2.402 | -47.1% | 1.016 |
| Combo mean180: 180d mean / 0.35-1.50 both | 3069.29 | 2.430 | -30.55 | 2.479 | 2.272 | -44.8% | 1.043 |

## Readout

- Current combo base: `Return 2946.79% / Calmar 2.574 / MaxDD -28.41%`.
- Best screened candidate: `Combo h90: 90d med / 0.35-1.50 both` with `Return 3114.74% / Calmar 2.762 / MaxDD -27.02%`.
- Best-vs-base delta: `dReturn +167.95pp / dCalmar +0.188 / dMaxDD +1.39pp`.

## Interpretation Hints

- `W11` entries and quick re-FLAT do not move here because the Core gate is fixed; this screen is only about sleeve sizing.
- The useful reads are therefore:
  - headline economics
  - `W06 DD/Exp`
  - how the scale changes in `W06` and `W11` for `S1` and `S2` separately.