# BTC Risk-Off Promotion V2 Report

## Final Judgment

- This round is structure-repair validation, not a new Risk-Off search.
- Promotion v2 answer: PARTIAL. Promotion v2 reduces opportunity cost, but it still does not clear the promotion bar.
- Best repair candidate: Core+AddOnOverlay+RO_EMA220_TWOSTAGE_50_TO_0
- Promotion status after v2: aligned but preliminary
- Recommendation: Keep AddOn-only baseline unchanged. At most, run one final narrow promotion check on the single best repair candidate.

## Candidate Set

- This round stays inside the locked EMA200/220 family and only tests small repairs.
- Recovery-hold variants were not expanded because they mechanically increase the exact opportunity cost this round is trying to reduce.

| Candidate | Return% | Sharpe | Calmar | MaxDD% | Avg Core% | Risk-Off Active% | State Changes | dRet vs AddOn | dCalmar |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RO_EMA200_FLAT | 1319.64 | 1.007 | 1.048 | -50.73 | 58.9 | 41.1 | 224 | +358.92 | +0.412 |
| RO_EMA220_FLAT | 1626.59 | 1.068 | 1.097 | -52.90 | 58.9 | 41.1 | 204 | +665.87 | +0.462 |
| RO_EMA200_HYST_OFF2_ON1 | 919.34 | 0.927 | 0.762 | -59.36 | 55.5 | 44.5 | 102 | -41.38 | +0.126 |
| RO_EMA220_HYST_OFF2_ON1 | 1353.75 | 1.032 | 0.907 | -59.28 | 55.7 | 44.3 | 92 | +393.03 | +0.271 |
| RO_EMA200_TWOSTAGE_50_TO_0 | 1335.84 | 1.010 | 0.989 | -54.01 | 59.3 | 41.1 | 318 | +375.12 | +0.354 |
| RO_EMA220_TWOSTAGE_50_TO_0 | 1778.06 | 1.092 | 1.102 | -54.60 | 59.3 | 41.1 | 289 | +817.34 | +0.467 |

## Walk-Forward OOS

| Candidate | Strict Win Ratio | Avg dReturn vs AddOn | Avg dCalmar |
| --- | --- | --- | --- |
| RO_EMA200_FLAT | 0.00 | -24.27pp | -1.016 |
| RO_EMA220_FLAT | 0.33 | -19.29pp | -0.767 |
| RO_EMA200_HYST_OFF2_ON1 | 0.33 | -27.34pp | -1.056 |
| RO_EMA220_HYST_OFF2_ON1 | 0.33 | -17.65pp | -0.644 |
| RO_EMA200_TWOSTAGE_50_TO_0 | 0.00 | -20.40pp | -0.766 |
| RO_EMA220_TWOSTAGE_50_TO_0 | 0.33 | -11.47pp | -0.174 |

- WF train-selected v2 strict win ratio: 0.33
- WF train-selected v2 average delta Return: -16.22pp
- WF train-selected v2 average delta Calmar: -0.557

## Time-Slice Focus

| Candidate | Bull dReturn | Recovery dReturn | Major Drawdown dReturn | Major Drawdown dMaxDD |
| --- | --- | --- | --- | --- |
| RO_EMA200_FLAT | -307.89pp | -65.58pp | +21.49pp | +21.93pp |
| RO_EMA220_FLAT | -233.07pp | -77.59pp | +19.78pp | +20.26pp |
| RO_EMA200_HYST_OFF2_ON1 | -431.05pp | -87.96pp | +12.55pp | +13.28pp |
| RO_EMA220_HYST_OFF2_ON1 | -324.62pp | -80.37pp | +12.67pp | +13.37pp |
| RO_EMA200_TWOSTAGE_50_TO_0 | -291.68pp | -48.95pp | +18.09pp | +18.65pp |
| RO_EMA220_TWOSTAGE_50_TO_0 | -225.46pp | -48.82pp | +17.70pp | +18.24pp |

## Execution Stress And Causality

- RO_EMA200_FLAT: stress delta Return +121.61pp, Sharpe +0.025, MaxDD improve +0.19pp
- RO_EMA220_FLAT: stress delta Return +80.03pp, Sharpe +0.014, MaxDD improve -0.11pp
- RO_EMA200_HYST_OFF2_ON1: stress delta Return +70.24pp, Sharpe +0.021, MaxDD improve +0.65pp
- RO_EMA220_HYST_OFF2_ON1: stress delta Return +118.68pp, Sharpe +0.024, MaxDD improve +0.77pp
- RO_EMA200_TWOSTAGE_50_TO_0: stress delta Return +136.28pp, Sharpe +0.028, MaxDD improve -0.00pp
- RO_EMA220_TWOSTAGE_50_TO_0: stress delta Return +117.18pp, Sharpe +0.019, MaxDD improve -0.05pp
- Default-mode causality violations: 0
- Stress-mode causality violations: 0

## Direct Answers

- Yes. The v1 failure is still consistent with bull/recovery opportunity cost. Best candidate still gives bull delta -225.46pp and recovery delta -48.82pp versus AddOn-only.
- No repair candidate materially fixes the OOS issue. Best candidate is Core+AddOnOverlay+RO_EMA220_TWOSTAGE_50_TO_0, but strict OOS win ratio is still only 0.33.
- No. Strict OOS win ratio does not improve beyond the v1 level of 0.33 in a meaningful way.
- Yes. Best candidate lifts avg delta Return to -11.47pp and avg delta Calmar to -0.174 while keeping major-drawdown MaxDD improvement at +18.24pp.
- No. Even after the repair test, Risk-Off should remain below promotion-candidate status.
- Keep AddOn-only baseline unchanged. If Risk-Off work continues, narrow it to the single best repair candidate only.