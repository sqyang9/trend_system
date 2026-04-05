# Balanced ATRVT Mainline Snapshot

## Snapshot Purpose

- This folder is the repository-level archive anchor for the current official mainline promoted on `2026-04-04`.
- It supersedes the earlier combo checkpoint while preserving the same core architecture.

## Locked Mainline

- structure:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- overlay:
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the high-churn gate earlier
  - override `Weekly RSI(14) <= 30 hold`
- sleeve scaling:
  - `S1 + S2 ATR vol-targeting`
  - `S1 = ATRVT_90D_med_035_150`
  - `S2 = ATRVT_60D_med_035_150`

## Official Headline

- `Return 3179.90%`
- `Calmar 2.872`
- `MaxDD -26.19%`

## Canonical Anchors

- [FORMAL_MAINLINE_LAUNCH_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md)
- [PORTFOLIO_LAYER2_WEIGHT_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md)
- [BALANCED_ATRVT_PROMOTION_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/BALANCED_ATRVT_PROMOTION_AUDIT.md)
- [PRE_MAINLINE_BALANCED_ATRVT_LANDING_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/system_defect_research/PRE_MAINLINE_BALANCED_ATRVT_LANDING_AUDIT.md)
- [OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md)
