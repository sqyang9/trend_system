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
- Sleeve #2 action markers: `S2B`, `S2S`
- matching 6-month equity curve

Main generator:

- `generate_historical_signal_atlas.py`

Outputs:

- `output/*.png`
- `output/atlas_index.csv`
- `output/atlas_summary.md`
