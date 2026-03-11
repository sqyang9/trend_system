# Intrabar Model Comparison

- 是否推荐继续调参: 不推荐。在 intrabar model 校准前，应暂停所有参数优化。
- 最接近 legacy 的模型: `legacy_bar_extrema`
- 新的日常研究默认模型: `legacy_bar_extrema`
- stress / gate 模型: `segment_path_same_bar`
- 核心结论: 当前 alpha collapse 可以正式定义为 `5m intrabar execution model` 语义不兼容。

## Model Definitions

- `legacy_bar_extrema`: 先检查 bar 开始时已有保护，再用整根 bar 极值更新 TP/BE/TRAIL；新保护下一 bar 才生效。
- `segment_path_same_bar`: 5m bar 内按 path segment 推进；新激活的保护允许同 bar 递归生效。
- `segment_path_defer_protective`: 仍按 segment 推进，但新激活的保护性 stop（BE/TRAIL）延后到下一 bar 才生效；TP 仍可同 bar 执行。

## Experiment 1

| name                                                      |   Return_pct |   CAGR_pct |    Sharpe |   MaxDD_pct |       PF |   Trades |   unique_entries |   avg_legs_per_entry |   avg_hold_4h_bars | profile                    | model                         |
|:----------------------------------------------------------|-------------:|-----------:|----------:|------------:|---------:|---------:|-----------------:|---------------------:|-------------------:|:---------------------------|:------------------------------|
| bridge_opt_signal_60_tp_on::legacy_bar_extrema            |    -81.5567  | -23.7843   | -0.827118 |   -83.0105  | 0.71989  |      821 |              539 |              1.52319 |            15.141  | bridge_opt_signal_60_tp_on | legacy_bar_extrema            |
| bridge_opt_signal_60_tp_on::segment_path_same_bar         |    -87.2527  | -28.1759   | -1.02177  |   -87.5186  | 0.683981 |      815 |              548 |              1.48723 |            14.4769 | bridge_opt_signal_60_tp_on | segment_path_same_bar         |
| bridge_opt_signal_60_tp_on::segment_path_defer_protective |    -87.2527  | -28.1759   | -1.02177  |   -87.5186  | 0.683981 |      815 |              548 |              1.48723 |            14.4769 | bridge_opt_signal_60_tp_on | segment_path_defer_protective |
| research_main_60_tp_off::legacy_bar_extrema               |      4.84932 |   0.763727 |  0.162546 |    -9.59773 | 1.51351  |       13 |               13 |              1       |            22.1971 | research_main_60_tp_off    | legacy_bar_extrema            |
| research_main_60_tp_off::segment_path_same_bar            |      4.84932 |   0.763727 |  0.162546 |    -9.59773 | 1.51351  |       13 |               13 |              1       |            22.1971 | research_main_60_tp_off    | segment_path_same_bar         |
| research_main_60_tp_off::segment_path_defer_protective    |      4.84932 |   0.763727 |  0.162546 |    -9.59773 | 1.51351  |       13 |               13 |              1       |            22.1971 | research_main_60_tp_off    | segment_path_defer_protective |
| launch_main_25_tp_off::legacy_bar_extrema                 |     38.0046  |   5.31162  |  0.842333 |    -4.47313 | 3.14605  |       66 |               66 |              1       |            23.9804 | launch_main_25_tp_off      | legacy_bar_extrema            |
| launch_main_25_tp_off::segment_path_same_bar              |     38.0046  |   5.31162  |  0.842333 |    -4.47313 | 3.14605  |       66 |               66 |              1       |            23.9804 | launch_main_25_tp_off      | segment_path_same_bar         |
| launch_main_25_tp_off::segment_path_defer_protective      |     38.0046  |   5.31162  |  0.842333 |    -4.47313 | 3.14605  |       66 |               66 |              1       |            23.9804 | launch_main_25_tp_off      | segment_path_defer_protective |

## Experiment 2

| model                         | entry_execution_mode      | intrabar_path_mode   |   Return_pct |   Sharpe |   MaxDD_pct |      PF |   Trades |   realism_score |
|:------------------------------|:--------------------------|:---------------------|-------------:|---------:|------------:|--------:|---------:|----------------:|
| legacy_bar_extrema            | next_bar_open             | midpoint             |      45.602  | 0.977809 |    -4.32674 | 3.80459 |       66 |         6.75603 |
| legacy_bar_extrema            | next_bar_open             | midpoint             |      38.0046 | 0.842333 |    -4.47313 | 3.14605 |       66 |         5.63173 |
| legacy_bar_extrema            | next_bar_open             | pessimistic          |      45.602  | 0.977809 |    -4.32674 | 3.80459 |       66 |         6.75603 |
| legacy_bar_extrema            | next_bar_open             | pessimistic          |      38.0046 | 0.842333 |    -4.47313 | 3.14605 |       66 |         5.63173 |
| legacy_bar_extrema            | live_runner_next_5m_close | midpoint             |      40.6307 | 0.890345 |    -4.35737 | 3.41251 |       68 |         6.06373 |
| legacy_bar_extrema            | live_runner_next_5m_close | midpoint             |      34.626  | 0.775111 |    -4.50155 | 2.84226 |       69 |         5.10808 |
| legacy_bar_extrema            | live_runner_next_5m_close | pessimistic          |      40.6307 | 0.890345 |    -4.35737 | 3.41251 |       68 |         6.06373 |
| legacy_bar_extrema            | live_runner_next_5m_close | pessimistic          |      34.626  | 0.775111 |    -4.50155 | 2.84226 |       69 |         5.10808 |
| segment_path_same_bar         | next_bar_open             | midpoint             |      45.602  | 0.977809 |    -4.32674 | 3.80459 |       66 |         6.75603 |
| segment_path_same_bar         | next_bar_open             | midpoint             |      38.0046 | 0.842333 |    -4.47313 | 3.14605 |       66 |         5.63173 |
| segment_path_same_bar         | next_bar_open             | pessimistic          |      45.602  | 0.977809 |    -4.32674 | 3.80459 |       66 |         6.75603 |
| segment_path_same_bar         | next_bar_open             | pessimistic          |      38.0046 | 0.842333 |    -4.47313 | 3.14605 |       66 |         5.63173 |
| segment_path_same_bar         | live_runner_next_5m_close | midpoint             |      40.6307 | 0.890345 |    -4.35737 | 3.41251 |       68 |         6.06373 |
| segment_path_same_bar         | live_runner_next_5m_close | midpoint             |      34.626  | 0.775111 |    -4.50155 | 2.84226 |       69 |         5.10808 |
| segment_path_same_bar         | live_runner_next_5m_close | pessimistic          |      40.6307 | 0.890345 |    -4.35737 | 3.41251 |       68 |         6.06373 |
| segment_path_same_bar         | live_runner_next_5m_close | pessimistic          |      34.626  | 0.775111 |    -4.50155 | 2.84226 |       69 |         5.10808 |
| segment_path_defer_protective | next_bar_open             | midpoint             |      45.602  | 0.977809 |    -4.32674 | 3.80459 |       66 |         6.75603 |
| segment_path_defer_protective | next_bar_open             | midpoint             |      38.0046 | 0.842333 |    -4.47313 | 3.14605 |       66 |         5.63173 |
| segment_path_defer_protective | next_bar_open             | pessimistic          |      45.602  | 0.977809 |    -4.32674 | 3.80459 |       66 |         6.75603 |
| segment_path_defer_protective | next_bar_open             | pessimistic          |      38.0046 | 0.842333 |    -4.47313 | 3.14605 |       66 |         5.63173 |
| segment_path_defer_protective | live_runner_next_5m_close | midpoint             |      40.6307 | 0.890345 |    -4.35737 | 3.41251 |       68 |         6.06373 |
| segment_path_defer_protective | live_runner_next_5m_close | midpoint             |      34.626  | 0.775111 |    -4.50155 | 2.84226 |       69 |         5.10808 |
| segment_path_defer_protective | live_runner_next_5m_close | pessimistic          |      40.6307 | 0.890345 |    -4.35737 | 3.41251 |       68 |         6.06373 |
| segment_path_defer_protective | live_runner_next_5m_close | pessimistic          |      34.626  | 0.775111 |    -4.50155 | 2.84226 |       69 |         5.10808 |

## Experiment 3: Legacy Recovery

| model                         |   distance |   exit_mix_l1 |   Return_pct |    Sharpe |   Trades |   unique_entries |   avg_hold_4h_bars |
|:------------------------------|-----------:|--------------:|-------------:|----------:|---------:|-----------------:|-------------------:|
| legacy_bar_extrema            |    8.3073  |      0.710475 |     -81.5567 | -0.827118 |      821 |              539 |            15.141  |
| segment_path_same_bar         |    8.68683 |      0.685447 |     -87.2527 | -1.02177  |      815 |              548 |            14.4769 |
| segment_path_defer_protective |    8.68683 |      0.685447 |     -87.2527 | -1.02177  |      815 |              548 |            14.4769 |

## Experiment 4: Realistic Executability

| model                         |   realism_score |   Return_pct |   Sharpe |   MaxDD_pct |      PF |
|:------------------------------|----------------:|-------------:|---------:|------------:|--------:|
| legacy_bar_extrema            |         5.88989 |      39.7158 | 0.871399 |     -4.4147 | 3.30135 |
| segment_path_defer_protective |         5.88989 |      39.7158 | 0.871399 |     -4.4147 | 3.30135 |
| segment_path_same_bar         |         5.88989 |      39.7158 | 0.871399 |     -4.4147 | 3.30135 |

## Recommendations

- Daily research default: `next_bar_open + legacy_bar_extrema + midpoint + full_model`
- Stress / gate: `live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model`
- `live_runner_next_5m_close + pessimistic + full_model` 不应再作为唯一默认，应降级为 stress 口径。
- launch_optimal / research_optimal 应在新 intrabar 默认模型下重新评估。
- 在 intrabar model 校准前，参数优化应暂停。