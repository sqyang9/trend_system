# Combo Walk-Forward Audit

## Scope

- Mainline not changed.
- This is a freeze-date / walk-forward credibility audit for the latest combo promotion.
- It does not attempt to re-open the older mother-line parameter history (`EMA250`, `close3`, `ATR 3.2 / 2.2`).
- It only tests whether the latest volatility-proxy promotion family looks materially weaker once candidate selection is forced to happen before later windows.

## Candidate Family Under Test

- `baseline` = pre-combo current mainline replay
- `p0_atrvt_s2`
- `p0_atrvt_all`
- `p1_hv85_coregate`
- `p1_hv90_coregate`
- `combo_s2_hv85`
- `combo_all_hv85`

## Selection Rule

- Training winner is selected by:
  - higher `Calmar`
  - then better `MaxDD`
  - then higher `Return`
- This is intentionally simple and stable; the goal is credibility, not re-optimization.

## Static Freeze Splits

| Split | Selected | Train Return% | Train Calmar | Train MaxDD% | Validate Return% | Validate Calmar | Validate MaxDD% | dCalmar vs Baseline |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fit_W01_W06_validate_W07_W13 | P0: ATR vol-targeting on S1+S2 | 1025.54 | 5.286 | -23.47 | 181.11 | 1.670 | -22.63 | +0.046 |
| fit_W01_W09_validate_W10_W13 | P0: ATR vol-targeting on S1+S2 | 2124.72 | 4.106 | -24.17 | 42.62 | 1.045 | -21.89 | +0.132 |

## Expanding Walk-Forward

- Stitched OOS windows: `W07-W13`.
- Expanding walk-forward stitched OOS: `Return 178.21% / Calmar 1.651 / MaxDD -22.63%`.
- Baseline stitched OOS delta: `dReturn +2.97pp / dCalmar +0.046 / dMaxDD +0.36pp`.
- Current combo stitched OOS on the same windows: `Return 171.47% / Calmar 1.605 / MaxDD -22.63%`.

Window-by-window picks:

| Validation Window | Training Span | Selected Candidate | Validation Calmar | Validation Return% |
| --- | --- | --- | --- | --- |
| W07 | W01-W06 | P0: ATR vol-targeting on S1+S2 | 4.485 | 26.42 |
| W08 | W01-W07 | P0: ATR vol-targeting on S1+S2 | 3.836 | 21.55 |
| W09 | W01-W08 | P0: ATR vol-targeting on S1+S2 | 3.393 | 28.49 |
| W10 | W01-W09 | P0: ATR vol-targeting on S1+S2 | 9.429 | 49.04 |
| W11 | W01-W10 | P0: ATR vol-targeting on S1+S2 | 0.378 | 3.26 |
| W12 | W01-W11 | P0: ATR vol-targeting on S1+S2 | -0.640 | -5.30 |
| W13 | W01-W12 | P0: ATR vol-targeting on S1+S2 | -1.161 | -3.32 |

## Readout

- `W01-W06 -> W07-W13` freeze selected `p0_atrvt_all` and validated at `Return 181.11% / Calmar 1.670 / MaxDD -22.63%`.
- `W01-W09 -> W10-W13` freeze selected `p0_atrvt_all` and validated at `Return 42.62% / Calmar 1.045 / MaxDD -21.89%`.
- Current promoted combo on those same validations delivered `W07-W13 Calmar 1.624` and `W10-W13 Calmar 1.041`.

## Verdict

- If the frozen-selection winner and the promoted combo remain close on later windows, the promotion looks less likely to be a pure in-sample artifact.
- If the frozen-selection winner flips away from combo and later OOS also clearly rejects combo, then the promotion should be treated as more fragile.
- This audit is about the latest combo package only; it is not a full mother-line parameter archaeology.