# GitHub Upload Checklist Pass 1

## Goal

Prepare a cautious first GitHub archive push for the current adopted BTC mainline without mixing in reserve branches, rejected research, or local cache noise.

## Target Branch

- `codex/mainline-archive-pass1`

## Include In Pass 1

### Root State / Index Files

- `ACTIVE_MAINLINE_STATUS.md`
- `WORKING_BASELINE.md`
- `RESEARCH_HISTORY.md`
- `memory.md`
- `PROJECT_FILE_ARCHITECTURE.md`
- `SYSTEM_ARCHITECTURE.md`
- `MAINLINE_GITHUB_ARCHIVE_SCOPE.md`

### Official Mainline Bundle

- `official_mainline/`
  - `README.md`
  - `FORMAL_MAINLINE_LAUNCH_AUDIT.md`
  - `RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md`
  - `COREONLY_RISKOFF_ADOPTION_AUDIT.md`
  - `COREONLY_RISKOFF_ADOPTION_PLOTS.html`
  - `COREONLY_RISKOFF_SELLSIDE_EMA_AUDIT.md`
  - `COREONLY_RISKOFF_SELLSIDE_EMA_PLOTS.html`
  - `PORTFOLIO_LAYER2_WEIGHT_AUDIT.md`
  - `PORTFOLIO_LAYER2_WEIGHT_TABLE.csv`
  - `PORTFOLIO_LAYER2_WEIGHT_PLOTS.html`

### Entry / Warmup / Rolling Start

- `entry_and_warmup_audit/`
  - `CURRENT_TIME_ENTRY_AUDIT.md`
  - `CURRENT_TIME_ENTRY_TABLE.csv`
  - `WARMUP_STARTUP_AUDIT.md`
  - `WARMUP_STARTUP_TABLE.csv`
  - `FORMAL_MAINLINE_ROLLING_START_AUDIT.md`
  - `FORMAL_MAINLINE_ROLLING_START_TABLE.csv`
  - `CURRENT_ENTRY_AND_WARMUP_PLOTS.html`
  - `current_entry_and_warmup_audit.json`
  - `formal_mainline_rolling_start_summary.json`
  - `v131_current_entry_and_warmup_audit.py`

### Live Operating Package

- `live_operating_layer/`
- `dashboard/`
- `historical_signal_atlas/`

### Restart Snapshot

- `archive/riskoff_coreonly_adopted_mainline_20260328/`

### Required Engine / Builder Scripts

- `universal_data_updater_5m.py`
- `v90_addon_grading_study.py`
- `v95_range_rotation_mean_reversion_audit.py`
- `v96_range_rotation_mean_reversion_s3_audit.py`
- `v120_coreonly_riskoff_adoption_audit.py`
- `v121_coreonly_riskoff_sellside_ema_audit.py`
- `v122_formal_launch_and_weight_audit.py`
- `v123_formal_launch_and_layer2_weight_audit.py`
- `v127_formal_mainline_rolling_start_audit.py`

## Exclude From Pass 1

### Reserve / Rejected Research

- `regime_detector_research/`
- `gravity_penalty_research/`
- `module_refinement_research/`
- `s2_time_stop_research/`
- `eth_transfer_audit/`
- `legacy_root_research/`

### Local Cache / Temp / Packaging Noise

- `.fontconfig/`
- `.mplcache/`
- `__pycache__/`
- `_zip_compare/`
- `trend_system_v1.0.zip`
- any `.DS_Store`
- any directory-local `__pycache__/`

### Not Needed In First Mainline Archive

- superseded full-stack Risk-Off files
- old root-level process reports that now live under `legacy_root_research/`
- reserve-only isolated challengers

## Current Readiness Notes

- mainline state docs are updated
- official mainline files are regrouped under `official_mainline/`
- rolling-start support files are regrouped under `entry_and_warmup_audit/`
- operating layer exists and is runnable
- historical atlas exists and is browsable
- root directory is cleaner, but still contains older research families not intended for pass 1

## Pass 1 Staging Rule

Only stage files required to:

1. explain the adopted baseline
2. reproduce the adopted baseline
3. operate the adopted baseline
4. restart the adopted baseline later

If a file only explains a rejected or reserve branch, leave it out of pass 1.
