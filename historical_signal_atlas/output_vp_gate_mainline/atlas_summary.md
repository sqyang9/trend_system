# Historical Signal Atlas Summary

- windows rendered: `13`
- first start: `2019-12-16 04:00:00+00:00`
- last end: `2026-03-30 20:00:00+00:00`

## Outputs

- index: `atlas_index.csv`
- trade ledger: `mainline_trade_ledger.csv`
- png files: `output_vp_gate_mainline/*.png`

## Notes

- Each PNG covers a 6-month 4h window.
- Equity is rebased to 100 at each window start.
- Core flat spans are shaded grey.
- High-churn spans are shaded light amber.
- Core restore is marked `RE`; core flattening is marked `FLAT`.
- Sleeve markers use text labels: `S1B`, `S1S`, `S1X`, `S2B`, `S2S`.
- `S1X` means a breakout candidate existed but the active `S1 gate` blocked execution.
- `mainline_trade_ledger.csv` contains the full current-mainline trading record: core rebalances plus executed S1/S2 round trips.