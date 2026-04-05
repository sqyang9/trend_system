# Official Mainline Folder

This directory contains the current latest adopted BTC mainline's primary audit, decision, and reproduction-reference files.

Current adopted baseline:

- `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- adopted posture:
  - `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- sell-side:
  - `EMA250`
- stable normal re-entry:
  - `close3`
- high-churn normal re-entry:
  - `strict EMA50 + breakout_4`
- override re-entry:
  - `Weekly RSI(14) <= 30 hold`
- launch state:
  - `LAUNCH_GO`
- current latest official mainline headline result:
  - `Return 2878.61%`
  - `Calmar 2.854`
  - `MaxDD -25.41%`

This is the current latest mainline for the repository.
The earlier `core-only Risk-Off overlay` promotion result:

- `Return 2459.02%`
- `Calmar 2.352`
- `MaxDD -29.06%`

is the adopted overlay-level result, not the final full portfolio headline.

Read order:

1. `OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md`
2. `RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md`
3. `FORMAL_MAINLINE_LAUNCH_AUDIT.md`
4. `../reentry_qualification_research/STATE_AWARE_HYBRID_FINAL_AUDITION.md`
5. `../reentry_qualification_research/HYBRID_PARAMETER_SCREEN.md`
6. `../reentry_qualification_research/PRE_MAINLINE_LANDING_AUDIT.md`

The prior pre-hybrid mainline package has been snapshotted to:

- `archive/riskoff_coreonly_close3_mainline_20260402/`

The current latest official mainline package is snapshotted to:

- `archive/riskoff_coreonly_hybrid_mainline_20260404/`

This folder is meant to keep the current mainline easy to review without mixing in older root-level legacy reports.
