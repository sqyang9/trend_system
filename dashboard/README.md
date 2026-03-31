# Dashboard Package

This folder is a runnable operating package for the adopted BTC mainline.

Layers:

- `data_layer.py`
- `signal_layer.py`
- `decision_layer.py`
- `output_layer.py`
- `run_dashboard.py`

One-click launcher:

- `run_mainline_dashboard.command`

Runtime config:

- `dashboard_config.json`

Local dashboard data:

- `data/`
- first run bootstraps from repo-level BTC csv files
- later runs strictly refresh local BTC data before rendering
- refreshed timeframes:
  - `5m`
  - `1h`
  - `4h`
  - `1d`
- funding is intentionally not fetched or displayed in the dashboard

Generated outputs:

- `output/current_signal_<timestamp>.png`
- `output/current_signal_latest.png`
- `output/current_signal.json`
- `output/current_signal.md`

Default operating assumption:

- current actual notional defaults to `0`
- this package therefore answers: if starting flat now, what notional should be held

Strict runtime rule:

- data refresh must succeed before PNG generation
- if refresh fails, the run should error out instead of silently using stale data
