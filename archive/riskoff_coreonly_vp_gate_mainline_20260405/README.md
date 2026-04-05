# VP-Gated Mainline Snapshot

## Snapshot Purpose

- This folder is the repository-level archive anchor for the current official mainline promoted on `2026-04-05`.
- It supersedes the earlier balanced ATRVT checkpoint while preserving the same core architecture and sleeve-scaling contract.

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
- adopted `S1` gate:
  - `S1_VP_LB60_EA050_VR120`

## Official Headline

- `Return 3321.25%`
- `Sharpe 1.386`
- `Calmar 3.209`
- `MaxDD -23.81%`

## Canonical Anchors

- [FORMAL_MAINLINE_LAUNCH_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md)
- [PORTFOLIO_LAYER2_WEIGHT_AUDIT.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md)
- [VOLUME_PROFILE_PROXY_FINAL_PROMOTION_REPLAY.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/future_direction_research/VOLUME_PROFILE_PROXY_FINAL_PROMOTION_REPLAY.md)
- [OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md)

## Runtime / Reproduction Notes

- canonical local runtime/research data root: `dashboard/data/`
- official atlas output directory: `historical_signal_atlas/output_vp_gate_mainline/`
- full current-mainline trading ledger: `historical_signal_atlas/output_vp_gate_mainline/mainline_trade_ledger.csv`
- TradingView reference overlay: `historical_signal_atlas/btc_mainline_signal_overlay.pine`
- bundled local materials in this snapshot:
  - `docs/`
  - `scripts/`
  - `reports/`
  - `data/`
  - `plots/`
