# Multi-Sleeve Operational Monitoring

## Monitoring Objective

Live monitoring should answer four questions quickly:

1. What state is the portfolio currently in?
2. How much cap headroom remains?
3. Is path burden still inside the approved envelope?
4. Is any governance action required?

## Required Dashboard Fields

### Portfolio State

| Field | Meaning |
| --- | --- |
| `portfolio_state` | `Core-Only`, `Expansion-Carry`, `Diversification-Carry`, `Stacked Multi-Sleeve`, `Cap-Constrained Stacked`, or `Governance Attention` |
| `sleeve1_active` | whether `ConstAddOn[1.00x]` is active |
| `sleeve2_active` | whether `RangeRotation` is active |
| `sleeve_overlap_state` | `none`, `single-sleeve`, or `dual-sleeve` |

### Exposure And Cap

| Field | Meaning |
| --- | --- |
| `core_exposure` | current core exposure, normally `1.0x` |
| `sleeve1_exposure` | current incremental exposure from `Sleeve #1` |
| `sleeve2_exposure` | current incremental exposure from `Sleeve #2` |
| `total_exposure` | current total gross exposure |
| `cap_headroom` | `3.0x - total_exposure` |
| `cap_utilization_pct` | `total_exposure / 3.0x` |
| `soft_cap_band` | `Normal`, `Stacked`, `High-Use`, `Pre-Breach`, `Breach` |

### Path-Burden

| Field | Meaning |
| --- | --- |
| `current_drawdown_pct` | drawdown from last equity high |
| `days_since_equity_high` | time since last equity high |
| `rolling_90d_return_pct` | near-term performance |
| `rolling_180d_return_pct` | medium-term performance |
| `rolling_365d_return_pct` | long-window performance |
| `rolling_180d_maxdd_pct` | recent path roughness |
| `trailing_3m_cluster_loss_pct` | worst short cluster burden |
| `trailing_6m_cluster_loss_pct` | worst medium cluster burden |
| `underwater_state` | whether the portfolio is below its equity high |

### Sleeve Contribution

| Field | Meaning |
| --- | --- |
| `sleeve1_30d_pnl_pct` | recent contribution from `Sleeve #1` |
| `sleeve2_30d_pnl_pct` | recent contribution from `Sleeve #2` |
| `sleeve1_90d_active_ratio_pct` | recent activation intensity |
| `sleeve2_90d_active_ratio_pct` | recent activation intensity |
| `dual_sleeve_90d_overlap_ratio_pct` | how often both sleeves were active recently |

### Governance Alerts

| Field | Meaning |
| --- | --- |
| `governance_alert_level` | `Observe`, `Review`, `Escalate`, or `Incident` |
| `alert_reason` | the metric that triggered the current alert |
| `review_due` | next required governance check |

## Monitoring Cadence

### Per bar / live update

- current sleeve activation state
- total exposure
- cap headroom
- alert level

### Daily governance summary

- end-of-day portfolio state distribution
- max exposure reached
- latest drawdown
- days since high
- trailing `90d / 180d / 365d` returns
- trailing `3m / 6m` cluster loss

### Weekly governance review

- whether the system spent material time in `High-Use` or `Pre-Breach`
- whether path burden is trending toward `Review` or `Escalate`
- sleeve overlap behavior and recent contribution mix

## Live Communication Rules

- If only `Sleeve #1` is active, report `Expansion-Carry`.
- If only `Sleeve #2` is active, report `Diversification-Carry`.
- If both sleeves are active, report `Stacked Multi-Sleeve`.
- If total exposure exceeds `2.5x`, attach explicit cap-band labeling.
- If path-burden thresholds are breached, append governance alert status to the state label.

## Decision Boundary In Operations

Operations may:

- label the current state
- escalate alerts
- recommend governance review
- report cap pressure and path burden

Operations may not:

- change sleeve logic
- reopen frozen research
- tighten or loosen trading behavior implicitly
- reinterpret alerts as signal changes

Operational monitoring is descriptive and escalation-oriented. Research changes require a separate authorized research step.
