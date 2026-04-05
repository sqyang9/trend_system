# Official Mainline Reproduction Bundle

This subdirectory is the local bundled reproduction package for the current latest official mainline.

It mirrors the essential chain preserved in:

- `official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md`
- `archive/riskoff_coreonly_vp_gate_mainline_20260405/`

Use this bundle when you want the current official mainline package to be self-contained inside `official_mainline/` without chasing files across the rest of the repository.

Current package notes:

- canonical local runtime/research data root: `dashboard/data/`
- current official atlas output: `historical_signal_atlas/output_vp_gate_mainline/`
- full trade ledger: `historical_signal_atlas/output_vp_gate_mainline/mainline_trade_ledger.csv`
- TradingView reference overlay: `historical_signal_atlas/btc_mainline_signal_overlay.pine`
- this local bundle now also contains:
  - current copied scripts in `official_mainline/reproduction/scripts/`
  - synced docs in `official_mainline/reproduction/docs/`
  - audit reports in `official_mainline/reproduction/reports/`
  - live/dashboard/json outputs in `official_mainline/reproduction/data/`
  - the 13 half-year atlas PNGs plus the full trade ledger under `official_mainline/reproduction/plots/atlas/` and `official_mainline/reproduction/data/atlas/`
