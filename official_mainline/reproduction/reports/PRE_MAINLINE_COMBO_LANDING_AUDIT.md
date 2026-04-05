# Pre-Mainline Combo Landing Audit

## Decision

- Signal branch status: `GO_TO_PROMOTION_AUDIT`
- Landing status today: `CONDITIONAL_GO`
- Reason: `Combo` has already cleared the independent audition bar against the current mainline replay, but the repository still lacks a shared implementation contract for:
  - dynamic sleeve scaling from `ATR`
  - background volatility forcing from `HV percentile`
  - live/dashboard semantics for time-varying sleeve weights and HV-forced high-churn state

## Landing Candidate

- Structure stays:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
- Candidate upgrade:
  - `S1 + S2 ATR vol-targeting`
  - `HV percentile >= 85 -> force high-churn core qualification`
- Current official baseline:
  - `Return 2878.61% / Calmar 2.854 / MaxDD -25.41%`
- Local replay baseline inside volatility-proxy audits:
  - `Return 2893.89% / Calmar 2.854 / MaxDD -25.46%`
- Combo audition result:
  - `Return 2995.89% / Calmar 3.044 / MaxDD -24.17%`

## Findings

### P0: Shared mainline code has no canonical interface for dynamic sleeve scaling

- In [v123_formal_launch_and_layer2_weight_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v123_formal_launch_and_layer2_weight_audit.py#L76), `base_bundle()` only exports fixed `base_s1_weight` and `base_s2_weight`.
- In [v123_formal_launch_and_layer2_weight_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v123_formal_launch_and_layer2_weight_audit.py#L128), `simulate_weight_combo()` only supports static scalar posture multipliers.
- `Combo` is not just a new posture tuple. It requires time-varying `atr_scale[t]` on both sleeves. If this is patched ad hoc in one audit script and not promoted into shared mainline code, official reproduction will fork into two incompatible engines.

Implication:

- `ATR vol-targeting` must be implemented as a first-class sleeve-scaling layer in the shared formal portfolio path, not as an isolated research-only wrapper.

### P0: Core high-churn detection has no shared background-volatility hook

- In [v121_coreonly_riskoff_sellside_ema_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v121_coreonly_riskoff_sellside_ema_audit.py#L164), `build_instability_flags()` only derives `instability_state` from trailing core flips.
- In [v121_coreonly_riskoff_sellside_ema_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v121_coreonly_riskoff_sellside_ema_audit.py#L56), `build_indicators()` has no `ATR` or `HV` background columns.
- `Combo` requires `HV percentile >= 85` to force the stricter high-churn gate earlier. Right now that behavior exists only in the independent volatility-proxy scripts, not in the shared mainline overlay API.

Implication:

- `HV percentile` forcing must be added to the canonical Risk-Off overlay interface, or live code and backtest code will disagree about when the system is truly in the stricter gate family.

### P1: Live and dashboard layers will misreport sleeve exposures after Combo lands

- In [live_operating_layer/v132_live_operating_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/v132_live_operating_layer.py#L38), `ADOPTED_POSTURE` is still defined as fixed scalar weights only.
- In [live_operating_layer/v132_live_operating_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/v132_live_operating_layer.py#L277), live package generation only calls `simulate_weight_combo(bundle, ADOPTED_POSTURE)`.
- In [live_operating_layer/v132_live_operating_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/live_operating_layer/v132_live_operating_layer.py#L283), `s1_exp` and `s2_exp` are computed as `base_weight * posture_weight`, which is wrong once the adopted sleeves are dynamically scaled by `ATR`.
- The same reporting assumption exists in [dashboard/signal_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/dashboard/signal_layer.py#L96) through [dashboard/signal_layer.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/dashboard/signal_layer.py#L194).

Implication:

- Without live/dashboard changes, the repo would claim one exposure path while the adopted engine runs another. That is a release blocker.

### P1: Current live/dashboard state vocabulary has no place for volatility forcing

- The live and dashboard payloads currently expose:
  - `core_reentry_family`
  - `core_reentry_state`
  - `core_reentry_gate`
  - `core_instability_state`
- They do not expose:
  - `atr_scale`
  - `hv_pct_180d`
  - whether high-churn was triggered by flips, by HV forcing, or by both
- As a result, after promotion, operators could see `strict_and_breakout4` but still have no explanation for why the system entered high-churn mode earlier than the flips-only baseline.

Implication:

- A new presentation contract is needed for background indicators and for the source of the high-churn state.

### P2: Official reproduction and archive packages are still anchored to the hybrid overlay-only adoption

- [ACTIVE_MAINLINE_STATUS.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/ACTIVE_MAINLINE_STATUS.md#L4) through [ACTIVE_MAINLINE_STATUS.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/ACTIVE_MAINLINE_STATUS.md#L19) still describe the current official mainline as the hybrid close3/high-churn overlay with fixed sleeve posture.
- [official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md#L3) through [official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md#L27) do not include any canonical `ATR/HV` adoption chain.

Implication:

- This is not a blocker before implementation, but it becomes a blocker before release. The docs and archive snapshot must move together with the code.

## Required Implementation Surface

### 1. Shared background-indicator layer

Add a shared helper, not a research-only copy, for:

- `ATR14`
- `ATR% = ATR / close`
- trailing `180d` ATR% median
- clipped `atr_scale`
- `HV14_ann`
- trailing `180d` `hv_pct_180d`

The cleanest target is either:

- extend [v121_coreonly_riskoff_sellside_ema_audit.py](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/v121_coreonly_riskoff_sellside_ema_audit.py)
- or factor a small shared utility that both `v121`, `v123`, `v132`, and dashboard can import

### 2. Canonical instability-state API

Upgrade the current flips-only instability builder so it can produce:

- `core_flips_30d`
- `core_flips_60d`
- `hv_pct_180d`
- `hv_forced_high_churn`
- `instability_state`
- `instability_source`
  - `flips`
  - `hv_force`
  - `both`

### 3. Dynamic sleeve-scaling contract in the formal portfolio layer

The formal bundle must export enough information to support:

- fixed sleeve posture
- optional per-bar sleeve scale series

At minimum the shared portfolio path needs:

- `base_s1_equity`
- `base_s2_equity`
- `base_s1_weight`
- `base_s2_weight`
- optional `s1_scale_series`
- optional `s2_scale_series`

and a simulation path that composes them canonically.

### 4. Live/dashboard schema upgrade

Add fields for:

- `atr_scale`
- `hv_pct_180d`
- `hv_force_high_churn`
- `instability_source`
- effective `s1_weight`
- effective `s2_weight`

This is required so live operating outputs can explain:

- why total exposure shrank even though posture weights did not change
- why the core entered the stricter gate family before flips alone would have triggered it

## Validation Required Before Promotion

### Backtest / audit chain

Must rerun and freeze:

1. A promotion-level formal audit for the adopted combo mainline
2. Layer-2 posture confirmation under the new dynamic sleeve logic
3. A current-state live package rebuild
4. Dashboard signal snapshot parity

### Acceptance checks

- `Combo` still beats the current official mainline across `default / stress / harsh`
- `W06 DD/Exp` improvement survives the shared-code implementation
- `W11 entries` stays reduced at `3`
- live `s1/s2` reported exposures match the actual scaled sleeves
- dashboard `core_instability_state` and `instability_source` match the adopted engine

### Documentation / archive chain

On promotion, update together:

- `ACTIVE_MAINLINE_STATUS.md`
- `WORKING_BASELINE.md`
- `memory.md`
- `BACKGROUND_INDICATORS.md`
- `official_mainline/README.md`
- `official_mainline/OFFICIAL_MAINLINE_REPRODUCTION_MANIFEST.md`
- `official_mainline/reproduction/*`
- new `archive/` snapshot for the combo-adopted mainline

## Go / No-Go Readout

- Signal quality: `GO`
- Landing readiness today: `NO_GO` without implementation work
- Promotion recommendation: `GO_AFTER_IMPLEMENTATION`

Most important conclusion:

- `Combo` does not fail because of results.
- It is blocked only because the current official mainline stack is built around:
  - fixed sleeve posture
  - flips-only instability
  - no background-indicator contract

That means the next step is not more signal research. It is a focused implementation pass plus a parity audit.
