# Risk-Off Core-Only Close3 Mainline Archive

## Scope

This archive preserves the pre-promotion mainline snapshot as of `2026-04-02`, immediately before the hybrid qualification promotion package.

It captures the repository state where:

- structure remained:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- sell-side remained:
  - `EMA250`
- implementation truth had already shifted to:
  - normal recovery `close3`
  - `weekly_rsi30_hold` as override
- governance and live docs still mostly described the older weekly-only wording

This archive exists so the old close3-era mainline can be restarted or audited later without mixing it with the promoted hybrid package.

## Directory Layout

- `docs/`
  - active status, baseline wording, architecture notes, live markdown snapshots
- `scripts/`
  - the mainline implementation files immediately before hybrid promotion
- `reports/`
  - the official mainline reports as they existed before replacement
- `plots/`
  - HTML plots from the official mainline package
- `data/`
  - tables and live JSON snapshots

## Important Note

This package intentionally preserves the pre-promotion mismatch:

- some docs still say `Weekly RSI(14) <= 30 hold`
- the actual core state machine already used `close3` as the normal recovery path

That mismatch is part of what this archive is meant to preserve for audit traceability.

## Canonical Restart Order

1. Read `docs/ACTIVE_MAINLINE_STATUS.md`
2. Read `docs/WORKING_BASELINE.md`
3. Read `scripts/v121_coreonly_riskoff_sellside_ema_audit.py`
4. Read `scripts/v123_formal_launch_and_layer2_weight_audit.py`
5. Read `reports/RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md`
6. Read `reports/FORMAL_MAINLINE_LAUNCH_AUDIT.md`
