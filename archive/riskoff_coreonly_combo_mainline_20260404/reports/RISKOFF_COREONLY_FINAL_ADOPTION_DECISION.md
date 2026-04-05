# Risk-Off Core-Only Final Adoption Decision

## Decision

- Promoted official overlay:
  - `core-only Risk-Off`
  - sell-side `EMA250`
  - stable normal re-entry `close3`
  - high-churn normal re-entry `strict EMA50 + breakout_4`
  - override `Weekly RSI(14) <= 30 hold`
- Canonical adopted label:
  - `Formal + EMA250_CLOSE3_HC23_STRICT_BREAKOUT4`

## Why This Version

This promotion closes the re-entry qualification line.

- The sell-side did not need replacement.
- The real problem was bad full re-entry qualification in high-churn windows.
- `state-aware strict` proved the environment diagnosis.
- `high churn -> strict AND breakout_4` is the first challenger that beat both:
  - the mainline `baseline close3`
  - the standing reference `state-aware strict`

## Promotion Evidence

Default:

- mainline baseline close3:
  - `Return 2329.48%`
  - `Calmar 2.129`
  - `MaxDD -31.45%`
- promoted challenger:
  - `Return 2459.02%`
  - `Calmar 2.352`
  - `MaxDD -29.06%`

Stress / harsh:

- stress delta vs mainline:
  - `dReturn +111.91pp`
  - `dCalmar +0.248`
  - `dMaxDD +2.68pp`
- harsh friction delta vs mainline:
  - `dReturn +164.69pp`
  - `dCalmar +0.245`
  - `dMaxDD +2.86pp`

Churn:

- full-sample quick re-FLAT 14d:
  - `59.6% -> 44.7%`
- high-churn quick re-FLAT 14d:
  - `58.5% -> 31.8%`
- high-churn quick re-FLAT 30d:
  - `75.6% -> 54.5%`

## Parameter Closure

The lightweight parameter screen kept only two tunable dimensions:

- breakout window length
- high-churn trigger thresholds

Result:

- current promotion point `HC 2/3 + breakout_4` remained the screen winner
- no stronger practical replacement appeared in that local grid

## Official Baseline Update

The formal default portfolio remains:

- `Core BTC holding`
- `+ Sleeve #1 = ConstAddOn[1.00x]`
- `+ Sleeve #2 = RangeRotation`
- `+ core-only Risk-Off overlay`
- adopted posture `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`
- approved hard total exposure cap `3.0x`

The updated core overlay is:

- sell-side `EMA250`
- stable normal re-entry `close3`
- high-churn normal re-entry `strict EMA50 + breakout_4`
- override `Weekly RSI(14) <= 30 hold`

## Archive And Traceability

- The previous pre-hybrid mainline snapshot is archived in:
  - `archive/riskoff_coreonly_close3_mainline_20260402/`
- The final research chain for this promotion is:
  - `reentry_qualification_research/STATE_AWARE_HYBRID_FINAL_AUDITION.md`
  - `reentry_qualification_research/HYBRID_PARAMETER_SCREEN.md`
  - `reentry_qualification_research/PRE_MAINLINE_LANDING_AUDIT.md`
