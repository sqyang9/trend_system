# V85 Live Kernel (P0)

This workspace now includes a live-trading kernel scaffold plus a strategy-target runner:

- `v85_live_execution.py`: exchange adapters
  - `CCXTOKXExecutionAdapter` for OKX
  - `PaperExecutionAdapter` for local rehearsals
- `v85_state_recovery.py`: JSON state persistence and startup recovery
- `v85_order_reconcile.py`: local/exchange reconciliation loop
- `v85_risk_kill_switch.py`: runtime risk checks and kill-switch
- `v85_live_runner.py`: one-shot or loop runner for reconcile/risk/strategy alignment/order path
- `v85_live_strategy.py`: replay-based live target engine reusing the research state machine
- `v85_live_smoke_test.py`: offline smoke test

## Quick Start (offline)

```bash
python v85_live_smoke_test.py
python v85_live_runner.py --paper --send_test_order --test_order_price 100000 --test_order_amount 0.002
python v85_live_runner.py --paper --run_strategy --signal_only --position_pct 30 --min_long_score 2 --min_short_score 4 --adx_trend_level 22
python v85_live_runner.py --paper --run_strategy --position_pct 30 --min_long_score 2 --min_short_score 4 --adx_trend_level 22
```

## Quick Start (OKX, dry run)

Set credentials:

- `OKX_API_KEY`
- `OKX_API_SECRET`
- `OKX_API_PASSWORD`

Then run:

```bash
python v85_live_runner.py --dry_run --send_test_order --test_order_type market --test_order_amount 0.001
```

## Notes

- The runner can now replay the research state machine and align the live position to the current strategy target.
- The default live profile is conservative: `position_pct=30`, `min_long_score=2`, `min_short_score=4`, `adx_trend_level=22`, and `allow_short=false` unless explicitly enabled.
- Intrabar exits are reproduced by replaying the 5m path every cycle; exchange-native protective orders are still a recommended next hardening step before full production size.
- State file defaults to `./data/live_state.json`.

