# Volatility Proxy Final Audition

## Scope

- Mainline not changed.
- This audit upgrades the prior screen into a promotion-style readout for the volatility-proxy branch.
- Candidate set is intentionally narrow:
  - baseline replay of the current official mainline rules
  - strongest P0-only fix: `ATR vol-targeting on S1+S2`
  - strongest P1-only fix: `HV90 forces high-churn gate`
  - strongest combined fix: `ATR vol-targeting on S1+S2 + HV85 forces high-churn gate`

## Canonical Baseline

- Official mainline headline remains `Return 2878.61% / Calmar 2.854 / MaxDD -25.41%` from `official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md`.
- Local replay baseline inside this audition engine is `Return 2893.89% / Calmar 2.854 / MaxDD -25.46%`.
- Promotion judgment below uses local deltas inside the same engine for apples-to-apples comparison.

## Default

| Candidate | Thesis | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgTotalExp% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Current mainline replay | Reference | 2893.89 | 2.854 | -25.46 | -15.78 | -16.23 | 14.7 | 92.75 |
| P0 only: ATR vol-targeting on S1+S2 | Fix P0 | 3072.90 | 3.073 | -24.17 | -16.11 | -15.64 | 43.5 | 92.75 |
| P1 only: HV90 forces HC gate | Fix P1 | 2857.92 | 2.841 | -25.46 | -15.81 | -16.23 | 14.7 | 92.63 |
| Combo: S1+S2 ATR VT + HV85 HC gate | Fix P0+P1 | 2995.89 | 3.044 | -24.17 | -16.13 | -15.63 | 43.5 | 92.57 |

## Scenario Delta Vs Baseline Replay

| Candidate | Default dReturn | Default dCalmar | Default dMaxDD | Stress dCalmar | Harsh dCalmar |
| --- | --- | --- | --- | --- | --- |
| P0 only | +179.00pp | +0.219 | +1.29pp | +0.183 | +0.298 |
| P1 only | -35.97pp | -0.013 | +0.00pp | -0.014 | -0.011 |
| Combo | +102.00pp | +0.191 | +1.29pp | +0.155 | +0.273 |

## W06 / W11

| Candidate | W06 DD/Exp | W06 MaxDD% | W11 Entries | W11 Quick14 | W11 Quick30 | W11 AvgExp |
| --- | --- | --- | --- | --- | --- | --- |
| Current mainline replay | -49.5% | -23.13 | 4 | 50.0% | 75.0% | 0.929 |
| P0 only: ATR vol-targeting on S1+S2 | -47.4% | -22.15 | 4 | 50.0% | 75.0% | 0.929 |
| P1 only: HV90 forces HC gate | -49.5% | -23.13 | 3 | 33.3% | 66.7% | 0.927 |
| Combo: S1+S2 ATR VT + HV85 HC gate | -47.4% | -22.15 | 3 | 33.3% | 66.7% | 0.920 |

## Churn Audit

| Candidate | Full RE | Median Days RE->next FLAT | Quick14 | Quick30 | HC Quick14 | HC Quick30 |
| --- | --- | --- | --- | --- | --- | --- |
| Current mainline replay | 38 | 19.0 | 44.7% | 60.5% | 31.8% | 54.5% |
| P0 only: ATR vol-targeting on S1+S2 | 38 | 19.0 | 44.7% | 60.5% | 31.8% | 54.5% |
| P1 only: HV90 forces HC gate | 37 | 19.2 | 43.2% | 59.5% | 29.2% | 50.0% |
| Combo: S1+S2 ATR VT + HV85 HC gate | 37 | 19.2 | 43.2% | 59.5% | 32.0% | 52.0% |

## Annual Starts

- `P0 only` vs baseline replay: Calmar better `7/7`, MaxDD better `7/7`, Return better `7/7`.
- `Combo` vs baseline replay: Calmar better `6/7`, MaxDD better `7/7`, Return better `5/7`.

## Readout

- `P0 only` is the strongest economic fix: default `Return 3072.90% / Calmar 3.073 / MaxDD -24.17%`, and it improves W06 `DD/Exp` from -49.5% to -47.4%.
- `P1 only` is a real detector upgrade but still too weak standalone: W11 entries drop from 4 to 3, yet default return/calmar stay below baseline replay.
- `Combo` is the best dual-defect candidate: default `Return 2995.89% / Calmar 3.044 / MaxDD -24.17%`, W06 `DD/Exp -47.4%`, W11 `entries 3, quick14 33.3%`.
- Promotion framing: if the goal is pure portfolio economics, `P0 only` should lead the next round; if the goal is to repair both P0 and P1 in one package, `Combo` is the better promotion candidate.

## Verdict

- `P0 only`: `GO_TO_AUDITION`.
- `P1 only`: `NO_GO` as a standalone promotion candidate, but `GO` as background data reserve.
- `Combo`: `GO_TO_AUDITION` as the best integrated system-defect candidate.