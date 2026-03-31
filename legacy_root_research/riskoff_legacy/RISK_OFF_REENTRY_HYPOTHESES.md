# Risk-Off Reentry Hypotheses

## Objective

This document records the portfolio-level hypotheses for the reopened Risk-Off core re-entry problem.

The evaluation target is not “best standalone Risk-Off optics.”
The target is:

- reduce bull / recovery opportunity cost
- preserve as much downside-control value as possible
- avoid quietly becoming a new trigger-search program

## Reference Points

### Archived Risk-Off baseline

- `RO_EMA220_FLAT`

Role:

- reference for the original aligned Risk-Off family

### Best archived re-entry repair

- `RO_EMA220_REENTRY_CLOSE_HOLD_3`

What it proved:

- re-entry timing matters
- simple hold-confirm logic can help

What it did not solve:

- recovery drag remained too large
- flat-state upside drag remained too large
- promotion blocker was not removed

## Hypotheses By Candidate

### `RO_REENTRY_STRUCTURE_REACCEPT_FULL`

Hypothesis:

- the old line missed too much upside because it waited on generic delay logic instead of looking for explicit post-exit structural acceptance
- a clean rebuilt-structure confirmation may restore the core earlier without a large whipsaw penalty

Main risk:

- may still collapse into a slower breakout-style re-entry if the structure test is too strict

### `RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100`

Hypothesis:

- the best balance may be early partial participation followed by full restoration only after acceptance persists
- staged restoration may reduce recovery opportunity cost better than full-flat waiting while still preserving more downside discipline than immediate full restoration

Main risk:

- the second stage may still arrive too late, leaving most of the blocker unresolved

### `RO_REENTRY_TREND_REBUILD_FULL`

Hypothesis:

- recovery windows may be better captured by a simple trend rebuild state than by local structure re-acceptance alone
- this may work especially well when recovery is directional rather than box-like

Main risk:

- may look too similar to the old EMA family and fail to solve the flat-too-long problem in practice

### `RO_REENTRY_TREND_REBUILD_STAGE50_100`

Hypothesis:

- trend rebuild may be useful as a staged restoration ladder rather than an immediate full restoration trigger
- this may reduce opportunity cost while keeping whipsaw control cleaner than the old hold-only family

Main risk:

- may become only a softer version of `RO_EMA220_REENTRY_CLOSE_HOLD_3` without enough practical improvement

### `RO_REENTRY_TIME_PLUS_STATE_STAGE`

Hypothesis:

- simple hold logic failed because it relied too much on time and not enough on state
- adding a time floor plus a simple state clearance may improve robustness without reopening full signal search

Main risk:

- may still be mostly a delay family in disguise and therefore inherit the old opportunity-cost problem

## First-Test Logic

### Recommended first candidate

`RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100`

Why first:

- it is the clearest direct attack on the archived blocker
- it tests both structure-led re-entry and staged restoration in one disciplined candidate
- it is less likely than pure trend rebuild to collapse back into the old EMA-delay family

## Old Directions That Stay Closed

These remain closed even though the core re-entry problem is now reopened:

- broad EMA200 / EMA210 / EMA220 trigger-family search
- new bear trigger families
- core-off-weight redesign
- broad close-hold ladder expansion
- broad staged percentage grid search
- Bear Short coupling
- governance-layer de-risk logic as trading logic

## Direct Answers

1. Why these designs address the old opportunity-cost blocker:
   They all try to restore core exposure earlier and more intelligently than staying flat on delay-only logic, while keeping the design simple enough to audit.

2. Which design should be tested first:
   `RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100`

3. Which old directions remain closed:
   trigger-family redesign, broad hold/stage brute-force, Bear Short, and governance-like overlays disguised as strategy logic.
