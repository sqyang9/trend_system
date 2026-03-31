# Gatekeeper V2

- Recommended: launch candidate must pass all gates
- Compared with baseline: materially stricter
- Suitable for first live launch: NO
- Main risk: pessimistic path and realistic execution can still fail launch gate

## Gates
- baseline_gate: Sharpe >= 0.80, MaxDD >= -30%, PF >= 1.15, Trades >= 250
- yearly: positive_year_ratio >= 0.60, avg_sharpe >= 0.40, worst_return > -35%
- rolling_oos: avg_sharpe >= 0.30, positive_ratio >= 0.55
- regime: all regime returns > -35%, all MaxDD > -40%
- cost_stress: 0.20% commission still positive, Sharpe >= 0.25, MaxDD >= -35%
- slippage_stress: stressed slippage return > -20%, MaxDD >= -40%
- execution_mode_stress: all realistic entry modes stay above -25% return and -40% MaxDD
- intrabar_path_stress: pessimistic path stays above -25% return and -40% MaxDD
- live_safety_check: protection / reconcile / state hardening checks pass

## Launch Candidate Gate Summary
- baseline_gate: FAIL
- yearly: FAIL
- rolling_oos: FAIL
- regime: PASS
- cost_stress: PASS
- slippage_stress: PASS
- execution_mode_stress: PASS
- intrabar_path_stress: PASS
- live_safety_check: PASS

## Research Candidate Gate Summary
- baseline_gate: FAIL
- yearly: FAIL
- rolling_oos: FAIL
- regime: PASS
- cost_stress: FAIL
- slippage_stress: PASS
- execution_mode_stress: FAIL
- intrabar_path_stress: PASS
- live_safety_check: PASS