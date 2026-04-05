# Official Mainline Folder

This directory contains the current latest adopted BTC mainline's primary audit, decision, and reproduction-reference files.

Current adopted baseline:

- `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- adopted posture:
  - `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- sleeve scaling:
  - `S1 + S2 ATR vol-targeting`
- sell-side:
  - `EMA250`
- stable normal re-entry:
  - `close3`
- high-churn normal re-entry:
  - `strict EMA50 + breakout_4`
- high-churn forcing:
  - `HV percentile >= 85`
- override re-entry:
  - `Weekly RSI(14) <= 30 hold`
- launch state:
  - `LAUNCH_GO`
- current latest official mainline headline result:
  - `Return 2980.07%`
  - `Calmar 3.040`
  - `MaxDD -24.16%`

This is the current latest mainline for the repository.
The earlier hybrid-only `core-only Risk-Off overlay` promotion result:

- `Return 2459.02%`
- `Calmar 2.352`
- `MaxDD -29.06%`

is the adopted overlay-level result, not the final full portfolio headline.

Read order:

1. `OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md`
2. `FORMAL_MAINLINE_LAUNCH_AUDIT.md`
3. `PORTFOLIO_LAYER2_WEIGHT_AUDIT.md`
4. `../system_defect_research/VOLATILITY_PROXY_FINAL_AUDITION.md`
5. `../system_defect_research/VOLATILITY_PROXY_COMBO_AUDITION.md`
6. `../system_defect_research/PRE_MAINLINE_COMBO_LANDING_AUDIT.md`
7. `RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md`

The prior pre-hybrid mainline package has been snapshotted to:

- `archive/riskoff_coreonly_close3_mainline_20260402/`

The superseded hybrid-without-volatility package is snapshotted to:

- `archive/riskoff_coreonly_hybrid_mainline_20260404/`

The current latest official mainline package is snapshotted to:

- `archive/riskoff_coreonly_combo_mainline_20260404/`

This folder is meant to keep the current mainline easy to review without mixing in older root-level legacy reports.
