# Historical Signal Atlas

This folder contains a standalone image-research package for the adopted BTC mainline.

Scope:

- use the current adopted mainline signal semantics
- replay the full historical state path from the earliest available 4h bar
- split the history into 6-month windows
- render one PNG per window

Each chart includes:

- 6 months of 4h candles
- EMA250
- core flat regions
- core re-entry / restore markers
- Sleeve #1 action markers: `S1B`, `S1S`
- Sleeve #1 candidate blocked markers: `S1X`
- Sleeve #2 action markers: `S2B`, `S2S`
- matching 6-month equity curve

Main generator:

- `generate_historical_signal_atlas.py`

Outputs:

- `output_vp_gate_mainline/*.png`
- `output_vp_gate_mainline/atlas_index.csv`
- `output_vp_gate_mainline/atlas_summary.md`
- `output_vp_gate_mainline/mainline_trade_ledger.csv`

Notes:

- the atlas follows the promoted `S1_VP_LB60_EA050_VR120` mainline package
- the canonical local data root for atlas generation is `dashboard/data/`
- `mainline_trade_ledger.csv` is the full from-inception trading ledger for the current latest `3321.25%` official mainline
