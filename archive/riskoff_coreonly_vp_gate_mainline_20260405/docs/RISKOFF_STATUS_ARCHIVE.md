# Risk-Off Status Archive

## Final Status

- Historical frozen line directionally valid: yes.
- Historical frozen line entered the locked baseline: no.
- Current official state of the repository: adopted official mainline includes `core-only Risk-Off overlay`.
- This file is preserved only as the archive of the older frozen pre-adoption line.
- Current latest official mainline should be read from:
  - `official_mainline/README.md`
  - `official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md`
  - `ACTIVE_MAINLINE_STATUS.md`

## Stage A: Exploratory Asset-Allocation Study

- Source files: v90_asset_management_system.py, BTC_ASSET_MANAGEMENT_SYSTEM_REPORT.md, btc_asset_management_system_report.json
- Conclusion: Exploration showed Risk-Off might materially improve the AddOn portfolio, but the result was not execution-aligned enough for formal promotion.
- caveat: The study used simplified allocation simulation plus full-sample candidate ranking, so it could not be treated as a formal baseline result.

## Stage B: Aligned Validation

- Source files: v90_asset_management_system_aligned.py, BTC_RISKOFF_ALIGNMENT_REPORT.md, btc_riskoff_alignment_report.json
- Conclusion: Risk-Off survived execution alignment and causality audit, but the evidence was only strong enough for aligned-but-preliminary status.
- result: YES. In the aligned default-tuple framework, AddOn + Risk-Off still beats AddOn-only for the locked narrow candidate set.
- evidence_level: aligned but preliminary

## Stage C: Core-Off Weight / With-Core vs No-Core

- Source files: v90_core_riskoff_level_study.py, BTC_CORE_RISKOFF_LEVEL_REPORT.md, btc_core_riskoff_level_report.json
- Conclusion: Full flat beat partial residual core, and the with-core framework remained more reasonable than a no-core switching framework.
- recommended_core_off_weight: 0.00
- with_core_vs_no_core: WITH-CORE FRAMEWORK IS MORE REASONABLE

## Stage D: Promotion V1

- Source files: v90_riskoff_promotion_validation.py, BTC_RISKOFF_PROMOTION_REPORT.md, btc_riskoff_promotion_report.json
- Conclusion: Promotion v1 failed because OOS consistency was too weak and the main blocker was bull/recovery opportunity cost, not EMA instability or causality.
- promotion_answer: NO. Risk-Off does not yet clear promotion-candidate validation.
- failure_reason: In walk-forward OOS, AddOn + Risk-Off does not beat AddOn-only consistently enough for promotion. It wins only one of three strict OOS windows.

## Stage E: Promotion V2

- Source files: v90_riskoff_promotion_v2.py, BTC_RISKOFF_PROMOTION_V2_REPORT.md, btc_riskoff_promotion_v2_report.json
- Conclusion: Two-stage repair was directionally better than flat or hysteresis, but still not good enough to clear the promotion bar.
- best_repair_candidate: Core+AddOnOverlay+RO_EMA220_TWOSTAGE_50_TO_0
- why_hysteresis_worse: Hysteresis delayed recovery without fixing the core OOS problem, so it raised opportunity cost instead of reducing it.
- why_two_stage_better: Yes. Best candidate lifts avg delta Return to -11.47pp and avg delta Calmar to -0.174 while keeping major-drawdown MaxDD improvement at +18.24pp.
- recommendation: Keep AddOn-only baseline unchanged. At most, run one final narrow promotion check on the single best repair candidate.

## Stage F: Narrow Promotion / Final Re-Entry Check

- Source files: v90_riskoff_reentry_final_check.py, v90_riskoff_reentry_last_mile.py, BTC_RISKOFF_REENTRY_LAST_MILE_REPORT.md, btc_riskoff_reentry_last_mile.json
- Conclusion: Even the best re-entry repair candidate improved the profile but still did not reach promotion-candidate strength, so promotion was frozen.
- final_key_issue: Flat-to-risk-on re-entry timing was the last material blocker after trigger and structure issues had already been narrowed down.
- best_candidate: RO_EMA220_REENTRY_CLOSE_HOLD_3
- why_still_failed: No. Evidence still does not reach promotion-candidate level.
- final_action: Stop Risk-Off promotion

## Stage G: Authorized Core Re-Entry Deep Dive

- Source files: v102_ro_reentry_structure_reaccept_stage50_100.py, v103_ro_reentry_trend_rebuild_stage50_100.py, v104_ro_reentry_trend_rebuild_full.py, v105_ro_reentry_time_plus_state_full.py and their paired audit/decision reports
- Scope: Reopen only the archived core re-entry problem, not broad Risk-Off search
- conclusion_1: `RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100` failed badly because first-step restoration was too sparse
- conclusion_2: `RO_REENTRY_TREND_REBUILD_STAGE50_100` was healthier but still not competitive enough
- conclusion_3: `RO_REENTRY_TREND_REBUILD_FULL` beat the staged trend branch, so staged restoration was effectively closed for this line
- conclusion_4: `RO_REENTRY_TIME_PLUS_STATE_FULL` did not beat `RO_REENTRY_TREND_REBUILD_FULL` and did not beat `RO_EMA220_REENTRY_CLOSE_HOLD_3`
- deep_dive_result: full-restoration variants improved internal understanding but did not solve the old opportunity-cost blocker well enough
- final_action: Re-freeze the Risk-Off re-entry deep dive

## Archive Conclusion

- Historical frozen line directionally valid: yes
- Historical frozen line entered baseline at that time: no
- Re-entry deep dive status in that historical line: completed and re-frozen
- Current repository truth is no longer this archived state
- Current latest official mainline is:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the high-churn gate earlier
  - override `Weekly RSI(14) <= 30 hold`
- Future restart prerequisites:
  - A clearly scoped new hypothesis that is not just more same-line promotion repair.
  - A clearly scoped new hypothesis that is not just more same-line re-entry repair.
  - Execution-aligned implementation under the locked default tuple.
  - A reason to expect better bull/recovery opportunity-cost control than the frozen line delivered.
  - Promotion criteria defined before re-opening the line.
- Currently forbidden Risk-Off work:
  - Continuing same-line Risk-Off promotion repair.
  - Continuing same-line Risk-Off re-entry repair.
  - Reopening Bear Short as a default extension.
  - Treating frozen Risk-Off results as active baseline conclusions.
  - Re-running broad EMA or regime-filter searches.
