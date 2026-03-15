# Project Memory

## Purpose

This file is the anti-drift memory for the repository.
It records the locked baseline, archived directions, active extension lines, and reproducibility rules.
If future work conflicts with this file, the conflict must be stated explicitly instead of being silently ignored.

## Locked Baseline

- Old `v85` long+short is retired as the primary research line.
- Current primary line is BTC long-only `squeeze_release_20`.
- Current `research_optimal` is `lb20_stop3.2_trail5.0_beoff`.
- Current official structure is `Core BTC holding + Binary AddOn overlay`.
- Default research tuple is:
  - `next_bar_open`
  - `legacy_bar_extrema`
  - `midpoint`
  - `full_model`
- Stress/gate tuple is:
  - `live_runner_next_5m_close`
  - `segment_path_same_bar`
  - `pessimistic`
  - `full_model`
- `launch_optimal` remains `LAUNCH_NO_GO`.
- The long-only line is a high-quality BTC trend overlay, not a confirmed standalone BTC buy-and-hold replacement.

## Archived Research

- Risk-Off:
  - directionally valid
  - execution-aligned
  - promotion frozen
  - archived and not part of the baseline
- old `v85` long+short:
  - retired as primary research
- Bear short sleeve:
  - inactive

Archived means the line is preserved for reference and audit, but should not be resumed as if it were still an active baseline candidate.

## Active Extension Lines

- AddOn grading is the active extension line.
- Current lead candidate is `Core + GradedAddOn[compression_breakout]`.
- Current status is promising but not promotable.

## Research Boundaries

- Continue only on `squeeze_release_20 / lb20_stop3.2_trail5.0_beoff` unless the user explicitly changes the baseline.
- Do not return to old `v85` long+short as the main line.
- Do not reopen Risk-Off promotion unless a genuinely new hypothesis is explicitly authorized.
- Do not reopen broad brute-force parameter search.
- Do not add many new filters just to improve backtest optics.
- Do not switch the default execution tuple back to a harsher stress tuple or to a more idealized tuple without explicitly documenting the change.

## Reproducibility Rules

1. Final claims must be reproducible from committed code and committed result files.
2. Bar-level logic must be causal.
   - Signals may use information available at bar `t` close.
   - Position changes and PnL realization must start from bar `t+1` or from the explicitly modeled execution event.
3. If a study does not use the default execution-aligned framework, it must be labeled `exploratory` and must not be presented as equal in status to engine-backed strategy results.
4. Full-sample winner selection is allowed only for exploration.
   - It is not enough for formal promotion of a new module, system structure, or default parameter.
5. Default-tuple strategy studies and stress/gate studies must remain clearly separated.
6. If a new module is introduced at the portfolio layer, its implementation path must be stated explicitly:
   - execution-aligned engine-backed
   - or simplified allocation simulation
7. If the simplified path is used, assumptions and limitations must be written into the report, not hidden.

## Development Principles

- First verify structure, then tune parameters.
- Prefer low-frequency, explainable, auditable logic.
- Keep modules simple enough that each one has a clear job.
- Add parameter analysis only when it is needed to test robustness, not as the main research method.
- Do not let one attractive backtest overturn a locked baseline without an explicit revalidation step.

## Future Research Directions

- Keep the baseline locked at `Core BTC holding + Binary AddOn overlay` unless a later promotion study explicitly clears all criteria.
- Continue only on narrow, auditable AddOn exposure research rather than new strategy families.
- Preserve archived directions as archive material rather than active workstreams.
- Treat AddOn grading as the only active extension line until a later promotion decision says otherwise.
