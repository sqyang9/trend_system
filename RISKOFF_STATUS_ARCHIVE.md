# Risk-Off Status Archive

## Final Status

- Risk-Off direction is valid: yes.
- Risk-Off is part of the locked baseline: no.
- Official state: Frozen aligned-but-preliminary direction. Not part of the locked baseline.
- Final action: Freeze Risk-Off promotion.

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

## Archive Conclusion

- Risk-Off directionally valid: yes
- Entered baseline: no
- Official status: Frozen aligned-but-preliminary direction. Not part of the locked baseline.
- Active mainline statement: The active mainline is still BTC long-only squeeze_release_20 with AddOn-only overlay semantics under the locked default tuple.
- Future restart prerequisites:
  - A clearly scoped new hypothesis that is not just more same-line promotion repair.
  - Execution-aligned implementation under the locked default tuple.
  - A reason to expect better bull/recovery opportunity-cost control than the frozen line delivered.
  - Promotion criteria defined before re-opening the line.
- Currently forbidden Risk-Off work:
  - Continuing same-line Risk-Off promotion repair.
  - Reopening Bear Short as a default extension.
  - Treating frozen Risk-Off results as active baseline conclusions.
  - Re-running broad EMA or regime-filter searches.