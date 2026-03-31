# Risk-Off Reentry Candidates

## Scope

This round reopens only one archived strategy question:

- how the BTC core should re-enter after a valid Risk-Off exit

This round does not reopen:

- broad Risk-Off trigger search
- full EMA grid work
- Bear Short
- governance-led posture overlays
- AddOn or sleeve logic changes

## Historical Problem To Solve

Archived Risk-Off work already established the core problem:

- downside protection was directionally valid
- the main blocker was bull / recovery opportunity cost
- the deepest remaining drag was staying flat too long after conditions improved

The best old candidate was:

- `RO_EMA220_REENTRY_CLOSE_HOLD_3`

It improved the old baseline, but still left too much recovery drag and flat-state upside drag.

## Proposed Reentry Designs

### 1. `RO_REENTRY_STRUCTURE_REACCEPT_FULL`

Logic:

- after Risk-Off exit state, require price to re-enter and hold above a short rebuilt structure zone
- restore core directly to full once structure is clearly re-accepted

Why it addresses the blocker:

- attacks the specific “flat too long after conditions improve” problem
- should re-engage earlier than long delay-only hold logic
- still demands local structural proof before full restoration

### 2. `RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100`

Logic:

- same rebuilt-structure re-acceptance condition as above
- restore `50%` core first
- restore remaining `50%` only after continued acceptance

Why it addresses the blocker:

- tests whether staged restoration can keep some upside participation without giving up all whipsaw protection
- directly compares full restoration vs staged restoration under the same structural hypothesis

### 3. `RO_REENTRY_TREND_REBUILD_FULL`

Logic:

- after Risk-Off, require a simple trend rebuild state such as reclaimed long EMA plus positive rebuild posture
- restore core directly to full once the rebuild state is confirmed

Why it addresses the blocker:

- targets recovery participation more directly than pure time-delay logic
- may be more robust than very local structure-only re-entry if the recovery is directional rather than box-like

### 4. `RO_REENTRY_TREND_REBUILD_STAGE50_100`

Logic:

- same trend rebuild confirmation as above
- restore in two steps instead of all at once

Why it addresses the blocker:

- tests whether trend rebuild is best used as early partial re-risking rather than full immediate restoration
- directly addresses the question of whether staged restoration beats all-at-once restoration

### 5. `RO_REENTRY_TIME_PLUS_STATE_STAGE`

Logic:

- require a minimum time-off window after Risk-Off
- after that time floor, allow staged restoration only when a simple approved state condition clears

Why it addresses the blocker:

- explicitly tests whether the old hold-confirm family failed because it was too time-heavy and not state-aware enough
- gives a disciplined comparison between pure delay and delay-plus-state

## Candidate Count Discipline

The candidate set is intentionally capped at five.

It covers the four authorized design families:

- structure re-acceptance
- trend rebuild
- staged restoration
- time-plus-state restoration

without reopening a wide search.

## Direct Answers

1. Proposed re-entry designs:
   - `RO_REENTRY_STRUCTURE_REACCEPT_FULL`
   - `RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100`
   - `RO_REENTRY_TREND_REBUILD_FULL`
   - `RO_REENTRY_TREND_REBUILD_STAGE50_100`
   - `RO_REENTRY_TIME_PLUS_STATE_STAGE`

2. Why each addresses the opportunity-cost blocker:
   Each one tries to reduce flat-state delay after risk conditions improve, while still keeping some simple confirmation so re-entry does not collapse into immediate whipsaw.

3. Which should be tested first:
   `RO_REENTRY_STRUCTURE_REACCEPT_STAGE50_100`

4. Which old directions remain closed:
   broad EMA trigger redesign, wide hold-ladder brute-force, core-off-weight rewrite, Bear Short expansion, and any attempt to repackage governance overlays as trading logic.
