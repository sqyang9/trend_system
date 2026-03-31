# Mainline GitHub Archive Scope

## Purpose

This file defines the safest first GitHub upload scope for the currently adopted BTC mainline.

The goal is not to upload every historical experiment at once.
The goal is to upload a clean, defensible package that preserves:

- the adopted baseline
- the official supporting audits
- the operating layer
- the minimum archive needed for future restart

## Recommended First Upload Scope

### 1. Root State Files

- `ACTIVE_MAINLINE_STATUS.md`
- `WORKING_BASELINE.md`
- `RESEARCH_HISTORY.md`
- `memory.md`
- `PROJECT_FILE_ARCHITECTURE.md`
- `SYSTEM_ARCHITECTURE.md`

### 2. Adopted Mainline Audit Files

- `official_mainline/`

### 3. Adopted Mainline Supporting Studies

- `entry_and_warmup_audit/`
- `formal_mainline_rolling_start_charts/`
- `entry_and_warmup_audit/FORMAL_MAINLINE_ROLLING_START_AUDIT.md`
- `entry_and_warmup_audit/FORMAL_MAINLINE_ROLLING_START_TABLE.csv`

### 4. Live Operating Package

- `live_operating_layer/`
- `dashboard/`
- `historical_signal_atlas/`

### 5. Adopted Archive Snapshot

- `archive/riskoff_coreonly_adopted_mainline_20260328/`

### 6. Required Engine / Builder Scripts

- `universal_data_updater_5m.py`
- `v90_addon_grading_study.py`
- `v95_range_rotation_mean_reversion_audit.py`
- `v96_range_rotation_mean_reversion_s3_audit.py`
- `v121_coreonly_riskoff_sellside_ema_audit.py`
- `v123_formal_launch_and_layer2_weight_audit.py`
- direct helper files these depend on, when those helpers are not already on GitHub

## Recommended Exclusions For First Upload

Do not mix these into the first archive commit unless the intent is explicitly “upload full research history”.

- `regime_detector_research/`
- `gravity_penalty_research/`
- `module_refinement_research/`
- `s2_time_stop_research/`
- `eth_transfer_audit/`
- `legacy_root_research/`
- superseded full-stack Risk-Off exploratory files
- temporary cache directories such as `.fontconfig/`
- local zip bundles and one-off export artifacts

## Commit Strategy

Recommended sequence:

1. state files + architecture docs
2. adopted mainline audits
3. live operating package
4. archive snapshot
5. optional reserve / rejected research branches later

## One-Line Rule

If a file is not needed to explain, reproduce, operate, or restart the adopted mainline, it should not be in the first cautious GitHub archive push.
