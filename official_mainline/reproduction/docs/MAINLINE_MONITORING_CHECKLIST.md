# Mainline Monitoring Checklist

## Every 4H Close

- Check `core_reentry_gate`.
- Check `core_instability_state`.
- Check `instability_source`.
- Check `hv_pct_180d`.
- Check `hv_forced_high_churn`.
- Check `atr_scale_s1`.
- Check `atr_scale_s2`.
- Check `total_exposure` and remaining cap headroom.
- Check current drawdown and `days_since_equity_high`.

## S1 Gate Surface

- Check `s1_gate_label`.
- Check `s1_gate_enabled`.
- Check whether a recent bar was `s1_gate_candidate = True`.
- If blocked, record `s1_gate_reason`.
- If the active reserve gate is volume-profile proxy, also track:
  - `s1_vp_hvn_escape_atr`
  - `s1_vp_volume_ratio20`

## Weekly Review

- Count recent `FLAT -> RE` and `RE -> FLAT` loops.
- Count recent `hv_forced_high_churn` bars.
- Review whether ATR scales are clustering near clip edges.
- Review whether total exposure is spending too much time near the `3.0x` cap.
- Review whether any reserve challenger is materially outperforming the locked baseline in shadow form.

## Escalation Triggers

- `total_exposure >= 2.85x`
- `governance_alert_level in {Review, Escalate, Incident}`
- repeated `hv_forced_high_churn`
- `atr_scale_s1` or `atr_scale_s2` pinned near clip edges for extended periods
- repeated `S1` candidate blocks after obvious breakout setups
