# Alpha Collapse Waterfall

- 是否推荐: 当前结果不支持直接把 launch_optimal 从 launch_no_go 改成 launch_go。
- 相对旧口径: 收益坍塌的主因不是单一滑点，而是 `legacy -> v2` 的 intrabar 语义迁移、因果执行和仓位压缩共同作用。
- 是否适合首发 live: 保护层和执行层更可靠了，但 alpha 层仍偏薄。
- 主要风险: 当前默认 pessimistic + full slippage 可能混入一部分过度保守；但 ideal_close / zero-slip 又明显不真实。
- 下一步主线: 先校准执行模型，再决定是否继续信号优化。

## Waterfall Total Table

| label                                                              | engine   |   Return_pct |   CAGR_pct |   Sharpe |   MaxDD_pct |    PF |   Trades |   unique_entries |   avg_legs_per_entry |   delta_Return_pct |   delta_Sharpe |   delta_MaxDD_pct |   delta_Trades |   delta_unique_entries |
|:-------------------------------------------------------------------|:---------|-------------:|-----------:|---------:|------------:|------:|---------:|-----------------:|---------------------:|-------------------:|---------------:|------------------:|---------------:|-----------------------:|
| Layer 0 | legacy old-style reference                               | legacy   |       639.02 |      37.9  |    1.183 |      -21.16 | 1.368 |      791 |              439 |                1.802 |               0    |           0    |              0    |              0 |                      0 |
| Bridge | v2 legacy-proxy (signal_close + optimistic + no_slippage) | v2       |       -87.29 |     -28.21 |   -1.023 |      -87.56 | 0.684 |      813 |              547 |                1.486 |            -726.31 |          -2.21 |            -66.39 |             22 |                    108 |
| Layer 1 | + next_bar_open                                          | v2       |        -2.42 |      -0.39 |   -0.077 |       -9.27 | 0.791 |       19 |               12 |                1.583 |              84.87 |           0.95 |             78.28 |           -794 |                   -535 |
| Layer 2 | + live_runner_next_5m_close                              | v2       |        -5.24 |      -0.86 |   -0.22  |       -8.9  | 0.508 |       14 |                9 |                1.556 |              -2.82 |          -0.14 |              0.37 |             -5 |                     -3 |
| Layer 3 | + base fixed slippage                                    | v2       |        -6.32 |      -1.04 |   -0.262 |       -9.89 | 0.404 |       13 |                9 |                1.444 |              -1.07 |          -0.04 |             -0.98 |             -1 |                      0 |
| Layer 4 | + full slippage model                                    | v2       |        -4.56 |      -0.75 |   -0.139 |      -10.21 | 0.655 |       25 |               17 |                1.471 |               1.76 |           0.12 |             -0.32 |             12 |                      8 |
| Layer 5 | + intrabar pessimistic                                   | v2       |        -4.56 |      -0.75 |   -0.139 |      -10.21 | 0.655 |       25 |               17 |                1.471 |               0    |           0    |              0    |              0 |                      0 |
| Layer 6 | + disable_partial_tp                                     | v2       |         7.37 |       1.15 |    0.232 |       -7.82 | 1.898 |       12 |               12 |                1     |              11.93 |           0.37 |              2.39 |            -13 |                     -5 |
| Layer 7 | + launch assumptions (position_pct=25)                   | v2       |        34.63 |       4.89 |    0.775 |       -4.5  | 2.842 |       69 |               69 |                1     |              27.25 |           0.54 |              3.32 |             57 |                     57 |

## Layer-by-Layer Interpretation

- Bridge | v2 legacy-proxy (signal_close + optimistic + no_slippage): Return -726.31pp, Sharpe -2.206, MaxDD -66.39pp, Trades +22, UniqueEntries +108, AvgLegs/Entry -0.316.
- Layer 1 | + next_bar_open: Return +84.87pp, Sharpe +0.946, MaxDD +78.28pp, Trades -794, UniqueEntries -535, AvgLegs/Entry +0.097.
- Layer 2 | + live_runner_next_5m_close: Return -2.82pp, Sharpe -0.143, MaxDD +0.37pp, Trades -5, UniqueEntries -3, AvgLegs/Entry -0.028.
- Layer 3 | + base fixed slippage: Return -1.07pp, Sharpe -0.042, MaxDD -0.98pp, Trades -1, UniqueEntries +0, AvgLegs/Entry -0.111.
- Layer 4 | + full slippage model: Return +1.76pp, Sharpe +0.123, MaxDD -0.32pp, Trades +12, UniqueEntries +8, AvgLegs/Entry +0.026.
- Layer 5 | + intrabar pessimistic: Return +0.00pp, Sharpe +0.000, MaxDD +0.00pp, Trades +0, UniqueEntries +0, AvgLegs/Entry +0.000.
- Layer 6 | + disable_partial_tp: Return +11.93pp, Sharpe +0.371, MaxDD +2.39pp, Trades -13, UniqueEntries -5, AvgLegs/Entry -0.471.
- Layer 7 | + launch assumptions (position_pct=25): Return +27.25pp, Sharpe +0.543, MaxDD +3.32pp, Trades +57, UniqueEntries +57, AvgLegs/Entry +0.000.

## Contribution Ranking

| factor                           |   delta_Return_pct |   delta_log_equity_return |   drop_share_of_total_log_change |
|:---------------------------------|-------------------:|--------------------------:|---------------------------------:|
| H. engine_semantic_migration     |            -726.31 |                    -4.063 |                            2.386 |
| A. entry_execution_realism       |              82.05 |                     2.009 |                           -1.18  |
| B. base_slippage                 |              -1.07 |                    -0.011 |                            0.007 |
| C. breakout_stop_range_penalties |               1.76 |                     0.019 |                           -0.011 |
| D. intrabar_pessimistic_path     |               0    |                     0     |                           -0     |
| E. partial_tp_removal            |              11.93 |                     0.118 |                           -0.069 |
| F. other_launch_constraints      |               0    |                     0     |                           -0     |
| G. position_sizing_effect        |              27.25 |                     0.226 |                           -0.133 |

### Top 3 Drags

| factor                       |   delta_Return_pct |   drop_share_of_total_log_change |
|:-----------------------------|-------------------:|---------------------------------:|
| H. engine_semantic_migration |            -726.31 |                            2.386 |
| B. base_slippage             |              -1.07 |                            0.007 |

## Reasonable De-Biasing vs Possible Over-Conservatism

| factor                           | label   | reason                                                                                                                                       |
|:---------------------------------|:--------|:---------------------------------------------------------------------------------------------------------------------------------------------|
| H. engine_semantic_migration     | 待重构  | Legacy 639% -> V2 idealized proxy already collapses hard. Directionally realistic, but magnitude is too large to accept without calibration. |
| A. entry_execution_realism       | 保留    | Signal-close fills are not live-tradable enough to remain the default research assumption.                                                   |
| B. base_slippage                 | 保留    | Zero slippage should not be the default research regime.                                                                                     |
| C. breakout_stop_range_penalties | 校准    | Correct directionally, but stop/range penalties should be calibrated against real paper/live logs.                                           |
| D. intrabar_pessimistic_path     | 校准    | Valid as stress mode, possibly too heavy as the sole daily default.                                                                          |
| E. partial_tp_removal            | 保留    | This is alpha rescue, not alpha drag. Keep partial TP off by default until a conditional TP design proves better.                            |
| G. position_sizing_effect        | 保留    | This is deployment sizing, not signal-quality decay.                                                                                         |

## Execution Matrix

Matrix scope: launch_optimal signal parameters, same position (`25%`), only execution realism dimensions vary.

| execution_mode            | intrabar_mode    | slippage_mode   | reality_band        |   Return_pct |   Sharpe |   MaxDD_pct |    PF |   Trades |
|:--------------------------|:-----------------|:----------------|:--------------------|-------------:|---------:|------------:|------:|---------:|
| live_runner_next_5m_close | midpoint         | fixed_only      | intermediate        |        40.63 |    0.89  |       -4.36 | 3.413 |       68 |
| live_runner_next_5m_close | optimistic       | fixed_only      | intermediate        |        37.97 |    0.849 |       -4.36 | 3.258 |       70 |
| live_runner_next_5m_close | pessimistic      | fixed_only      | intermediate        |        40.63 |    0.89  |       -4.36 | 3.413 |       68 |
| live_runner_next_5m_close | volatility_aware | fixed_only      | intermediate        |        40.63 |    0.89  |       -4.36 | 3.413 |       68 |
| live_runner_next_5m_close | midpoint         | full_model      | research_reasonable |        34.63 |    0.775 |       -4.5  | 2.842 |       69 |
| live_runner_next_5m_close | optimistic       | full_model      | intermediate        |        31.91 |    0.73  |       -4.5  | 2.691 |       71 |
| live_runner_next_5m_close | pessimistic      | full_model      | strict_stress       |        34.63 |    0.775 |       -4.5  | 2.842 |       69 |
| live_runner_next_5m_close | volatility_aware | full_model      | research_reasonable |        34.63 |    0.775 |       -4.5  | 2.842 |       69 |
| next_bar_open             | midpoint         | fixed_only      | intermediate        |        45.6  |    0.978 |       -4.33 | 3.805 |       66 |
| next_bar_open             | optimistic       | fixed_only      | intermediate        |        43.07 |    0.942 |       -4.33 | 3.649 |       68 |
| next_bar_open             | pessimistic      | fixed_only      | intermediate        |        45.6  |    0.978 |       -4.33 | 3.805 |       66 |
| next_bar_open             | volatility_aware | fixed_only      | intermediate        |        45.6  |    0.978 |       -4.33 | 3.805 |       66 |
| next_bar_open             | midpoint         | full_model      | research_reasonable |        38    |    0.842 |       -4.47 | 3.146 |       66 |
| next_bar_open             | optimistic       | full_model      | intermediate        |        35.52 |    0.804 |       -4.47 | 2.995 |       68 |
| next_bar_open             | pessimistic      | full_model      | intermediate        |        38    |    0.842 |       -4.47 | 3.146 |       66 |
| next_bar_open             | volatility_aware | full_model      | research_reasonable |        38    |    0.842 |       -4.47 | 3.146 |       66 |

## Trade Count Collapse Attribution

| label                                                              |   Trades |   unique_entries |   avg_legs_per_entry |   delta_Trades |   delta_unique_entries |   delta_avg_legs_per_entry |
|:-------------------------------------------------------------------|---------:|-----------------:|---------------------:|---------------:|-----------------------:|---------------------------:|
| Layer 0 | legacy old-style reference                               |      791 |              439 |                1.802 |              0 |                      0 |                      0     |
| Bridge | v2 legacy-proxy (signal_close + optimistic + no_slippage) |      813 |              547 |                1.486 |             22 |                    108 |                     -0.316 |
| Layer 2 | + live_runner_next_5m_close                              |       14 |                9 |                1.556 |           -799 |                   -538 |                      0.069 |
| Layer 5 | + intrabar pessimistic                                   |       25 |               17 |                1.471 |             11 |                      8 |                     -0.085 |
| Layer 6 | + disable_partial_tp                                     |       12 |               12 |                1     |            -13 |                     -5 |                     -0.471 |
| Layer 7 | + launch assumptions (position_pct=25)                   |       69 |               69 |                1     |             57 |                     57 |                      0     |

- Legacy -> V2 bridge keeps trade legs broadly similar if partial TP is still enabled, so the first collapse is expectancy collapse, not signal disappearance.
- Execution realism changes unique entries, but not enough to explain the full trade-leg collapse on its own.
- Disabling partial TP compresses trade legs much more than unique entries, so a large part of 791 -> 69 is statistics compression rather than raw signal scarcity.
- Position sizing still changes realized entry count because daily-loss gating and compounding alter whether later entries are allowed.

## Recommended Default Regime

- Recommended: `next_bar_open` + `midpoint` + `full_model`
- Reason: Chosen from causal, non-zero slippage, paper/live-explainable candidates. Pessimistic full-model stays as stress mode.
- Stress default should remain: `live_runner_next_5m_close + pessimistic + full_model`

## Next Steps

- First, calibrate the V2 intrabar sequencing model against paper/live fills before touching signal parameters again.
- Second, keep `disable_partial_tp` as an explicit switch in attribution studies, because it changes trade-leg statistics more than raw signal count.
- Third, keep position sizing out of alpha discussions; treat it as launch deployment policy.