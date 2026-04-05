# Mainline Live Status Usage

Run the fixed-frequency status script after each `4h` bar close.

## Command

```bash
python live_operating_layer/mainline_live_status.py \
  --account-equity 1000 \
  --current-notional 720
```

Optional:

```bash
python live_operating_layer/mainline_live_status.py \
  --account-equity 1000 \
  --current-notional 720 \
  --symbol "BTCUSDT perpetual" \
  --tolerance-usdt 5
```

## Output

Each run writes:

- `live_operating_layer/MAINLINE_LIVE_STATUS.md`
- `live_operating_layer/mainline_live_status.json`

And prints the same status payload to stdout.

## What It Reports

1. Current state
2. Current target exposure
3. Target notional by layer and in total
4. Rebalance instruction versus current actual notional

## Scheduling

- Recommended frequency: `every 4h bar close`
- Reason: the adopted mainline is already organized around `4h` state updates
- Weekly RSI is automatically handled inside the same `4h` refresh cycle
