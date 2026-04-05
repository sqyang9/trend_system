# Startup And Onboarding Playbook

## Official Operating Baseline

- Structure: `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`.
- Adopted running posture: `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`.
- Sleeve scaling: `S1 + S2 ATR vol-targeting`.
- Risk-Off overlay: sell-side `EMA250`, stable re-entry `close3`, high-churn re-entry `strict EMA50 + breakout_4`, `HV percentile >= 85` forces the stricter gate earlier, override `Weekly RSI(14) <= 30 hold`.

## New Capital Onboarding

- Primary rule: read the live state panel first.
- If current live state matches the present audited state family, preferred method is the current memo recommendation.
- Current audited recommendation: `immediate_full`.

## Warmup Requirements

- Preferred: `12m` prewarm.
- Acceptable: `6m` prewarm.
- Not recommended: `3m` prewarm only.
- Full-history prewarm is not mandatory for practical operation.

## Daily / Weekly Use

- Daily: check current state, exposures, Risk-Off status, cap headroom, and path-burden alert level.
- Weekly: check whether onboarding guidance or expected operating posture changed materially.
- Do not reinterpret governance alerts as trading signals.