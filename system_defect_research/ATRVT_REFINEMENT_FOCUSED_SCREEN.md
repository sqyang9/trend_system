# ATRVT Refinement Focused Screen

- Scope: keep the corrected combo mainline fixed and only refine ATRVT around `H60/H90` plus nearby contracts.
- Candidate families in this screen:
  - symmetric horizons `45 / 60 / 75 / 90 / 120 / 180`
  - light clip tweaks around `H60/H90`
  - `S1/S2` asymmetric horizons

## Top By Default

| Candidate | Return% | Calmar | MaxDD% | Stress Calmar | Harsh Calmar | W06 DD/Exp | W11 AvgExp | WF Avg Calmar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 45d med / 0.35-1.50 both | 3355.48 | 3.036 | -25.26 | 3.096 | 2.827 | -40.1% | 0.958 | 1.312 |
| 60d med / 0.35-1.35 both | 3248.30 | 3.001 | -25.25 | 3.062 | 2.800 | -42.2% | 0.968 | 1.374 |
| 60d med / 0.45-1.50 both | 3327.85 | 2.988 | -25.59 | 3.047 | 2.786 | -40.9% | 0.976 | 1.373 |
| 60d med / 0.35-1.50 both | 3327.75 | 2.988 | -25.59 | 3.047 | 2.786 | -40.9% | 0.976 | 1.373 |
| 60d med / 0.35-1.65 both | 3351.18 | 2.985 | -25.67 | 3.044 | 2.782 | -40.3% | 0.978 | 1.360 |
| 90d med / 0.35-1.25 both | 3078.77 | 2.926 | -25.40 | 2.990 | 2.733 | -45.0% | 0.964 | 1.378 |
| S1 60d 0.35-1.50 / S2 90d 0.35-1.50 | 3245.70 | 2.876 | -26.34 | 2.935 | 2.684 | -42.0% | 0.978 | 1.357 |
| S1 90d 0.35-1.50 / S2 60d 0.35-1.50 | 3196.79 | 2.873 | -26.23 | 2.932 | 2.680 | -42.7% | 0.978 | 1.410 |

## Top By Walk-Forward Average Calmar

| Candidate | Split1 Val Ret% | Split1 Val Calmar | Split2 Val Ret% | Split2 Val Calmar | Default Calmar |
| --- | --- | --- | --- | --- | --- |
| S1 180d 0.35-1.50 / S2 60d 0.35-1.50 | 181.07 | 1.758 | 45.09 | 1.144 | 2.716 |
| 120d med / 0.35-1.50 both | 186.30 | 1.711 | 45.07 | 1.121 | 2.714 |
| S1 90d 0.35-1.50 / S2 60d 0.35-1.50 | 174.12 | 1.661 | 44.70 | 1.159 | 2.873 |
| 180d med / 0.35-1.50 both | 190.80 | 1.739 | 43.98 | 1.062 | 2.574 |
| 90d med / 0.35-1.50 both | 179.63 | 1.665 | 44.23 | 1.125 | 2.762 |
| 75d med / 0.35-1.50 both | 172.89 | 1.626 | 43.83 | 1.140 | 2.860 |
| 90d med / 0.35-1.25 both | 177.64 | 1.660 | 43.36 | 1.095 | 2.926 |
| 60d med / 0.35-1.35 both | 168.67 | 1.606 | 43.41 | 1.141 | 3.001 |

## Anchor Readout

- `H90`: `Return 3114.74% / Calmar 2.762 / MaxDD -27.02%`; walk-forward avg Calmar `1.395`.
- `H60`: `Return 3327.75% / Calmar 2.988 / MaxDD -25.59%`; walk-forward avg Calmar `1.373`.

## Interpretation Hints

- If a contract wins default but falls behind on both freeze-date splits, treat it as economics-first rather than promotion-ready.
- If an asymmetric contract keeps most of the H60 economics while repairing freeze-date splits, that is the most interesting follow-up path.
