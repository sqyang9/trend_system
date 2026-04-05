# Official Mainline Reproduction Manifest

## Current Latest Official Mainline

- structure:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- adopted posture:
  - `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- adopted overlay:
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - override `Weekly RSI(14) <= 30 hold`

Official headline result:

- `Return 2878.61%`
- `Calmar 2.854`
- `MaxDD -25.41%`

Overlay-level promoted result:

- `Return 2459.02%`
- `Calmar 2.352`
- `MaxDD -29.06%`

Interpretation:

- `2459.02%` is the promoted `core-only Risk-Off overlay` result
- `2878.61%` is the current latest full `official mainline` after that overlay is integrated into the formal portfolio

## Canonical Reproduction Order

1. [RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md)
2. [STATE_AWARE_HYBRID_FINAL_AUDITION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/STATE_AWARE_HYBRID_FINAL_AUDITION.md)
3. [HYBRID_PARAMETER_SCREEN.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/HYBRID_PARAMETER_SCREEN.md)
4. [PRE_MAINLINE_LANDING_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/PRE_MAINLINE_LANDING_AUDIT.md)
5. [FORMAL_MAINLINE_LAUNCH_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md)
6. [PORTFOLIO_LAYER2_WEIGHT_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md)
7. [ACTIVE_MAINLINE_STATUS.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/ACTIVE_MAINLINE_STATUS.md)
8. [WORKING_BASELINE.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/WORKING_BASELINE.md)

## Canonical Code Files

- [v121_coreonly_riskoff_sellside_ema_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v121_coreonly_riskoff_sellside_ema_audit.py)
- [v123_formal_launch_and_layer2_weight_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v123_formal_launch_and_layer2_weight_audit.py)
- [v165_state_aware_hybrid_qualification_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/v165_state_aware_hybrid_qualification_audit.py)
- [v166_state_aware_hybrid_final_audition.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/v166_state_aware_hybrid_final_audition.py)
- [v167_hybrid_parameter_screen.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/reentry_qualification_research/v167_hybrid_parameter_screen.py)
- [dashboard/signal_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/dashboard/signal_layer.py)
- [live_operating_layer/v132_live_operating_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/v132_live_operating_layer.py)
- [live_operating_layer/mainline_live_status.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/mainline_live_status.py)

## Archive Snapshot

The repository-level reproducibility snapshot for this current latest official mainline is:

- [archive/riskoff_coreonly_hybrid_mainline_20260404/README.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/archive/riskoff_coreonly_hybrid_mainline_20260404/README.md)
