# Risk-Off Archive

## Scope

This document records the completed Risk-Off research line so that it is not accidentally reopened as if it were still an active baseline candidate.

Important distinction:

- this archive applies to the old core-only Risk-Off promotion line
- it does not invalidate the later authorized full-stack cash-like Risk-Off adoption branch
- the later branch uses different portfolio semantics and must be tracked separately from the archived core-only line

## What Was Tested

### Trigger Family

- EMA200
- EMA210
- EMA220

### Exit Structures

- full flat core
- partial residual core
- two-stage reduction

### Re-entry Repairs

- flat re-entry timing
- hold-confirm re-entry
- staged re-entry variants
- authorized full-restoration deep-dive variants

## Research Path

### 1. Exploratory Phase

Risk-Off first looked attractive in allocation-style studies because it materially improved drawdown behavior on top of AddOn.

But those results were not formal because:

- execution path was simplified
- candidate selection used full-sample ranking
- conclusions were not yet engine-aligned

### 2. Execution-Aligned Validation

The line was rebuilt under the locked execution framework.

Result:

- direction still held
- causality and execution alignment were acceptable
- evidence level became `aligned but preliminary`

### 3. Core-Off-Weight Study

This phase compared:

- full flat
- partial residual core
- with-core vs no-core

Conclusion:

- full flat was stronger than partial residual-core variants
- with-core was more reasonable than no-core switching
- this improved structural understanding, but not promotion status

### 4. Promotion V1

Promotion failed because:

- OOS consistency was not strong enough
- the real blocker was bull / recovery opportunity cost

### 5. Promotion V2

The line was narrowed to structural repairs.

Main findings:

- hysteresis was worse
- two-stage exits were more reasonable than simple flat exits
- still not enough for promotion

Best structural repair:

- `RO_EMA220_TWOSTAGE_50_TO_0`

### 6. Final Narrow Re-entry Work

Final issue identified:

- flat-to-risk-on re-entry timing was too slow

Best final candidate:

- `RO_EMA220_REENTRY_CLOSE_HOLD_3`

Even that candidate still failed promotion because:

- avg delta Calmar was still not strong enough
- recovery drag remained too large
- full promotion threshold was not crossed

### 7. Authorized Core Re-Entry Deep Dive

The line was later reopened narrowly for one question only:

- can core re-entry be improved without reopening broad Risk-Off search

Deep-dive findings:

- structure-led staged restoration failed badly because first-step restoration was too sparse
- trend-rebuild staged restoration was healthier, but still not competitive enough
- trend-rebuild full restoration beat the staged trend branch, so staged restoration was effectively closed
- time-plus-state full restoration did not beat trend-rebuild full and did not beat `RO_EMA220_REENTRY_CLOSE_HOLD_3`

Deep-dive conclusion:

- staged restoration closed
- full-restoration variants improved internal understanding
- no tested deep-dive variant beat the archived best repair
- the re-entry line was re-frozen

## Final Status

The old core-only Risk-Off line is:

- directionally valid
- execution aligned
- promotion frozen
- re-entry deep dive completed and re-frozen
- archived

Later development changed one thing:

- a new full-stack cash-like Risk-Off / re-entry branch was explicitly authorized on top of the formal portfolio
- low-value re-entry candidates `RO_LOWVALUE_WEEKLY_RSI30_HOLD` and `RO_LOWVALUE_4H_RSI10_HOLD` emerged as serious successor candidates
- the optimistic pre-adoption gate simulation was superseded
- the stricter event-level adoption work later showed:
  - full-stack cash-like Risk-Off should be rejected
  - core-only Risk-Off should be retained
  - final adopted overlay became:
    - sell-side `EMA250`
    - stable re-entry `close3`
    - high-churn re-entry `strict EMA50 + breakout_4`
    - `HV percentile >= 85` force
    - override `Weekly RSI(14) <= 30 hold`

So archive status applies to:

- the old core-only Risk-Off promotion line
- the rejected full-stack cash-like overlay line

It does not mean:

- all future Risk-Off architecture work is forbidden forever

## What This Means

Allowed:

- keep archived reports and scripts
- cite Risk-Off as completed repository history
- distinguish clearly between the archived core-only line and the later full-stack adoption candidate branch

Not allowed:

- resume the same promotion line as if it were still active
- silently treat Risk-Off as part of the working baseline
- reopen broad EMA / regime-filter searches under the same theme

Any future restart would require a genuinely new hypothesis, not more repair work on the frozen line.
