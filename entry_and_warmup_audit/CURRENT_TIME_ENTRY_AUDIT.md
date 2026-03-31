# Current Time Entry Audit

- Scope: determine how to onboard the adopted formal mainline at the current timestamp.
- Latest available bar: `2026-03-07 16:00:00+00:00`
- Latest state: `core_full_s1_0_s2_0`
- Latest exposures: `Core 1.00 / Sleeve1 0.00 / Sleeve2 0.00 / Total 1.00`

## Method Definitions

- `immediate_full`: deploy all capital into the mainline immediately at the current state.
- `staged_30_60`: deploy one-third now, one-third after 30 days, one-third after 60 days.
- `wait_next_switch`: stay in cash until the portfolio leaves the current state, then deploy fully.

## Current-State Analog Summary (`core_full_s1_0_s2_0` monthly starts)

| Method | Count | Avg12m | Median12m | AvgCalmar | AvgMaxDD | AvgWorst6m | AvgRecoveryDays |
| --- | --- | --- | --- | --- | --- | --- | --- |
| immediate_full | 26 | 60.30 | 21.85 | 1.050 | -27.32 | -16.29 | 116.8 |
| staged_30_60 | 26 | 51.56 | 18.42 | 0.970 | -26.57 | -16.25 | 106.8 |
| wait_next_switch | 26 | 58.43 | 20.53 | 0.918 | -27.03 | -16.29 | 116.2 |

## Recommendation

- Best current-state analog method: `immediate_full`.
- Why: highest average Calmar with current-state analogs, while preserving near-term return participation better than waiting for a switch.

## Interpretation

- This audit is not using future data from the actual latest bar; it uses historical starts that match the latest state profile.
- The latest live state is effectively `Core-only / sleeves-off`, so the key question is whether delaying capital helps when the system is already in a low-complexity investable posture.