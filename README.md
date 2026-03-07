# Trend System

Trend-following research and live-trading scaffold for `OKX BTC-USDT-SWAP`.

## Core Modules

- `universal_data_updater_5m.py`: OKX data fetch, incremental update, and resampling.
- `v85_intrabar_backtest.py`: 4H signal + 5m intrabar risk backtest engine.
- `v85_prelive_research_suite.py`: pre-live research gate and validation suite.
- `v85_live_strategy.py`: replay-based live target engine using the same research state machine.
- `v85_live_runner.py`: reconciliation, risk checks, and strategy-target alignment runner.
- `v85_live_execution.py`: OKX / paper execution adapters.
- `v85_state_recovery.py`: persistent local state.
- `v85_order_reconcile.py`: local / exchange reconciliation.
- `v85_risk_kill_switch.py`: runtime risk and kill-switch guard.

## Quick Start

### Update data

```bash
python universal_data_updater_5m.py --fetch --fetch_direct_tf --compare --outdir ./data
```

### Backtest

```bash
python v85_intrabar_backtest.py --data_dir ./data
```

### Pre-live research

```bash
python v85_prelive_research_suite.py --data_dir ./data --mc_n 1500
```

### Paper live runner

```bash
python v85_live_runner.py --paper --run_strategy --loop_seconds 300 --position_pct 30 --min_long_score 2 --min_short_score 4 --adx_trend_level 22
```

## Notes

- The workspace excludes local data, cache, and generated reports from git.
- The live runner can align the current position to a replay-derived strategy target.
- Exchange-native protective orders are still recommended before scaling beyond small capital.
