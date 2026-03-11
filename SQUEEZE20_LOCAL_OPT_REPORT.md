# SQUEEZE20 Local Optimization Report

## Conclusion

- New research_optimal: `lb20_stop3.2_trail5.0_beoff`
- Upgrade to new research_optimal: YES
- launch_optimal: `LAUNCH_NO_GO`
- 35% sizing conclusion: the main remaining blocker is `baseline_gate`'s trade-count threshold, which is mismatched for a low-frequency trend mother. This is not a system-safety failure and not a stress-test failure.
- Decision note: `lb20_stop3.2_trail5.0_beoff` improved return, CAGR, Sharpe, Calmar, and PF versus the prior research_optimal while preserving the same non-baseline Gatekeeper V2 pass profile. It is now the new research_optimal, but it is still not launch-approved.

## Direct Answers

1. Most worth optimizing now: initial_stop_atr and donchian_entry_len
2. Most promising local neighborhood: lookback around 20-22 with initial_stop_atr around 3.2-3.4 remains the highest-value neighborhood; trail_atr_mult should stay centered near 5.0, and break-even should remain disabled unless a clearly stronger raw winner appears.
3. Sharpe/Calmar still ahead while CAGR moves closer to B&H: Yes. `lb20_stop3.2_trail5.0_beoff` improved CAGR, Sharpe, and Calmar versus the prior research_optimal, then passed the full non-baseline Gatekeeper V2 stack. That is sufficient to upgrade it as the new research_optimal, even though it remains `LAUNCH_NO_GO`.
4. Baseline_gate diagnosis: At 100% sizing, baseline_gate still fails for more than just trade count because MaxDD remains below the -30% cap. At 35% sizing, the main remaining blocker is the legacy 250-trade threshold, which does not fit a low-frequency trend mother. This is not a system-safety or other stress failure.

## Best Candidates

| Variant | Return% | CAGR% | Sharpe | Calmar | MaxDD% | Trades |
| --- | --- | --- | --- | --- | --- | --- |
| lb20_stop3.2_trail5.0_beoff | 470.51 | 32.28 | 0.933 | 0.936 | -34.49 | 56 |
| lb20_stop3.4_trail5.0_beoff | 461.92 | 31.96 | 0.926 | 0.927 | -34.49 | 56 |
| lb22_stop3.4_trail5.0_beoff | 439.18 | 31.09 | 0.910 | 0.901 | -34.49 | 56 |
| lb20_stop3.4_trail5.2_beoff | 399.60 | 29.49 | 0.864 | 0.844 | -34.95 | 56 |
| lb22_stop3.2_trail5.2_beoff | 387.95 | 29.00 | 0.857 | 0.830 | -34.95 | 56 |

## Details

- Default research tuple: next_bar_open + legacy_bar_extrema + midpoint + full_model
- Stress tuple: live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model
- New research_optimal stats: Return 470.51%, CAGR 32.28%, Sharpe 0.933, MaxDD -34.49%, PF 1.947, Trades 56
- Prior research_optimal stats: Return 461.92%, CAGR 31.96%, Sharpe 0.926, MaxDD -34.49%, PF 1.928, Trades 56
- New full-size gate summary: {"baseline_gate":false,"yearly":true,"rolling_oos":true,"regime":true,"cost_stress":true,"slippage_stress":true,"execution_mode_stress":true,"intrabar_path_stress":true,"live_safety_check":true}
- New 35% gate summary: {"baseline_gate":false,"yearly":true,"rolling_oos":true,"regime":true,"cost_stress":true,"slippage_stress":true,"execution_mode_stress":true,"intrabar_path_stress":true,"live_safety_check":true}
- launch_optimal remains `LAUNCH_NO_GO` because `baseline_gate` is still false at 35% sizing.
- 35% baseline_gate details: Sharpe 0.926, MaxDD -14.72%, PF 2.376, Trades 56, pass=False
- 35% mismatch note: Legacy baseline_gate trade threshold may be too high for a low-frequency trend mother.

### Parameter Sensitivity
- `initial_stop_atr` tested span: return 82.56pp, CAGR 3.28pp, best tested value 3.2
- `donchian_entry_len` tested span: return 51.23pp, CAGR 2.09pp, best tested value 22
- `trail_atr_mult` tested span: return 11.65pp, CAGR 0.49pp, best tested value 5.2
