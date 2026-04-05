# Official Mainline Reproduction Manifest

## Current Latest Official Mainline

- structure:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- adopted posture:
  - `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- sleeve scaling:
  - `S1 + S2 ATR vol-targeting`
  - `S1 = ATRVT_90D_med_035_150`
  - `S2 = ATRVT_60D_med_035_150`
- adopted `S1` gate:
  - `S1_VP_LB60_EA050_VR120`
- adopted overlay:
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the high-churn gate earlier
  - override `Weekly RSI(14) <= 30 hold`

Official headline result:

- `Return 3321.25%`
- `Sharpe 1.386`
- `Calmar 3.209`
- `MaxDD -23.81%`
- canonical local runtime/research data root: `dashboard/data/`
- canonical atlas output: `historical_signal_atlas/output_vp_gate_mainline/`
- canonical full trade ledger: `historical_signal_atlas/output_vp_gate_mainline/mainline_trade_ledger.csv`
- TradingView reference overlay: `historical_signal_atlas/btc_mainline_signal_overlay.pine`

Prior overlay-level promoted result:

- `Return 2459.02%`
- `Calmar 2.352`
- `MaxDD -29.06%`

Interpretation:

- `2459.02%` is the promoted `core-only Risk-Off overlay` result
- `3321.25%` is the current latest full `official mainline` after the later `S1 volume-profile proxy gate` promotion is integrated into the formal portfolio

## Canonical Reproduction Order

1. [VOLATILITY_PROXY_FINAL_AUDITION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/VOLATILITY_PROXY_FINAL_AUDITION.md)
2. [VOLATILITY_PROXY_COMBO_AUDITION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/VOLATILITY_PROXY_COMBO_AUDITION.md)
3. [PRE_MAINLINE_COMBO_LANDING_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/PRE_MAINLINE_COMBO_LANDING_AUDIT.md)
4. [BALANCED_ATRVT_PROMOTION_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/BALANCED_ATRVT_PROMOTION_AUDIT.md)
5. [PRE_MAINLINE_BALANCED_ATRVT_LANDING_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/PRE_MAINLINE_BALANCED_ATRVT_LANDING_AUDIT.md)
6. [PRE_MAINLINE_VOLUME_PROFILE_PROXY_LANDING_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/future_direction_research/PRE_MAINLINE_VOLUME_PROFILE_PROXY_LANDING_AUDIT.md)
7. [VOLUME_PROFILE_PROXY_FINAL_PROMOTION_REPLAY.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/future_direction_research/VOLUME_PROFILE_PROXY_FINAL_PROMOTION_REPLAY.md)
8. [FORMAL_MAINLINE_LAUNCH_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md)
9. [PORTFOLIO_LAYER2_WEIGHT_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md)
10. [ACTIVE_MAINLINE_STATUS.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/ACTIVE_MAINLINE_STATUS.md)
11. [WORKING_BASELINE.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/WORKING_BASELINE.md)
12. [RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md)

## Canonical Code Files

- [v121_coreonly_riskoff_sellside_ema_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v121_coreonly_riskoff_sellside_ema_audit.py)
- [volatility_background.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/volatility_background.py)
- [canonical_market_data.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/canonical_market_data.py)
- [v123_formal_launch_and_layer2_weight_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v123_formal_launch_and_layer2_weight_audit.py)
- [v171_volatility_proxy_system_upgrade.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/v171_volatility_proxy_system_upgrade.py)
- [v172_volatility_proxy_final_audition.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/v172_volatility_proxy_final_audition.py)
- [v173_volatility_proxy_combo_audition.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/v173_volatility_proxy_combo_audition.py)
- [v183_balanced_atrvt_promotion_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/v183_balanced_atrvt_promotion_audit.py)
- [s1_gate_background.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/s1_gate_background.py)
- [v189_volume_profile_proxy_final_promotion_replay.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/future_direction_research/v189_volume_profile_proxy_final_promotion_replay.py)
- [dashboard/signal_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/dashboard/signal_layer.py)
- [live_operating_layer/v132_live_operating_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/v132_live_operating_layer.py)
- [live_operating_layer/mainline_live_status.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/mainline_live_status.py)
- [historical_signal_atlas/generate_historical_signal_atlas.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/historical_signal_atlas/generate_historical_signal_atlas.py)

## Archive Snapshot

The repository-level reproducibility snapshot for this current latest official mainline is:

- [archive/riskoff_coreonly_vp_gate_mainline_20260405/README.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/archive/riskoff_coreonly_vp_gate_mainline_20260405/README.md)

The immediately prior official package remains available as a historical checkpoint:

- [archive/riskoff_coreonly_balanced_atrvt_mainline_20260404/README.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/archive/riskoff_coreonly_balanced_atrvt_mainline_20260404/README.md)
- [archive/riskoff_coreonly_combo_mainline_20260404/README.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/archive/riskoff_coreonly_combo_mainline_20260404/README.md)
- [archive/riskoff_coreonly_hybrid_mainline_20260404/README.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/archive/riskoff_coreonly_hybrid_mainline_20260404/README.md)
