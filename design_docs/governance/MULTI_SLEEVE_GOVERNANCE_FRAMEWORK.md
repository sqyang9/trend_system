# Multi-Sleeve Governance Framework

## Governance Objective

The governance objective is to operate the approved formal portfolio cleanly:

- preserve the approved `3.0x` hard cap
- recognize expected path burden without overreacting
- escalate when realized burden moves outside the audited envelope
- keep governance decisions separate from frozen research decisions

## Cap Governance Model

### Hard rule

- `3.0x` total gross exposure is the inviolable hard ceiling

### Interpretation

- `3.0x` is a peak-use ceiling, not an average-use target
- average exposure near the audited `~136.85%` is normal
- dual-sleeve stacking is expected behavior, not a breach by itself

### Soft governance bands

| Band | Total Exposure | Meaning | Governance Action |
| --- | --- | --- | --- |
| `Normal` | `<= 2.0x` | ordinary portfolio operation | monitor only |
| `Stacked` | `> 2.0x and <= 2.5x` | dual-sleeve deployment is meaningful | daily review sufficient |
| `High-Use` | `> 2.5x and < 2.85x` | cap utilization is elevated | explicit governance attention |
| `Pre-Breach` | `>= 2.85x and < 3.0x` | hard-cap headroom is thin | same-day alert and review |
| `Breach` | `>= 3.0x` | hard-cap violation | escalation and incident handling |

### Cap headroom metric

- `cap_headroom = 3.0x - current_total_exposure`

This should be shown live and treated as a first-class governance field.

## Path-Burden Governance

The largest remaining practical risk is path burden, not signal validity.

### Metrics to monitor

- current drawdown from last equity high
- days since last equity high
- rolling `90d / 180d / 365d` return
- rolling `180d` max drawdown
- worst trailing `3m` cluster return
- worst trailing `6m` cluster return
- underwater ratio / time underwater
- sleeve overlap persistence during drawdown

### Threshold ladder

| Level | Trigger | Interpretation | Governance Response |
| --- | --- | --- | --- |
| `Observe` | drawdown worse than `-35%` or days since high above `180` | still inside expected burden zone | increase review frequency |
| `Review` | drawdown worse than `-45%` or days since high above `300` or trailing `6m` return below `-30%` | burden is materially heavy | governance review meeting required |
| `Escalate` | drawdown worse than `-55%` or days since high above `425` or trailing `6m` return below `-40%` | near the audited extreme burden envelope | senior governance escalation |
| `Incident` | hard-cap breach or path metrics worse than audited deployment envelope | unacceptable live deviation | incident protocol |

### Expected but acceptable

The following are expected and should not automatically trigger research reopening:

- long underwater periods
- dual-sleeve overlap during difficult periods
- deep but sub-threshold clustered losses
- temporary operation in `High-Use` cap band

### Escalation-worthy

The following deserve governance escalation:

- repeated operation near the hard cap while drawdown is worsening
- drawdown moving toward audited worst-case burden
- unusually long time since last equity high
- cluster losses materially worse than the approved operating envelope

## Governance Decision Protocol

### Governance may decide

- whether `3.0x` remains approved for deployment
- whether to fall back to `2.5x`
- alert thresholds and reporting cadence
- whether deployment remains in normal mode, heightened review mode, or escalation mode
- whether new capital deployment should pause while the system remains active

### Governance may not decide unilaterally

- reopen `Risk-Off`
- reopen regime cap
- reopen breakout repair lines
- re-optimize signal parameters
- reinterpret rejected sleeves as active candidates
- turn operational alerts into silent strategy changes

## Governance vs Research Boundary

### Governance domain

- cap usage
- monitoring thresholds
- escalation policy
- deployment posture
- reporting and oversight cadence

### Research-frozen domain

- mother strategy
- locked execution tuples
- Sleeve #1 signal logic
- Sleeve #2 signal logic
- rejected or archived research lines

If a governance concern suggests a real strategy change, that change must return to research as a new authorized stage. Governance should not implement it informally.
