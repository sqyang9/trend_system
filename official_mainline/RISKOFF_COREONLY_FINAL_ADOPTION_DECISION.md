# Risk-Off Core-Only Final Adoption Decision

## Decision

- Promoted official overlay:
  - `core-only Risk-Off`
  - sell-side: `EMA250`
  - re-entry: `Weekly RSI(14) <= 30 hold`
- Canonical adopted label:
  - `Formal + WRSI14_30_EMA250`

## Why This Version

It is the best balanced candidate after the full closure sequence:

- old core-only archived line
- low-value re-entry reopening
- full-stack vs core-only structure screen
- core-only sell-side EMA replacement audit

Relative to the prior formal baseline:

- default:
  - `Return 2720.25%`
  - `Calmar 2.024`
  - `MaxDD -35.07%`
- stress:
  - `Return 2876.60%`
  - `Calmar 2.089`
  - `MaxDD -34.70%`
- harsher friction:
  - `Return 2454.40%`
  - `Calmar 1.860`
  - `MaxDD -36.73%`

Interpretation:

- `EMA250 + Weekly30` gives the cleanest path efficiency
- it preserves the main upside gain while materially improving drawdown, cluster loss, and recovery burden
- it is stronger than the full-stack cash-like structure, which was rejected as unnecessary suppression

## Structure Closure

- rejected:
  - `full-stack cash-like Risk-Off`
- superseded:
  - old archived best repair `RO_EMA220_REENTRY_CLOSE_HOLD_3`
  - interim core-only incumbent `WRSI14_30_EMA220`
- retained as non-primary references:
  - `H4RSI14_10_EMA200`
  - `H4RSI14_10_EMA220`

## Official Baseline Update

The formal default portfolio is now:

- `Core BTC holding`
- `+ Sleeve #1 = ConstAddOn[1.00x]`
- `+ Sleeve #2 = RangeRotation`
- `+ core-only Risk-Off overlay`
- sell-side `EMA250`
- re-entry `Weekly RSI(14) <= 30 hold`
- approved hard total exposure cap remains `3.0x`

## Notes

- `2.5x` remains governance fallback only if cap policy tightens later.
- `4H` re-entry variants remain valid references, but they are not the adopted default.
