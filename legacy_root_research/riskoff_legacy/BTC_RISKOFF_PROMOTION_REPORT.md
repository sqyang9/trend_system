# BTC Risk-Off Promotion Report

## Promotion Judgment

- This round is promotion validation, not new strategy exploration.
- Promotion answer: NO. Risk-Off does not yet clear promotion-candidate validation.
- Evidence level after this round: aligned but preliminary
- Baseline promotion recommendation: NO. Keep Risk-Off below baseline and continue to treat it as aligned but preliminary.
- Preferred system direction: AddOn + Risk-Off is still the preferred direction for validation, but not yet baseline-worthy.

## Full-Sample Snapshot

| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Exposure% | Avg Core% | Risk-Off Active% | State Changes | dRet vs AddOn | dCalmar | dMaxDD improve |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B&H | 856.16 | 43.73 | 0.750 | 0.568 | -77.04 | 100.0 | 100.0 | 0.0 | 0 | -104.56 | -0.068 | -4.43 |
| Core+AddOnOverlay | 960.72 | 46.14 | 0.791 | 0.636 | -72.61 | 108.8 | 100.0 | 0.0 | 0 | +0.00 | +0.000 | +0.00 |
| Core+AddOnOverlay+RO_EMA200_FLAT | 1319.64 | 53.15 | 1.007 | 1.048 | -50.73 | 67.7 | 58.9 | 41.1 | 224 | +358.92 | +0.412 | +21.88 |
| Core+AddOnOverlay+RO_EMA220_FLAT | 1626.59 | 58.04 | 1.068 | 1.097 | -52.90 | 67.7 | 58.9 | 41.1 | 204 | +665.87 | +0.462 | +19.71 |
| Core+RO_EMA220_FLAT | 1521.68 | 56.46 | 1.035 | 1.012 | -55.80 | 58.9 | 58.9 | 41.1 | 204 | +560.96 | +0.376 | +16.81 |

## Walk-Forward OOS

- Train rule: 3-year train window, choose only between `RO_EMA200_FLAT` and `RO_EMA220_FLAT` by train Calmar, then Sharpe.
- Test rule: 1-year OOS window, compare selected Risk-Off system vs AddOn-only.

| Test Year | Selected | Test Return% | Test Sharpe | Test MaxDD% | dRet vs AddOn | dSharpe | dCalmar | dMaxDD improve | Strict Outperform |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2023 | Core+AddOnOverlay+RO_EMA220_FLAT | 90.67 | 1.720 | -19.13 | -40.14 | -0.313 | -2.349 | -0.66 | False |
| 2024 | Core+AddOnOverlay+RO_EMA220_FLAT | 90.16 | 1.475 | -23.59 | -18.28 | +0.017 | +0.095 | +5.50 | True |
| 2025 | Core+AddOnOverlay+RO_EMA200_FLAT | -15.71 | -0.451 | -29.16 | -9.89 | -0.502 | -0.360 | +3.28 | False |

- WF selection counts: {'RO_EMA200_FLAT': 1, 'RO_EMA220_FLAT': 2}
- WF selected average OOS Sharpe: 0.915
- WF strict outperform ratio vs AddOn-only: 0.33
- WF average delta Return vs AddOn-only: -22.77pp
- WF average delta Calmar vs AddOn-only: -0.871

## Time-Slice Stability

| Slice | AddOn Return% | EMA200 Return% | EMA220 Return% | EMA200 dMaxDD | EMA220 dMaxDD |
| --- | --- | --- | --- | --- | --- |
| bull_expansion | 968.81 | 660.92 | 735.75 | +20.78 | +24.21 |
| major_drawdown | -70.66 | -49.17 | -50.88 | +21.93 | +20.26 |
| recovery_phase | 278.32 | 212.74 | 200.73 | -1.29 | -0.66 |
| sideways_volatility | -1.67 | -0.43 | 18.19 | +12.64 | +21.93 |

## Small Neighborhood Robustness

- Plateau judgment across EMA200/210/220: True
- Best scheme in the narrow plateau check: Core+AddOnOverlay+RO_EMA220_FLAT
- Calmar spread across EMA200/210/220: 0.049
- Sharpe spread across EMA200/210/220: 0.061

## Execution And Cost Sensitivity

- Execution sensitivity EMA200: Return +121.61pp, Sharpe +0.025, MaxDD improve +0.19pp
- Execution sensitivity EMA220: Return +80.03pp, Sharpe +0.014, MaxDD improve -0.11pp
- Higher-cost sensitivity EMA200: Return -295.97pp, Sharpe -0.071, MaxDD improve -1.83pp
- Higher-cost sensitivity EMA220: Return -329.95pp, Sharpe -0.065, MaxDD improve -1.68pp

## Causality Audit

- Default-mode causality violations: 0
- Stress-mode causality violations: 0

## Direct Answers

- In walk-forward OOS, AddOn + Risk-Off does not beat AddOn-only consistently enough for promotion. It wins only one of three strict OOS windows.
- RO_EMA220_FLAT is better on the full sample, but RO_EMA200_FLAT is close enough to treat them as the same class.
- EMA200-220 behaves like a stable plateau, not a single isolated EMA220 spike.
- Risk-Off edge comes mainly from bear-market protection and the compounding benefit of materially smaller drawdowns, not from a single crash-only outlier.
- Current evidence level remains `aligned but preliminary`.
- NO. Keep Risk-Off below baseline and continue to treat it as aligned but preliminary.