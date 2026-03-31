# Project File Architecture

This file is the practical map of the repository after the current BTC adopted mainline was locked.

## 1. Root-Level State Files

These files define the current official status and should be read first before opening older research reports.

- [ACTIVE_MAINLINE_STATUS.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/ACTIVE_MAINLINE_STATUS.md)
  - shortest current-state readout
- [WORKING_BASELINE.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/WORKING_BASELINE.md)
  - official baseline, launch state, boundaries, current guidance
- [RESEARCH_HISTORY.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/RESEARCH_HISTORY.md)
  - long-form chronology of the project
- [memory.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/memory.md)
  - anti-drift memory and research rules
- [SYSTEM_ARCHITECTURE.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/SYSTEM_ARCHITECTURE.md)
  - conceptual system structure

## 2. Current Mainline Audit Files

These are the main result files supporting the present adopted BTC baseline.

- [official_mainline/README.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/README.md)
- [official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md)
- [official_mainline/RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md)
- [official_mainline/COREONLY_RISKOFF_ADOPTION_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/COREONLY_RISKOFF_ADOPTION_AUDIT.md)
- [official_mainline/COREONLY_RISKOFF_SELLSIDE_EMA_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/COREONLY_RISKOFF_SELLSIDE_EMA_AUDIT.md)
- [official_mainline/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md)
- [entry_and_warmup_audit/FORMAL_MAINLINE_ROLLING_START_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/entry_and_warmup_audit/FORMAL_MAINLINE_ROLLING_START_AUDIT.md)

## 3. Research Output Directories

These directories hold self-contained audit rounds or specialized studies.

- [archive](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/archive)
  - explicit archive packages and restartable snapshots
- [legacy_root_research](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/legacy_root_research)
  - reorganized root-level legacy process reports that are no longer part of the active read path
- [riskoff_reentry_param_audit](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/riskoff_reentry_param_audit)
  - first-layer Risk-Off signal parameter studies
- [entry_and_warmup_audit](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/entry_and_warmup_audit)
  - current-time onboarding, startup warmup, and rolling-start studies
- [official_mainline](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline)
  - official adopted mainline audit bundle
- [live_operating_layer](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer)
  - live state panel, decision memo, onboarding playbook, and fixed-frequency live status runner
- [dashboard](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/dashboard)
  - runnable operating dashboard package with explicit `data / signal / decision / output` layers and a one-click `.command` launcher
- [historical_signal_atlas](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/historical_signal_atlas)
  - historical 6-month signal atlas, TradingView overlay references, and long-span signal review outputs
- [formal_mainline_rolling_start_charts](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/formal_mainline_rolling_start_charts)
  - rolling-start chart outputs
- [eth_transfer_audit](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/eth_transfer_audit)
  - ETH transfer and BTC-flat-to-ETH switch study; currently closed/rejected
- [regime_detector_research](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/regime_detector_research)
  - isolated reserve branch for lightweight regime-layer research; not adopted
- [gravity_penalty_research](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/gravity_penalty_research)
  - isolated dynamic sizing research; reserve only
- [module_refinement_research](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/module_refinement_research)
  - isolated first-pass module cleanup screens; current screened branches are rejected
- [s2_time_stop_research](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/s2_time_stop_research)
  - isolated `S2` exit-logic research; corrected replay completed; current branch rejected
- [data](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/data)
  - market data plus local historical output folders

## 4. Core Strategy / Engine Scripts

These root-level scripts are the main reusable research engines.

- [universal_data_updater_5m.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/universal_data_updater_5m.py)
  - BTC loader / data access backbone
- [v90_addon_grading_study.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/v90_addon_grading_study.py)
  - `Sleeve #1` base engine and trade-plan generation
- [v95_range_rotation_mean_reversion_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/v95_range_rotation_mean_reversion_audit.py)
  - `Sleeve #2` logic and helper functions
- [v96_range_rotation_mean_reversion_s3_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/v96_range_rotation_mean_reversion_s3_audit.py)
  - formal portfolio system constructor
- [v121_coreonly_riskoff_sellside_ema_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/v121_coreonly_riskoff_sellside_ema_audit.py)
  - adopted Risk-Off sell-side / re-entry builder helpers
- [v123_formal_launch_and_layer2_weight_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/v123_formal_launch_and_layer2_weight_audit.py)
  - launch and layer-2 posture constructor for the current adopted baseline

## 5. Visual / Review Outputs

These files are useful for quick review rather than for logic derivation.

- [MULTI_SLEEVE_VISUALIZATION_MVP.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/MULTI_SLEEVE_VISUALIZATION_MVP.md)
- [MULTI_SLEEVE_VISUALIZATION_MVP_CHARTS.html](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/MULTI_SLEEVE_VISUALIZATION_MVP_CHARTS.html)
- [official_mainline/PORTFOLIO_LAYER2_WEIGHT_PLOTS.html](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/PORTFOLIO_LAYER2_WEIGHT_PLOTS.html)
- [historical_signal_atlas/output/historical_signal_atlas_overview.html](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/historical_signal_atlas/output/historical_signal_atlas_overview.html)
- [dashboard/output/current_signal_latest.png](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/dashboard/output/current_signal_latest.png)

## 6. Practical Read Order

If another developer needs to restart quickly, the shortest path is:

1. [ACTIVE_MAINLINE_STATUS.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/ACTIVE_MAINLINE_STATUS.md)
2. [WORKING_BASELINE.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/WORKING_BASELINE.md)
3. [memory.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/memory.md)
4. [official_mainline/RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md)
5. [official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md)
6. [official_mainline/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md)
7. [entry_and_warmup_audit/CURRENT_TIME_ENTRY_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/entry_and_warmup_audit/CURRENT_TIME_ENTRY_AUDIT.md)
8. [entry_and_warmup_audit/WARMUP_STARTUP_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/entry_and_warmup_audit/WARMUP_STARTUP_AUDIT.md)
9. [entry_and_warmup_audit/FORMAL_MAINLINE_ROLLING_START_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/entry_and_warmup_audit/FORMAL_MAINLINE_ROLLING_START_AUDIT.md)
10. [live_operating_layer/LIVE_STATE_PANEL.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/LIVE_STATE_PANEL.md)
11. [live_operating_layer/LIVE_DECISION_MEMO.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/LIVE_DECISION_MEMO.md)
12. [live_operating_layer/STARTUP_ONBOARDING_PLAYBOOK.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/STARTUP_ONBOARDING_PLAYBOOK.md)
13. [live_operating_layer/MAINLINE_LIVE_STATUS_USAGE.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/MAINLINE_LIVE_STATUS_USAGE.md)

## 6A. Current Adopted Running Posture

- mainline structure:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- adopted posture:
  - `Core 0.75 / Sleeve1 1.25 / Sleeve2 1.00`
- superseded prior posture:
  - `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`

## 7. Current Closed / Non-Mainline Branches

These exist in the repo but should not be treated as active workstreams.

- old `v85` long+short
- archived old Risk-Off re-entry line
- rejected full-stack Risk-Off architecture
- closed `Sleeve #3` reset screening line
- rejected ETH switch line
- rejected first-pass `module_refinement_research` branches
- rejected corrected `S2` time/progress stop branch

## 8. Current Git Archiving Guidance

If the repo is prepared for a careful GitHub update, the cleanest first upload scope should prioritize:

1. root-level state files
2. current adopted mainline audit files
3. adopted archive snapshot under `archive/`
4. live operating package under `live_operating_layer/`
5. runnable `dashboard/`
6. onboarding / warmup / rolling-start support studies

Do not mix these with reserve or rejected isolated research unless the commit explicitly states that it is uploading full research history.
