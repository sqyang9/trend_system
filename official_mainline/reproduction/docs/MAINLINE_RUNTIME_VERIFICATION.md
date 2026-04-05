# Mainline Runtime Verification

## Scope

- Canonical locked mainline:
  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`
  - `S1 = ATRVT_90D_med_035_150`
  - `S2 = ATRVT_60D_med_035_150`
  - stable re-entry `close3`
  - high-churn re-entry `strict EMA50 + breakout_4`
  - `HV percentile >= 85` force HC
  - current `S1 gate contract = S1_VP_LB60_EA050_VR120`

## Verification Chain

- Formal replay:
  - `v123_formal_launch_and_layer2_weight_audit.py`
- Live package:
  - `live_operating_layer/v132_live_operating_layer.py`
- Execution status runner:
  - `live_operating_layer/mainline_live_status.py`
- Dashboard snapshot path:
  - `dashboard/signal_layer.py`
- Historical atlas:
  - `historical_signal_atlas/generate_historical_signal_atlas.py`
- Canonical local runtime/research data root:
  - `dashboard/data/`

## Expected Runtime Surface

- Core context:
  - `core_reentry_gate`
  - `core_instability_state`
  - `instability_source`
  - `hv_forced_high_churn`
- Sleeve scaling:
  - `atrvt_label`
  - `atr_scale_s1`
  - `atr_scale_s2`
- Background state:
  - `hv_pct_180d`
- S1 gate surface:
  - `s1_gate_label`
  - `s1_gate_enabled`
  - `s1_gate_candidate`
  - `s1_gate_pass`
  - `s1_gate_reason`
  - `s1_vp_hvn_escape_atr`
  - `s1_vp_volume_ratio20`

## Latest Verification Run

- Date:
  - `2026-04-05`
- Passed:
  - `python3 -m py_compile` for shared/background, formal, live, status, dashboard signal layer, and atlas generator
  - `python3 v123_formal_launch_and_layer2_weight_audit.py`
  - `python3 live_operating_layer/v132_live_operating_layer.py`
  - `python3 live_operating_layer/mainline_live_status.py --account-equity 100000 --current-notional 100000`
  - `python3 historical_signal_atlas/generate_historical_signal_atlas.py`
  - dashboard snapshot with cached data:
    - interpreter `/Users/zhao/miniforge3/bin/python3`
    - refresh bypassed in-process because the sandbox has no network
- Current verified live snapshot:
  - time `2026-03-29 12:00:00+00:00`
  - state `core_flat_s1_0_s2_0`
  - `ATR S1 1.2507 / S2 1.3592`
  - `HV pct 35.4`
  - `instability_source = flips`
  - `S1 gate = S1_VP_LB60_EA050_VR120 / not_applicable`
- Current verified dashboard cached snapshot:
  - time `2026-03-30 20:00:00+00:00`
  - state `core_flat_s1_0_s2_0`
  - `S1 gate = S1_VP_LB60_EA050_VR120 / not_applicable`
  - `core / s1 / s2 / total = 0.00 / 0.00 / 0.00 / 0.00`
  - snapshot rendered successfully through `dashboard/run_dashboard.py`

## Known Runtime Caveats

- From the `dashboard/` directory, shell `python3` resolves to `/opt/homebrew/opt/python@3.13/bin/python3.13`, which does not have `plotly`.
- For dashboard runtime verification, use the canonical miniforge interpreter or the project environment.
- Default dashboard refresh tries to pull OKX data; in offline/sandboxed mode, cached-data verification should bypass `strict_refresh()`.
- Formal replay, live package, dashboard, and atlas are now wired to the canonical `dashboard/data` root when it is present.
- Live/status and dashboard can still differ in their latest visible timestamp because they summarize different runtime surfaces, not because they read different data roots.

## Current Intent

- Runtime verification confirms the locked mainline remains the only canonical production path.
- The promoted `S1 volume-profile proxy gate` is now part of the canonical production path across formal/live/dashboard/atlas.
