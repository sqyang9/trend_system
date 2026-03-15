# Risk-Off Archive

## Scope

This document records the completed Risk-Off research line so that it is not accidentally reopened as if it were still an active baseline candidate.

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

## Final Status

Risk-Off is:

- directionally valid
- execution aligned
- promotion frozen
- archived

## What This Means

Allowed:

- keep archived reports and scripts
- cite Risk-Off as completed repository history

Not allowed:

- resume the same promotion line as if it were still active
- silently treat Risk-Off as part of the working baseline
- reopen broad EMA / regime-filter searches under the same theme

Any future restart would require a genuinely new hypothesis, not more repair work on the frozen line.
