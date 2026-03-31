# Risk-Off Core-Only Adopted Mainline Archive

## Scope

This archive package preserves the full reproducibility chain for the adopted BTC mainline as of `2026-03-28`:

- formal portfolio base:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation`
- adopted overlay:
  - `core-only Risk-Off`
  - sell-side `EMA250`
  - re-entry `Weekly RSI(14) <= 30 hold`
- approved hard total exposure cap:
  - `3.0x`

The purpose of this archive is to let later development restart from the exact adopted branch without reopening rejected full-stack or older archived Risk-Off lines by accident.

## Directory Layout

- `docs/`
  - state snapshots and final decision documents
- `scripts/`
  - core scripts used to discover, screen, audit, and finalize the adopted overlay
- `reports/`
  - markdown reports for the main audit chain
- `plots/`
  - HTML comparison charts
- `data/`
  - machine-readable audit outputs and parameter table

## Canonical Restart Order

1. Read `docs/RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md`
2. Read `docs/WORKING_BASELINE.md`
3. Read `reports/COREONLY_RISKOFF_ADOPTION_AUDIT.md`
4. Read `reports/COREONLY_RISKOFF_SELLSIDE_EMA_AUDIT.md`
5. Use `scripts/v120_coreonly_riskoff_adoption_audit.py`
6. Use `scripts/v121_coreonly_riskoff_sellside_ema_audit.py`

This sequence reconstructs:

- why full-stack cash-like Risk-Off was rejected
- why core-only was retained
- why `Weekly RSI30` won the main branch
- why `EMA250` replaced `EMA220`

## Weekly And 4H Branches

### Adopted Weekly Branch

- label: `Formal + WRSI14_30_EMA250`
- status: adopted official default overlay
- interpretation:
  - best balanced candidate
  - strongest path efficiency
  - best official mainline replacement value

### Secondary 4H Branch

- label: `Formal + H4RSI14_10_EMA200`
- status: non-primary reference branch
- interpretation:
  - valid and strong
  - more aggressive
  - not the adopted default

## File Roles

### Discovery / First-Layer Re-Entry Ecology

- `scripts/v110_riskoff_lowvalue_reentry_candidates.py`
- `reports/RISK_OFF_LOWVALUE_REENTRY_REPORT.md`
- `plots/RISK_OFF_LOWVALUE_REENTRY_EQUITY_CURVES.html`

These files establish that the oversold / low-value re-entry ecology is a real successor direction and identify the serious weekly / 4h candidates.

### Parameter Layer

- `scripts/v118_riskoff_reentry_signal_param_audit.py`
- `reports/RISKOFF_REENTRY_SIGNAL_PARAM_REPORT.md`
- `plots/RISKOFF_REENTRY_SIGNAL_PARAM_PLOTS.html`
- `data/RISKOFF_REENTRY_SIGNAL_PARAM_TABLE.csv`

These files lock the main re-entry family neighborhood:

- weekly incumbent:
  - `WRSI14_30`
- 4h incumbent:
  - `H4RSI14_10`

### Structure Screen

- `scripts/v119_riskoff_structure_screen.py`
- `reports/RISKOFF_STRUCTURE_SCREEN.md`
- `plots/RISKOFF_STRUCTURE_SCREEN_PLOTS.html`
- `data/riskoff_structure_screen.json`

These files answer the architecture question:

- `core-only Risk-Off` is the correct retained structure
- `full-stack cash-like Risk-Off` is rejected

### Final Core-Only Adoption Audit

- `scripts/v120_coreonly_riskoff_adoption_audit.py`
- `reports/COREONLY_RISKOFF_ADOPTION_AUDIT.md`
- `plots/COREONLY_RISKOFF_ADOPTION_PLOTS.html`
- `data/coreonly_riskoff_adoption_audit.json`

These files provide the full adoption audit for the retained core-only structure under:

- `default`
- `stress`
- `harsher friction`

### Sell-Side EMA Replacement Audit

- `scripts/v121_coreonly_riskoff_sellside_ema_audit.py`
- `reports/COREONLY_RISKOFF_SELLSIDE_EMA_AUDIT.md`
- `plots/COREONLY_RISKOFF_SELLSIDE_EMA_PLOTS.html`
- `data/coreonly_riskoff_sellside_ema_audit.json`

These files settle the first-layer sell-side replacement question:

- weekly branch:
  - `EMA250` beats `EMA220`
- 4h branch:
  - `EMA200` beats `EMA220`

## State Snapshot Files

The following files preserve the repository-level state at the moment the branch was closed:

- `docs/ACTIVE_MAINLINE_STATUS.md`
- `docs/WORKING_BASELINE.md`
- `docs/RESEARCH_HISTORY.md`
- `docs/memory.md`
- `docs/RISKOFF_ARCHIVE.md`
- `docs/RISKOFF_COREONLY_FINAL_ADOPTION_DECISION.md`

## Explicitly Superseded Or Rejected

Do not treat the following as final evidence for this archive package:

- optimistic `v115` full-stack gate simulation
- rejected full-stack cash-like Risk-Off architecture
- old archived best repair `RO_EMA220_REENTRY_CLOSE_HOLD_3`
- interim weekly incumbent `WRSI14_30_EMA220`

## Final Archived Conclusion

The adopted mainline preserved here is:

- `Core BTC holding`
- `+ ConstAddOn[1.00x]`
- `+ RangeRotation`
- `+ core-only Risk-Off overlay`
- sell-side `EMA250`
- re-entry `Weekly RSI(14) <= 30 hold`
- hard total exposure cap `3.0x`
