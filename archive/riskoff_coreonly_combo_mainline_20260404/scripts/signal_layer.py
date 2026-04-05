#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Signal/state layer for the dashboard package."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = REPO_ROOT / "live_operating_layer"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(LIVE_ROOT) not in sys.path:
    sys.path.insert(0, str(LIVE_ROOT))

_stderr_fd = os.dup(2)
_devnull_fd = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull_fd, 2)
try:
    from v132_live_operating_layer import (  # noqa: E402
        ADOPTED_POSTURE,
        HARD_CAP,
        build_state_series,
        classify_core_riskoff_state,
        classify_governance_alert,
        classify_portfolio_state,
        classify_soft_cap_band,
        days_since_high,
        path_bundle,
        rolling_return,
    )
    from v90_asset_management_system_aligned import current_research_optimal as riskoff_current_research_optimal  # noqa: E402
    from v121_coreonly_riskoff_sellside_ema_audit import build_indicators, build_instability_flags, build_target_trace  # noqa: E402
    from v123_formal_launch_and_layer2_weight_audit import ADOPTED_SPEC, SCENARIOS, base_bundle, simulate_weight_combo  # noqa: E402
finally:
    os.dup2(_stderr_fd, 2)
    os.close(_stderr_fd)
    os.close(_devnull_fd)

from data_layer import data_freshness_report, direct_aux_report, load_market_data


def transition_events(series: pd.Series, active_fn) -> pd.DataFrame:
    cur = series.astype(float)
    prev = cur.shift(1).fillna(cur.iloc[0])
    rows = []
    for ts, p, c in zip(cur.index, prev, cur):
        was_active = active_fn(float(p))
        is_active = active_fn(float(c))
        if not was_active and is_active:
            rows.append({"timestamp": ts, "event": "entry", "value": float(c)})
        elif was_active and not is_active:
            rows.append({"timestamp": ts, "event": "exit", "value": float(c)})
    return pd.DataFrame(rows)


def contiguous_flat_spans(series: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    flat = series.astype(float) <= 1e-9
    spans: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    start = None
    prev_ts = None
    for ts, is_flat in flat.items():
        if is_flat and start is None:
            start = ts
        if not is_flat and start is not None:
            spans.append((start, prev_ts if prev_ts is not None else ts))
            start = None
        prev_ts = ts
    if start is not None and prev_ts is not None:
        spans.append((start, prev_ts))
    return spans


def build_signal_snapshot() -> Dict:
    df_5m, df_4h = load_market_data()
    freshness = data_freshness_report(df_5m, df_4h)
    freshness.update(direct_aux_report())
    bundle = base_bundle(df_5m, df_4h, SCENARIOS[0])
    sim = simulate_weight_combo(bundle, ADOPTED_POSTURE)
    core_trace = bundle["core_trace_4h"].copy()
    core_target_unit = bundle["core_target_4h"].astype(float)
    riskoff_ind = bundle["core_indicators_4h"].copy()
    instability = bundle["core_instability_4h"].copy()

    idx = sim["combo_equity"].index
    equity = sim["combo_equity"].astype(float)
    total_exp = sim["combo_exposure"].astype(float)
    core_exp = sim["effective_core_weight"].reindex(idx).astype(float)
    s1_exp = sim["effective_s1_weight"].reindex(idx).astype(float)
    s2_exp = sim["effective_s2_weight"].reindex(idx).astype(float)
    dd = (equity / equity.cummax() - 1.0) * 100.0
    dsh = days_since_high(equity)
    state_series = build_state_series(core_exp, s1_exp, s2_exp)
    latest_ts = idx[-1]
    latest = {
        "timestamp": str(latest_ts),
        "portfolio_state": classify_portfolio_state(
            float(core_exp.iloc[-1]),
            float(s1_exp.iloc[-1]),
            float(s2_exp.iloc[-1]),
            float(total_exp.iloc[-1]),
            float(dd.iloc[-1]),
            float(dsh.iloc[-1]),
        ),
        "core_riskoff_state": classify_core_riskoff_state(float(core_exp.iloc[-1])),
        "riskoff_active": bool(core_exp.iloc[-1] < ADOPTED_POSTURE["core_weight"] - 1e-9),
        "core_exposure": float(core_exp.iloc[-1]),
        "sleeve1_exposure": float(s1_exp.iloc[-1]),
        "sleeve2_exposure": float(s2_exp.iloc[-1]),
        "total_exposure": float(total_exp.iloc[-1]),
        "cap_headroom": float(HARD_CAP - total_exp.iloc[-1]),
        "soft_cap_band": classify_soft_cap_band(float(total_exp.iloc[-1])),
        "current_drawdown_pct": float(dd.iloc[-1]),
        "days_since_equity_high": float(dsh.iloc[-1]),
        "rolling_30d_return_pct": rolling_return(equity, 30 * 6),
        "rolling_90d_return_pct": rolling_return(equity, 90 * 6),
        "rolling_180d_return_pct": rolling_return(equity, 180 * 6),
        "rolling_365d_return_pct": rolling_return(equity, 365 * 6),
        "core_reentry_family": str(ADOPTED_SPEC["name"]),
        "core_reentry_state": str(core_trace["state"].iloc[-1]),
        "core_reentry_gate": str(core_trace["active_gate"].iloc[-1]),
        "core_instability_state": str(core_trace["instability_state"].iloc[-1]),
        "core_instability_source": str(instability["instability_source"].reindex(idx).ffill().iloc[-1]),
        "atr_scale": float(sim["atr_scale"].reindex(idx).ffill().iloc[-1]),
        "hv_pct_180d": float(sim["hv_pct_180d"].reindex(idx).ffill().iloc[-1]),
        "hv_forced_high_churn": bool(instability["hv_forced_high_churn"].reindex(idx).ffill().iloc[-1]),
    }
    pb = path_bundle(equity)
    latest["trailing_3m_cluster_loss_pct"] = pb["worst_3m_cluster_return_pct"]
    latest["trailing_6m_cluster_loss_pct"] = pb["worst_6m_cluster_return_pct"]
    latest["governance_alert_level"] = classify_governance_alert(
        latest["current_drawdown_pct"],
        latest["days_since_equity_high"],
        latest["trailing_6m_cluster_loss_pct"],
        latest["total_exposure"],
    )

    recent_bars = 180 * 6
    recent_4h = df_4h.set_index("timestamp").sort_index().tail(recent_bars).copy()
    recent_4h["ema250"] = riskoff_ind["ema"].reindex(recent_4h.index).astype(float)
    recent_4h["ema50"] = riskoff_ind["ema50"].reindex(recent_4h.index).astype(float)
    recent_4h["core_target"] = (
        core_target_unit.reindex(recent_4h.index).ffill().fillna(1.0).astype(float) * ADOPTED_POSTURE["core_weight"]
    )
    recent_4h["core_gate"] = core_trace["active_gate"].reindex(recent_4h.index).ffill().fillna("baseline_close3")
    recent_4h["core_instability_state"] = core_trace["instability_state"].reindex(recent_4h.index).ffill().fillna("stable")
    recent_4h["core_instability_source"] = instability["instability_source"].reindex(recent_4h.index).ffill().fillna("stable")
    recent_4h["atr_scale"] = sim["atr_scale"].reindex(recent_4h.index).ffill().fillna(1.0).astype(float)
    recent_4h["hv_pct_180d"] = sim["hv_pct_180d"].reindex(recent_4h.index).ffill().astype(float)
    recent_4h["s1_weight"] = sim["effective_s1_weight"].reindex(recent_4h.index).fillna(0.0).astype(float)
    recent_4h["s2_weight"] = sim["effective_s2_weight"].reindex(recent_4h.index).fillna(0.0).astype(float)
    core_events = transition_events(recent_4h["core_target"], lambda x: x > 1e-9)
    s1_events = transition_events(recent_4h["s1_weight"], lambda x: x > 1e-9)
    s2_events = transition_events(recent_4h["s2_weight"], lambda x: x > 1e-9)
    flat_spans = contiguous_flat_spans(recent_4h["core_target"])

    payload = {
        "timestamp": latest["timestamp"],
        "state": str(state_series.iloc[-1]),
        "portfolio_state": latest["portfolio_state"],
        "core_riskoff_state": latest["core_riskoff_state"],
        "riskoff_active": latest["riskoff_active"],
        "core_exposure": latest["core_exposure"],
        "sleeve1_exposure": latest["sleeve1_exposure"],
        "sleeve2_exposure": latest["sleeve2_exposure"],
        "total_exposure": latest["total_exposure"],
        "cap_headroom": latest["cap_headroom"],
        "hard_cap": HARD_CAP,
        "soft_cap_band": latest["soft_cap_band"],
        "governance_alert_level": latest["governance_alert_level"],
        "core_reentry_family": latest["core_reentry_family"],
        "core_reentry_state": latest["core_reentry_state"],
        "core_reentry_gate": latest["core_reentry_gate"],
        "core_instability_state": latest["core_instability_state"],
        "core_instability_source": latest["core_instability_source"],
        "atr_scale": latest["atr_scale"],
        "hv_pct_180d": latest["hv_pct_180d"],
        "hv_forced_high_churn": latest["hv_forced_high_churn"],
        "current_drawdown_pct": latest["current_drawdown_pct"],
        "days_since_equity_high": latest["days_since_equity_high"],
        "trailing_3m_cluster_loss_pct": latest["trailing_3m_cluster_loss_pct"],
        "trailing_6m_cluster_loss_pct": latest["trailing_6m_cluster_loss_pct"],
        "preferred_onboarding": "immediate_full",
        "adopted_posture": ADOPTED_POSTURE,
        "recent_equity": equity.tail(180 * 6),
        "recent_total_exposure": total_exp.tail(180 * 6),
        "recent_ohlc": recent_4h[["open", "high", "low", "close", "ema250", "ema50", "core_target", "core_gate", "core_instability_state", "core_instability_source", "atr_scale", "hv_pct_180d", "s1_weight", "s2_weight"]],
        "core_events": core_events,
        "s1_events": s1_events,
        "s2_events": s2_events,
        "core_flat_spans": flat_spans,
        "data_freshness": freshness,
    }
    return payload
