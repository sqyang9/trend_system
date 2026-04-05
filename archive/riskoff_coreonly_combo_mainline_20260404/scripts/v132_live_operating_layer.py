#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate live operating layer artifacts for the adopted BTC mainline."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig")

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_asset_management_system_aligned import compute_metrics
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v92_const1x_deployment_audit import loss_cluster_diagnostics, path_diagnostics
from v123_formal_launch_and_layer2_weight_audit import SCENARIOS, base_bundle, simulate_weight_combo


ROOT = Path(__file__).resolve().parent
LIVE_PANEL_MD = ROOT / "LIVE_STATE_PANEL.md"
LIVE_PANEL_HTML = ROOT / "LIVE_STATE_PANEL.html"
LIVE_MEMO_MD = ROOT / "LIVE_DECISION_MEMO.md"
ONBOARDING_PLAYBOOK_MD = ROOT / "STARTUP_ONBOARDING_PLAYBOOK.md"
SNAPSHOT_JSON = ROOT / "live_state_snapshot.json"

ADOPTED_POSTURE = {
    "id": "adopted_posture_core1.00_s11.00_s21.00_atrvt",
    "core_weight": 1.00,
    "sleeve1_weight": 1.00,
    "sleeve2_weight": 1.00,
    "atr_vol_target_s1": True,
    "atr_vol_target_s2": True,
}
INIT_EQUITY = 10000.0
HARD_CAP = 3.0
STAGED_DAY_DELAYS = [0, 30, 60]


def metric_bundle(equity: pd.Series, exposure: pd.Series) -> Dict:
    return {
        "metrics": extended_metrics({"combo_equity": equity, "combo_metrics": compute_metrics(equity, exposure)}),
        "path": path_bundle(equity),
        "avg_total_exposure_pct": float(exposure.mean() * 100.0),
        "peak_total_exposure_pct": float(exposure.max() * 100.0),
    }


def path_bundle(equity: pd.Series) -> Dict:
    clusters = loss_cluster_diagnostics(equity)
    pdx = path_diagnostics(equity)
    maxdd_episode = pdx["worst_underwater_episodes"][0] if pdx["worst_underwater_episodes"] else None
    return {
        "worst_3m_cluster_return_pct": float(clusters["worst_3m_cluster_return_pct"]),
        "worst_6m_cluster_return_pct": float(clusters["worst_6m_cluster_return_pct"]),
        "recovery_days_from_maxdd": (
            float(maxdd_episode["recovery_days_from_trough"]) if maxdd_episode is not None else 0.0
        ),
        "rolling_180d_worst_maxdd_pct": float(pdx["rolling_180d"]["worst_maxdd_pct"]),
    }


def monthly_starts(index: pd.Index, first_date: str = "2020-01-01") -> List[pd.Timestamp]:
    idx = pd.DatetimeIndex(index).sort_values().unique()
    anchor = pd.Timestamp(first_date, tz="UTC")
    month_starts = pd.date_range(start=anchor.normalize(), end=idx[-1].normalize(), freq="MS", tz="UTC")
    out: List[pd.Timestamp] = []
    for dt in month_starts:
        pos = idx.searchsorted(dt)
        if pos < len(idx):
            out.append(idx[pos])
    return list(pd.DatetimeIndex(out).unique().sort_values())


def first_at_or_after(index: pd.Index, ts: pd.Timestamp) -> pd.Timestamp | None:
    pos = index.searchsorted(ts)
    if pos >= len(index):
        return None
    return pd.Timestamp(index[pos])


def classify_portfolio_state(core_exp: float, s1_exp: float, s2_exp: float, total_exp: float, drawdown_pct: float, days_since_high: float) -> str:
    if total_exp >= 2.5:
        return "Cap-Constrained Stacked"
    if drawdown_pct <= -45.0 or days_since_high > 300.0:
        return "Governance Attention"
    if s1_exp > 1e-9 and s2_exp > 1e-9:
        return "Stacked Multi-Sleeve"
    if s1_exp > 1e-9:
        return "Expansion-Carry"
    if s2_exp > 1e-9:
        return "Diversification-Carry"
    return "Core-Only"


def classify_core_riskoff_state(core_exp: float) -> str:
    if core_exp <= 1e-9:
        return "flat"
    if core_exp < ADOPTED_POSTURE["core_weight"] - 1e-9:
        return "soft_off"
    return "full"


def classify_soft_cap_band(total_exp: float) -> str:
    if total_exp >= 3.0:
        return "Breach"
    if total_exp >= 2.85:
        return "Pre-Breach"
    if total_exp >= 2.5:
        return "High-Use"
    if total_exp >= 2.0:
        return "Stacked"
    return "Normal"


def classify_governance_alert(drawdown_pct: float, days_since_high: float, worst_6m_pct: float, total_exp: float) -> str:
    if total_exp >= 3.0:
        return "Incident"
    if drawdown_pct <= -55.0 or days_since_high > 425.0 or worst_6m_pct <= -40.0:
        return "Escalate"
    if drawdown_pct <= -45.0 or days_since_high > 300.0 or worst_6m_pct <= -30.0:
        return "Review"
    if drawdown_pct <= -35.0 or days_since_high > 180.0:
        return "Observe"
    return "Normal"


def rolling_return(equity: pd.Series, bars: int) -> float:
    if len(equity) <= bars:
        return float("nan")
    return float(equity.iloc[-1] / equity.iloc[-bars - 1] - 1.0) * 100.0


def days_since_high(equity: pd.Series) -> pd.Series:
    last_high = equity.index[0]
    running_high = float("-inf")
    values = []
    for ts, value in equity.items():
        value = float(value)
        if value >= running_high - 1e-12:
            running_high = value
            last_high = ts
        values.append((ts - last_high).total_seconds() / 86400.0)
    return pd.Series(values, index=equity.index, dtype=float)


def build_state_series(core_exp: pd.Series, s1_exp: pd.Series, s2_exp: pd.Series) -> pd.Series:
    states = []
    for c, s1, s2 in zip(core_exp.astype(float), s1_exp.astype(float), s2_exp.astype(float)):
        core_state = "full" if c >= ADOPTED_POSTURE["core_weight"] - 1e-9 else "partial" if c > 1e-9 else "flat"
        states.append(f"core_{core_state}_s1_{1 if s1 > 1e-9 else 0}_s2_{1 if s2 > 1e-9 else 0}")
    return pd.Series(states, index=core_exp.index, dtype="object")


def rebase_from(series: pd.Series, start: pd.Timestamp) -> pd.Series:
    sub = series.loc[series.index >= start].astype(float)
    if sub.empty:
        return sub
    return INIT_EQUITY * sub / float(sub.iloc[0])


def immediate_entry(equity: pd.Series, exposure: pd.Series, start: pd.Timestamp) -> Dict | None:
    eq = rebase_from(equity, start)
    ex = exposure.loc[exposure.index >= start].astype(float)
    if len(eq) < 2:
        return None
    return {"equity": eq, "exposure": ex}


def staged_entry(equity: pd.Series, exposure: pd.Series, start: pd.Timestamp, delays_days: List[int]) -> Dict | None:
    base_index = equity.loc[equity.index >= start].index
    if len(base_index) < 2:
        return None
    combo_eq = pd.Series(0.0, index=base_index, dtype=float)
    combo_ex = pd.Series(0.0, index=base_index, dtype=float)
    tranche_weight = 1.0 / len(delays_days)
    for delay in delays_days:
        tranche_start = first_at_or_after(equity.index, start + pd.Timedelta(days=delay))
        tranche_eq = pd.Series(INIT_EQUITY * tranche_weight, index=base_index, dtype=float)
        tranche_ex = pd.Series(0.0, index=base_index, dtype=float)
        if tranche_start is not None and tranche_start <= base_index[-1]:
            active_eq = INIT_EQUITY * tranche_weight * equity.loc[equity.index >= tranche_start] / float(equity.loc[tranche_start])
            active_eq = active_eq.reindex(base_index[base_index >= tranche_start]).astype(float)
            tranche_eq.loc[active_eq.index] = active_eq
            active_ex = tranche_weight * exposure.loc[exposure.index >= tranche_start]
            active_ex = active_ex.reindex(base_index[base_index >= tranche_start]).astype(float)
            tranche_ex.loc[active_ex.index] = active_ex
        combo_eq = combo_eq + tranche_eq
        combo_ex = combo_ex + tranche_ex
    return {"equity": combo_eq, "exposure": combo_ex}


def wait_next_switch(equity: pd.Series, exposure: pd.Series, states: pd.Series, start: pd.Timestamp) -> Dict | None:
    current = states.loc[start]
    later = states.loc[states.index > start]
    changed = later[later != current]
    base_index = equity.loc[equity.index >= start].index
    if len(base_index) < 2:
        return None
    if changed.empty:
        return {"equity": pd.Series(INIT_EQUITY, index=base_index, dtype=float), "exposure": pd.Series(0.0, index=base_index, dtype=float)}
    switch_ts = changed.index[0]
    eq = pd.Series(INIT_EQUITY, index=base_index, dtype=float)
    ex = pd.Series(0.0, index=base_index, dtype=float)
    active_eq = INIT_EQUITY * equity.loc[equity.index >= switch_ts] / float(equity.loc[switch_ts])
    active_eq = active_eq.reindex(base_index[base_index >= switch_ts]).astype(float)
    eq.loc[active_eq.index] = active_eq
    active_ex = exposure.loc[exposure.index >= switch_ts].reindex(base_index[base_index >= switch_ts]).astype(float)
    ex.loc[active_ex.index] = active_ex
    return {"equity": eq, "exposure": ex}


def subperiod_return(equity: pd.Series, months: int) -> float | None:
    if equity.empty:
        return None
    target = equity.index[0] + pd.DateOffset(months=months)
    window = equity.loc[equity.index <= target]
    if len(window) < 2:
        return None
    return float(window.iloc[-1] / window.iloc[0] - 1.0) * 100.0


def current_state_onboarding_summary(equity: pd.Series, exposure: pd.Series, state_series: pd.Series, current_state: str) -> Dict:
    rows = []
    for start in monthly_starts(equity.index):
        if state_series.loc[start] != current_state:
            continue
        methods = {
            "immediate_full": immediate_entry(equity, exposure, start),
            "staged_30_60": staged_entry(equity, exposure, start, STAGED_DAY_DELAYS),
            "wait_next_switch": wait_next_switch(equity, exposure, state_series, start),
        }
        for method, result in methods.items():
            if result is None:
                continue
            mb = metric_bundle(result["equity"], result["exposure"])
            rows.append({
                "method": method,
                "ret_12m_pct": subperiod_return(result["equity"], 12),
                "calmar": mb["metrics"]["Calmar"],
                "maxdd_pct": mb["metrics"]["MaxDD_pct"],
                "worst_6m_cluster_pct": mb["path"]["worst_6m_cluster_return_pct"],
                "recovery_days": mb["path"]["recovery_days_from_maxdd"],
            })
    df = pd.DataFrame(rows)
    summary = {}
    if df.empty:
        return summary
    for method in sorted(df["method"].unique()):
        one = df[df["method"] == method]
        summary[method] = {
            "count": int(len(one)),
            "avg_12m_return_pct": float(one["ret_12m_pct"].dropna().mean()) if one["ret_12m_pct"].notna().any() else None,
            "median_12m_return_pct": float(one["ret_12m_pct"].dropna().median()) if one["ret_12m_pct"].notna().any() else None,
            "avg_calmar": float(one["calmar"].mean()),
            "avg_maxdd_pct": float(one["maxdd_pct"].mean()),
            "avg_worst6m_pct": float(one["worst_6m_cluster_pct"].mean()),
            "avg_recovery_days": float(one["recovery_days"].fillna(0.0).mean()),
        }
    return summary


def build_live_package() -> Dict:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    bundle = base_bundle(df_5m, df_4h, SCENARIOS[0])
    sim = simulate_weight_combo(bundle, ADOPTED_POSTURE)

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
    core_trace = bundle["core_trace_4h"].reindex(idx).ffill()
    core_instability = bundle["core_instability_4h"].reindex(idx).ffill()
    latest_atr_scale = float(sim["atr_scale"].reindex(idx).ffill().iloc[-1])
    latest_hv_pct = float(sim["hv_pct_180d"].reindex(idx).ffill().iloc[-1])
    latest = {
        "timestamp": str(latest_ts),
        "portfolio_state": classify_portfolio_state(float(core_exp.iloc[-1]), float(s1_exp.iloc[-1]), float(s2_exp.iloc[-1]), float(total_exp.iloc[-1]), float(dd.iloc[-1]), float(dsh.iloc[-1])),
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
        "atr_scale": latest_atr_scale,
        "hv_pct_180d": latest_hv_pct,
        "hv_forced_high_churn": bool(core_instability["hv_forced_high_churn"].iloc[-1]),
        "instability_source": str(core_instability["instability_source"].iloc[-1]),
        "core_reentry_family": str(bundle["core_trace_4h"].attrs.get("reentry_family", "state_aware_hybrid_close3")),
        "core_reentry_state": str(core_trace["state"].iloc[-1]),
        "core_reentry_gate": str(core_trace["active_gate"].iloc[-1]),
        "core_instability_state": str(core_trace["instability_state"].iloc[-1]),
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

    onboarding = current_state_onboarding_summary(equity, total_exp, state_series, state_series.iloc[-1])
    if onboarding:
        preferred_onboarding = sorted(
            onboarding.items(),
            key=lambda kv: (kv[1]["avg_calmar"], kv[1]["avg_12m_return_pct"] or -1e9),
            reverse=True,
        )[0][0]
    else:
        preferred_onboarding = "immediate_full"

    return {
        "equity": equity,
        "total_exposure": total_exp,
        "core_exposure": core_exp,
        "sleeve1_exposure": s1_exp,
        "sleeve2_exposure": s2_exp,
        "drawdown_pct": dd,
        "days_since_high": dsh,
        "state_series": state_series,
        "latest": latest,
        "metrics": sim["metrics"],
        "path": sim["path"],
        "onboarding": onboarding,
        "preferred_onboarding": preferred_onboarding,
        "core_trace_4h": core_trace,
        "core_instability_4h": core_instability,
        "atr_scale": sim["atr_scale"].reindex(idx).astype(float),
        "hv_pct_180d": sim["hv_pct_180d"].reindex(idx).astype(float),
    }


def memo_text(pkg: Dict) -> str:
    latest = pkg["latest"]
    expectation = "hold and continue observation"
    if latest["governance_alert_level"] in {"Review", "Escalate", "Incident"}:
        expectation = "lower expectations and review path burden closely"
    elif latest["portfolio_state"] in {"Expansion-Carry", "Stacked Multi-Sleeve"}:
        expectation = "hold with normal upside expectations"
    elif latest["portfolio_state"] == "Core-Only":
        expectation = "hold the core-dominant posture and continue observation"

    lines = [
        "# Live Decision Memo",
        "",
        f"- Timestamp: `{latest['timestamp']}`",
        f"- Current state: `{latest['portfolio_state']}` / core Risk-Off state `{latest['core_riskoff_state']}`",
        f"- Current exposures: `Core {latest['core_exposure']:.2f} / Sleeve1 {latest['sleeve1_exposure']:.2f} / Sleeve2 {latest['sleeve2_exposure']:.2f} / Total {latest['total_exposure']:.2f}`",
        f"- Cap headroom: `{latest['cap_headroom']:.2f}x` (`{latest['soft_cap_band']}` band)",
        f"- Path burden: drawdown `{latest['current_drawdown_pct']:.2f}%`, days since high `{latest['days_since_equity_high']:.1f}`, alert `{latest['governance_alert_level']}`",
        "",
        "## Operating Readout",
        "",
        f"- Current suggestion: `{expectation}`.",
        f"- New capital today: `{pkg['preferred_onboarding']}`.",
        "- Startup guidance: use `12m` warmup when practical, `6m` is acceptable, `3m` is too short.",
        "",
        "## Why",
        "",
        "- This memo converts the current-state analog onboarding audit and the latest portfolio-state snapshot into a one-line operating posture.",
        "- It does not add new trading signals; it translates the adopted baseline into live operating language.",
    ]
    return "\n".join(lines)


def playbook_text(pkg: Dict) -> str:
    lines = [
        "# Startup And Onboarding Playbook",
        "",
        "## Official Operating Baseline",
        "",
        "- Structure: `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`.",
        "- Adopted running posture: `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`.",
        "- Sleeve scaling: `S1 + S2 ATR vol-targeting`.",
        "- Risk-Off overlay: sell-side `EMA250`, stable re-entry `close3`, high-churn re-entry `strict EMA50 + breakout_4`, `HV percentile >= 85` forces the stricter gate earlier, override `Weekly RSI(14) <= 30 hold`.",
        "",
        "## New Capital Onboarding",
        "",
        "- Primary rule: read the live state panel first.",
        "- If current live state matches the present audited state family, preferred method is the current memo recommendation.",
        f"- Current audited recommendation: `{pkg['preferred_onboarding']}`.",
        "",
        "## Warmup Requirements",
        "",
        "- Preferred: `12m` prewarm.",
        "- Acceptable: `6m` prewarm.",
        "- Not recommended: `3m` prewarm only.",
        "- Full-history prewarm is not mandatory for practical operation.",
        "",
        "## Daily / Weekly Use",
        "",
        "- Daily: check current state, exposures, Risk-Off status, cap headroom, and path-burden alert level.",
        "- Weekly: check whether onboarding guidance or expected operating posture changed materially.",
        "- Do not reinterpret governance alerts as trading signals.",
    ]
    return "\n".join(lines)


def panel_text(pkg: Dict) -> str:
    latest = pkg["latest"]
    lines = [
        "# Live State Panel",
        "",
        "## Snapshot",
        "",
        f"- Timestamp: `{latest['timestamp']}`",
        f"- Portfolio state: `{latest['portfolio_state']}`",
        f"- Core Risk-Off state: `{latest['core_riskoff_state']}`",
        f"- Risk-Off active: `{latest['riskoff_active']}`",
        f"- Core exposure: `{latest['core_exposure']:.2f}`",
        f"- Sleeve #1 exposure: `{latest['sleeve1_exposure']:.2f}`",
        f"- Sleeve #2 exposure: `{latest['sleeve2_exposure']:.2f}`",
        f"- Total exposure: `{latest['total_exposure']:.2f}`",
        f"- ATR scale: `{latest['atr_scale']:.2f}x`",
        f"- HV percentile: `{latest['hv_pct_180d'] * 100.0:.1f}`",
        f"- Cap headroom: `{latest['cap_headroom']:.2f}x`",
        f"- Soft cap band: `{latest['soft_cap_band']}`",
        f"- Governance alert: `{latest['governance_alert_level']}`",
        f"- Core gate: `{latest['core_reentry_gate']}` / instability `{latest['core_instability_state']}` via `{latest['instability_source']}`",
        "",
        "## Path Burden",
        "",
        f"- Current drawdown: `{latest['current_drawdown_pct']:.2f}%`",
        f"- Days since equity high: `{latest['days_since_equity_high']:.1f}`",
        f"- Trailing 3m cluster loss: `{latest['trailing_3m_cluster_loss_pct']:.2f}%`",
        f"- Trailing 6m cluster loss: `{latest['trailing_6m_cluster_loss_pct']:.2f}%`",
        "",
        "## Current Memo",
        "",
        f"- Operating suggestion: `{pkg['preferred_onboarding']}` for new capital, maintain `{latest['portfolio_state']}` posture for existing capital unless the live alert regime changes.",
    ]
    return "\n".join(lines)


def build_html(pkg: Dict) -> str:
    latest = pkg["latest"]
    recent_idx = pkg["equity"].index[-365 * 6 :] if len(pkg["equity"]) > 365 * 6 else pkg["equity"].index
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.18, 0.27, 0.27, 0.28],
        subplot_titles=("Exposure Stack", "Equity", "Underwater", "Days Since Equity High"),
    )
    fig.add_trace(go.Scatter(x=recent_idx, y=pkg["core_exposure"].reindex(recent_idx), name="Core", stackgroup="one"), row=1, col=1)
    fig.add_trace(go.Scatter(x=recent_idx, y=pkg["sleeve1_exposure"].reindex(recent_idx), name="Sleeve #1", stackgroup="one"), row=1, col=1)
    fig.add_trace(go.Scatter(x=recent_idx, y=pkg["sleeve2_exposure"].reindex(recent_idx), name="Sleeve #2", stackgroup="one"), row=1, col=1)
    fig.add_trace(go.Scatter(x=recent_idx, y=pkg["total_exposure"].reindex(recent_idx), name="Total", line=dict(color="#111827", dash="dot")), row=1, col=1)
    fig.add_hline(y=3.0, row=1, col=1, line_color="#dc2626", line_dash="dash")
    fig.add_trace(go.Scatter(x=recent_idx, y=pkg["equity"].reindex(recent_idx), name="Equity", line=dict(color="#0f172a", width=2.2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=recent_idx, y=pkg["drawdown_pct"].reindex(recent_idx), name="Drawdown %", line=dict(color="#dc2626", width=1.8)), row=3, col=1)
    fig.add_trace(go.Scatter(x=recent_idx, y=pkg["days_since_high"].reindex(recent_idx), name="Days Since High", line=dict(color="#2563eb", width=1.8)), row=4, col=1)
    fig.update_layout(
        template="plotly_white",
        height=1100,
        hovermode="x unified",
        title=(
            "Adopted Mainline Live State Panel"
            f"<br><sup>State={latest['portfolio_state']} | Core={latest['core_exposure']:.2f} "
            f"S1={latest['sleeve1_exposure']:.2f} S2={latest['sleeve2_exposure']:.2f} "
            f"Total={latest['total_exposure']:.2f} | Headroom={latest['cap_headroom']:.2f}x | "
            f"ATR={latest['atr_scale']:.2f}x | HV={latest['hv_pct_180d'] * 100.0:.1f} | Onboarding={pkg['preferred_onboarding']}</sup>"
        ),
    )
    fig.update_yaxes(title_text="Exposure", row=1, col=1)
    fig.update_yaxes(title_text="Equity", row=2, col=1)
    fig.update_yaxes(title_text="Drawdown %", row=3, col=1)
    fig.update_yaxes(title_text="Days", row=4, col=1)
    return fig.to_html(full_html=True, include_plotlyjs=True)


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    pkg = build_live_package()
    LIVE_MEMO_MD.write_text(memo_text(pkg), encoding="utf-8")
    ONBOARDING_PLAYBOOK_MD.write_text(playbook_text(pkg), encoding="utf-8")
    LIVE_PANEL_MD.write_text(panel_text(pkg), encoding="utf-8")
    LIVE_PANEL_HTML.write_text(build_html(pkg), encoding="utf-8")
    SNAPSHOT_JSON.write_text(
        json.dumps(
            {
                "latest": pkg["latest"],
                "onboarding": pkg["onboarding"],
                "preferred_onboarding": pkg["preferred_onboarding"],
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "panel_md": LIVE_PANEL_MD.name,
            "panel_html": LIVE_PANEL_HTML.name,
            "memo_md": LIVE_MEMO_MD.name,
            "playbook_md": ONBOARDING_PLAYBOOK_MD.name,
            "snapshot_json": SNAPSHOT_JSON.name,
        },
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
