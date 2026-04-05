# ATRVT H90 Refinement Screen

- Scope: keep the corrected combo mainline structure fixed, and refine only the ATR vol-targeting layer around the H90 challenger.
- Core side stays fixed at current combo logic:
  - `EMA250` sell-side
  - stable `close3`
  - high-churn `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the stricter gate earlier
- H90 anchor carried through this screen explicitly.

## Default Summary

| Candidate | Return% | Calmar | MaxDD% | Stress Calmar | Harsh Calmar | W06 DD/Exp | W11 AvgExp |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 60d med / 0.35-1.50 both | 3327.75 | 2.988 | -25.59 | 3.047 | 2.786 | -40.9% | 0.976 |
| 90d med / 0.35-1.25 both | 3078.77 | 2.926 | -25.40 | 2.990 | 2.733 | -45.0% | 0.964 |
| S1 60d med / S2 90d med | 3245.70 | 2.876 | -26.34 | 2.935 | 2.684 | -42.0% | 0.978 |
| S1 90d med 0.35-1.25 / S2 H90 | 3101.42 | 2.874 | -25.93 | 2.936 | 2.681 | -44.4% | 0.969 |
| S1 H90 / S2 90d med 0.35-1.25 | 3092.09 | 2.806 | -26.53 | 2.866 | 2.624 | -44.6% | 0.975 |
| S1 90d med / S2 120d med | 3088.78 | 2.764 | -26.92 | 2.823 | 2.582 | -44.5% | 0.985 |
| Anchor: 90d med / 0.35-1.50 both | 3114.74 | 2.762 | -27.02 | 2.820 | 2.579 | -44.0% | 0.980 |
| 90d med / 0.25-1.50 both | 3114.74 | 2.762 | -27.02 | 2.820 | 2.579 | -44.0% | 0.980 |
| 90d med / 0.50-1.50 both | 3114.66 | 2.762 | -27.02 | 2.820 | 2.579 | -44.1% | 0.980 |
| 90d mean / 0.35-1.50 both | 3296.70 | 2.756 | -27.65 | 2.810 | 2.569 | -42.0% | 1.035 |
| 120d med / 0.35-1.50 both | 3052.38 | 2.714 | -27.30 | 2.772 | 2.535 | -45.4% | 0.995 |
| 90d med / 0.35-1.75 both | 3131.02 | 2.698 | -27.72 | 2.754 | 2.518 | -43.5% | 0.982 |
| Reference: 180d med / 0.35-1.50 both | 2946.79 | 2.574 | -28.41 | 2.631 | 2.407 | -46.9% | 1.016 |

## Readout

- H90 anchor: `Return 3114.74% / Calmar 2.762 / MaxDD -27.02%`.
- Best screened candidate: `60d med / 0.35-1.50 both` with `Return 3327.75% / Calmar 2.988 / MaxDD -25.59%`.
- Best-vs-H90 delta: `dReturn +213.01pp / dCalmar +0.226 / dMaxDD +1.44pp`.

## Interpretation Hints

- `W11` entries and quick re-FLAT do not move here because the Core gate is fixed; this screen is only about sleeve sizing.
- The useful reads are therefore:
  - headline economics
  - `W06 DD/Exp`
  - `W11` average exposure
  - `S1 / S2` median scales inside `W06` and `W11`.