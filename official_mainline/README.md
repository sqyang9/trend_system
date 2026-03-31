# Official Mainline Folder

This directory contains the current adopted BTC mainline's primary audit and decision files.

Current adopted baseline:

- `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- adopted posture:
  - `Core 0.75 / Sleeve1 1.25 / Sleeve2 1.00`
- sell-side:
  - `EMA250`
- re-entry:
  - `Weekly RSI(14) <= 30 hold`
- launch state:
  - `LAUNCH_GO`

Read order:

1. `RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md`
2. `FORMAL_MAINLINE_LAUNCH_AUDIT.md`
3. `COREONLY_RISKOFF_ADOPTION_AUDIT.md`
4. `COREONLY_RISKOFF_SELLSIDE_EMA_AUDIT.md`
5. `PORTFOLIO_LAYER2_WEIGHT_AUDIT.md`

This folder is meant to keep the current mainline easy to review without mixing in older root-level legacy reports.
