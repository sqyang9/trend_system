# Risk-Off Core-Only Combo Mainline Archive

## Scope

This archive preserves the current latest official mainline package as of `2026-04-04`.

The preserved mainline is:

- `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- adopted posture:
  - `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- adopted sleeve scaling:
  - `S1 + S2 ATR vol-targeting`
- adopted overlay:
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` forces the high-churn gate earlier
  - override `Weekly RSI(14) <= 30 hold`

Important distinction:

- prior overlay-level promoted result:
  - `Return 2459.02%`
  - `Calmar 2.352`
  - `MaxDD -29.06%`
- current full official mainline result:
  - `Return 2980.07%`
  - `Calmar 3.040`
  - `MaxDD -24.16%`

## Purpose

This package exists so the latest official mainline can be restarted, audited, or handed off without reassembling files from multiple folders by memory.

It supersedes:

- `archive/riskoff_coreonly_adopted_mainline_20260328/`
- `archive/riskoff_coreonly_close3_mainline_20260402/`
- `archive/riskoff_coreonly_hybrid_mainline_20260404/`

Those older packages remain valid historical checkpoints, but they are not the current latest official mainline package.

## Directory Layout

- `docs/`
  - current repository truth and operating docs
- `scripts/`
  - core scripts used to promote and formalize the latest official mainline
- `reports/`
  - promotion, launch, and implementation audit markdown reports
- `plots/`
  - HTML plots for the official mainline and combo promotion chain
- `data/`
  - key audit tables, live outputs, and atlas summaries

## Canonical Restart Order

1. `docs/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md`
2. `reports/VOLATILITY_PROXY_FINAL_AUDITION.md`
3. `reports/VOLATILITY_PROXY_COMBO_AUDITION.md`
4. `reports/PRE_MAINLINE_COMBO_LANDING_AUDIT.md`
5. `reports/FORMAL_MAINLINE_LAUNCH_AUDIT.md`
6. `reports/PORTFOLIO_LAYER2_WEIGHT_AUDIT.md`
7. `docs/ACTIVE_MAINLINE_STATUS.md`
8. `docs/WORKING_BASELINE.md`
9. `docs/memory.md`

## Minimal Reproduction Chain

For combo promotion:

- `scripts/volatility_background.py`
- `scripts/v171_volatility_proxy_system_upgrade.py`
- `scripts/v172_volatility_proxy_final_audition.py`
- `scripts/v173_volatility_proxy_combo_audition.py`

For official mainline integration:

- `scripts/v121_coreonly_riskoff_sellside_ema_audit.py`
- `scripts/v123_formal_launch_and_layer2_weight_audit.py`

For current live interpretation:

- `scripts/v132_live_operating_layer.py`
- `scripts/mainline_live_status.py`
- `scripts/signal_layer.py`

## Current Archive Meaning

This archive is the current repository-level reproducibility checkpoint for the official mainline.
It should be treated as the current restart package unless a later official mainline package explicitly supersedes it.
