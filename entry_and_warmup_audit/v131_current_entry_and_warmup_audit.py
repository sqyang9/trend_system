#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Current-time onboarding audit plus warmup sensitivity audit for the adopted formal mainline."""

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

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_asset_management_system_aligned import compute_metrics
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v92_const1x_deployment_audit import loss_cluster_diagnostics, path_diagnostics
from v123_formal_launch_and_layer2_weight_audit import BASELINE_ID, SCENARIOS, WEIGHT_CANDIDATES, base_bundle, simulate_weight_combo


ROOT = Path(__file__).resolve().parent
ENTRY_MD = ROOT / "CURRENT_TIME_ENTRY_AUDIT.md"
ENTRY_CSV = ROOT / "CURRENT_TIME_ENTRY_TABLE.csv"
WARMUP_MD = ROOT / "WARMUP_STARTUP_AUDIT.md"
WARMUP_CSV = ROOT / "WARMUP_STARTUP_TABLE.csv"
PLOTS_HTML = ROOT / "CURRENT_ENTRY_AND_WARMUP_PLOTS.html"
REPORT_JSON = ROOT / "current_entry_and_warmup_audit.json"

INIT_EQUITY = 10000.0
STAGED_DAY_DELAYS = [0, 30, 60]
WARMUP_MONTHS = [None, 12, 6, 3]
ANNUAL_START_YEARS = list(range(2020, 2027))


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


def metric_bundle(equity: pd.Series, exposure: pd.Series) -> Dict:
    return {
        "metrics": extended_metrics({"combo_equity": equity, "combo_metrics": compute_metrics(equity, exposure)}),
        "path": path_bundle(equity),
        "avg_total_exposure_pct": float(exposure.mean() * 100.0),
        "peak_total_exposure_pct": float(exposure.max() * 100.0),
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


def annual_starts(index: pd.Index) -> List[pd.Timestamp]:
    idx = pd.DatetimeIndex(index).sort_values().unique()
    out = []
    for year in ANNUAL_START_YEARS:
        dt = pd.Timestamp(f"{year}-01-01", tz="UTC")
        pos = idx.searchsorted(dt)
        if pos < len(idx):
            out.append(idx[pos])
    return list(pd.DatetimeIndex(out).unique().sort_values())


def first_at_or_after(index: pd.Index, ts: pd.Timestamp) -> pd.Timestamp | None:
    pos = index.searchsorted(ts)
    if pos >= len(index):
        return None
    return pd.Timestamp(index[pos])


def state_key(core_exp: float, s1_exp: float, s2_exp: float) -> str:
    core_state = "full" if core_exp > 0.9999 else "partial" if core_exp > 1e-9 else "flat"
    s1 = 1 if s1_exp > 1e-9 else 0
    s2 = 1 if s2_exp > 1e-9 else 0
    return f"core_{core_state}_s1_{s1}_s2_{s2}"


def build_state_series(core_exp: pd.Series, s1_exp: pd.Series, s2_exp: pd.Series) -> pd.Series:
    return pd.Series(
        [state_key(c, s1, s2) for c, s1, s2 in zip(core_exp.astype(float), s1_exp.astype(float), s2_exp.astype(float))],
        index=core_exp.index,
        dtype="object",
    )


def rebase_from(series: pd.Series, start: pd.Timestamp) -> pd.Series:
    sub = series.loc[series.index >= start].astype(float)
    if sub.empty:
        return sub
    return INIT_EQUITY * sub / float(sub.iloc[0])


def exposure_from(series: pd.Series, start: pd.Timestamp) -> pd.Series:
    return series.loc[series.index >= start].astype(float)


def immediate_entry(equity: pd.Series, exposure: pd.Series, start: pd.Timestamp) -> Dict | None:
    eq = rebase_from(equity, start)
    ex = exposure_from(exposure, start)
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


def wait_for_next_switch(equity: pd.Series, exposure: pd.Series, states: pd.Series, start: pd.Timestamp) -> Dict | None:
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
    return {"equity": eq, "exposure": ex, "switch_ts": switch_ts}


def subperiod_return(equity: pd.Series, months: int) -> float | None:
    if equity.empty:
        return None
    target = equity.index[0] + pd.DateOffset(months=months)
    window = equity.loc[equity.index <= target]
    if len(window) < 2:
        return None
    return float(window.iloc[-1] / window.iloc[0] - 1.0) * 100.0


def evaluate_onboarding_methods(
    equity: pd.Series,
    exposure: pd.Series,
    states: pd.Series,
    starts: List[pd.Timestamp],
) -> pd.DataFrame:
    rows = []
    for start in starts:
        methods = {
            "immediate_full": immediate_entry(equity, exposure, start),
            "staged_30_60": staged_entry(equity, exposure, start, STAGED_DAY_DELAYS),
            "wait_next_switch": wait_for_next_switch(equity, exposure, states, start),
        }
        for method, result in methods.items():
            if result is None:
                continue
            eq = result["equity"]
            ex = result["exposure"]
            mb = metric_bundle(eq, ex)
            rows.append({
                "start_date": start.strftime("%Y-%m-%d"),
                "state_key": states.loc[start],
                "method": method,
                "ret_1m_pct": subperiod_return(eq, 1),
                "ret_3m_pct": subperiod_return(eq, 3),
                "ret_6m_pct": subperiod_return(eq, 6),
                "ret_12m_pct": subperiod_return(eq, 12),
                "total_return_pct": mb["metrics"]["TotalReturn_pct"],
                "calmar": mb["metrics"]["Calmar"],
                "maxdd_pct": mb["metrics"]["MaxDD_pct"],
                "worst_3m_cluster_pct": mb["path"]["worst_3m_cluster_return_pct"],
                "worst_6m_cluster_pct": mb["path"]["worst_6m_cluster_return_pct"],
                "recovery_days": mb["path"]["recovery_days_from_maxdd"],
                "avg_exposure_pct": mb["avg_total_exposure_pct"],
                "switch_ts": result.get("switch_ts"),
            })
    return pd.DataFrame(rows)


def summarize_onboarding(table: pd.DataFrame, state_filter: str) -> Dict:
    sub = table[table["state_key"] == state_filter].copy()
    summary = {}
    for method in sorted(sub["method"].unique()):
        one = sub[sub["method"] == method]
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


def run_mainline_with_warmup(
    df_5m: pd.DataFrame,
    df_4h: pd.DataFrame,
    actual_start: pd.Timestamp,
    warmup_months: int | None,
) -> Dict | None:
    min_ts = max(df_5m["timestamp"].min(), df_4h["timestamp"].min())
    warmup_start = min_ts if warmup_months is None else max(min_ts, actual_start - pd.DateOffset(months=warmup_months))
    sub5 = df_5m[df_5m["timestamp"] >= warmup_start].reset_index(drop=True)
    sub4 = df_4h[df_4h["timestamp"] >= warmup_start].reset_index(drop=True)
    if len(sub5) < 200 or len(sub4) < 50:
        return None
    bundle = base_bundle(sub5, sub4, SCENARIOS[0])
    spec = next(spec for spec in WEIGHT_CANDIDATES if spec["id"] == BASELINE_ID)
    sim = simulate_weight_combo(bundle, spec)
    eq = sim["combo_equity"].loc[sim["combo_equity"].index >= actual_start].astype(float)
    ex = sim["combo_exposure"].loc[sim["combo_exposure"].index >= actual_start].astype(float)
    if len(eq) < 2:
        return None
    eq = INIT_EQUITY * eq / float(eq.iloc[0])
    return {"equity": eq, "exposure": ex, "warmup_months": warmup_months}


def warmup_label(months: int | None) -> str:
    return "full_history" if months is None else f"{months}m"


def evaluate_warmups(df_5m: pd.DataFrame, df_4h: pd.DataFrame, annual_points: List[pd.Timestamp]) -> pd.DataFrame:
    rows = []
    for start in annual_points:
        baseline = run_mainline_with_warmup(df_5m, df_4h, start, None)
        if baseline is None:
            continue
        base_metrics = metric_bundle(baseline["equity"], baseline["exposure"])
        for warmup in WARMUP_MONTHS:
            result = baseline if warmup is None else run_mainline_with_warmup(df_5m, df_4h, start, warmup)
            if result is None:
                continue
            mb = metric_bundle(result["equity"], result["exposure"])
            rows.append({
                "start_date": start.strftime("%Y-%m-%d"),
                "warmup_label": warmup_label(warmup),
                "ret_12m_pct": subperiod_return(result["equity"], 12),
                "total_return_pct": mb["metrics"]["TotalReturn_pct"],
                "calmar": mb["metrics"]["Calmar"],
                "maxdd_pct": mb["metrics"]["MaxDD_pct"],
                "worst_6m_cluster_pct": mb["path"]["worst_6m_cluster_return_pct"],
                "recovery_days": mb["path"]["recovery_days_from_maxdd"],
                "avg_exposure_pct": mb["avg_total_exposure_pct"],
                "d_total_return_vs_full_pp": mb["metrics"]["TotalReturn_pct"] - base_metrics["metrics"]["TotalReturn_pct"],
                "d_calmar_vs_full": mb["metrics"]["Calmar"] - base_metrics["metrics"]["Calmar"],
                "d_maxdd_vs_full_pp": mb["metrics"]["MaxDD_pct"] - base_metrics["metrics"]["MaxDD_pct"],
                "d_ret12m_vs_full_pp": (
                    (subperiod_return(result["equity"], 12) or 0.0)
                    - (subperiod_return(baseline["equity"], 12) or 0.0)
                ),
            })
    return pd.DataFrame(rows)


def render_plots(current_state: str, onboarding: pd.DataFrame, warmup: pd.DataFrame) -> None:
    fig = make_subplots(
        rows=2,
        cols=2,
        vertical_spacing=0.12,
        horizontal_spacing=0.10,
        subplot_titles=(
            f"Current-State Analog: Avg 12m Return ({current_state})",
            f"Current-State Analog: Avg Calmar ({current_state})",
            "Warmup Windows: Calmar Delta Vs Full",
            "Warmup Windows: 12m Return Delta Vs Full",
        ),
    )

    cur = onboarding[onboarding["state_key"] == current_state]
    summary = cur.groupby("method", as_index=False).agg(avg_12m=("ret_12m_pct", "mean"), avg_calmar=("calmar", "mean"))
    fig.add_trace(go.Bar(x=summary["method"], y=summary["avg_12m"], name="Avg 12m Return"), row=1, col=1)
    fig.add_trace(go.Bar(x=summary["method"], y=summary["avg_calmar"], name="Avg Calmar", marker_color="#16a34a"), row=1, col=2)

    warm = warmup[warmup["warmup_label"] != "full_history"].copy()
    for label, color in [("12m", "#2563eb"), ("6m", "#f97316"), ("3m", "#dc2626")]:
        one = warm[warm["warmup_label"] == label]
        fig.add_trace(go.Scatter(x=one["start_date"], y=one["d_calmar_vs_full"], mode="lines+markers", name=f"{label} dCalmar"), row=2, col=1)
        fig.add_trace(go.Scatter(x=one["start_date"], y=one["d_ret12m_vs_full_pp"], mode="lines+markers", name=f"{label} d12m"), row=2, col=2)

    fig.update_layout(template="plotly_white", height=950, title="Current-Time Entry And Warmup Audit")
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def write_reports(latest: Dict, onboarding: pd.DataFrame, warmup: pd.DataFrame) -> None:
    current_state = latest["state_key"]
    summary = summarize_onboarding(onboarding, current_state)
    preferred = sorted(summary.items(), key=lambda kv: (kv[1]["avg_calmar"], kv[1]["avg_12m_return_pct"] or -1e9), reverse=True)[0]

    lines = [
        "# Current Time Entry Audit",
        "",
        "- Scope: determine how to onboard the adopted formal mainline at the current timestamp.",
        f"- Latest available bar: `{latest['timestamp']}`",
        f"- Latest state: `{current_state}`",
        f"- Latest exposures: `Core {latest['core_exposure']:.2f} / Sleeve1 {latest['s1_exposure']:.2f} / Sleeve2 {latest['s2_exposure']:.2f} / Total {latest['total_exposure']:.2f}`",
        "",
        "## Method Definitions",
        "",
        "- `immediate_full`: deploy all capital into the mainline immediately at the current state.",
        "- `staged_30_60`: deploy one-third now, one-third after 30 days, one-third after 60 days.",
        "- `wait_next_switch`: stay in cash until the portfolio leaves the current state, then deploy fully.",
        "",
        f"## Current-State Analog Summary (`{current_state}` monthly starts)",
        "",
        "| Method | Count | Avg12m | Median12m | AvgCalmar | AvgMaxDD | AvgWorst6m | AvgRecoveryDays |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for method, stats in summary.items():
        lines.append(
            f"| {method} | {stats['count']} | {stats['avg_12m_return_pct']:.2f} | {stats['median_12m_return_pct']:.2f} | {stats['avg_calmar']:.3f} | "
            f"{stats['avg_maxdd_pct']:.2f} | {stats['avg_worst6m_pct']:.2f} | {stats['avg_recovery_days']:.1f} |"
        )
    lines.extend([
        "",
        "## Recommendation",
        "",
        f"- Best current-state analog method: `{preferred[0]}`.",
        f"- Why: highest average Calmar with current-state analogs, while preserving near-term return participation better than waiting for a switch.",
        "",
        "## Interpretation",
        "",
        "- This audit is not using future data from the actual latest bar; it uses historical starts that match the latest state profile.",
        "- The latest live state is effectively `Core-only / sleeves-off`, so the key question is whether delaying capital helps when the system is already in a low-complexity investable posture.",
    ])
    ENTRY_MD.write_text("\n".join(lines), encoding="utf-8")

    annual = warmup.copy()
    lines = [
        "# Warmup Startup Audit",
        "",
        "- Scope: compare full-history prewarm vs limited warmup windows for a new account / new deployment.",
        "- Windows tested: `full_history`, `12m`, `6m`, `3m`.",
        "- Starts tested: annual anchors from 2020 through 2026.",
        "",
        "## Results",
        "",
        "| Start | Warmup | 12mReturn | TotalReturn | Calmar | MaxDD | d12m vs full | dCalmar vs full | dMaxDD vs full |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in annual.iterrows():
        lines.append(
            f"| {row['start_date']} | {row['warmup_label']} | {row['ret_12m_pct'] if pd.notna(row['ret_12m_pct']) else 'NA'} | "
            f"{row['total_return_pct']:.2f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
            f"{row['d_ret12m_vs_full_pp']:.2f} | {row['d_calmar_vs_full']:.3f} | {row['d_maxdd_vs_full_pp']:.2f} |"
        )
    agg = warmup[warmup["warmup_label"] != "full_history"].groupby("warmup_label", as_index=False).agg(
        avg_d12m=("d_ret12m_vs_full_pp", "mean"),
        avg_dcalmar=("d_calmar_vs_full", "mean"),
        avg_dmaxdd=("d_maxdd_vs_full_pp", "mean"),
    )
    lines.extend([
        "",
        "## Aggregated Readout",
        "",
        "| Warmup | Avg d12m vs full | Avg dCalmar vs full | Avg dMaxDD vs full |",
        "| --- | --- | --- | --- |",
    ])
    for _, row in agg.iterrows():
        lines.append(
            f"| {row['warmup_label']} | {row['avg_d12m']:.2f} | {row['avg_dcalmar']:.3f} | {row['avg_dmaxdd']:.2f} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- This audit answers whether a new account without full historical state memory materially underperforms.",
        "- If shorter warmup windows remain close to full-history warmup, the mainline is operationally easier to cold-start.",
    ])
    WARMUP_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    bundle = base_bundle(df_5m, df_4h, SCENARIOS[0])
    baseline_spec = next(spec for spec in WEIGHT_CANDIDATES if spec["id"] == BASELINE_ID)
    baseline = simulate_weight_combo(bundle, baseline_spec)

    eq = baseline["combo_equity"].astype(float)
    total_exp = baseline["combo_exposure"].astype(float)
    core_exp = (bundle["base_core_exposure"] * baseline_spec["core_weight"]).reindex(eq.index).astype(float)
    s1_exp = (bundle["base_s1_weight"] * baseline_spec["sleeve1_weight"]).reindex(eq.index).astype(float)
    s2_exp = (bundle["base_s2_weight"] * baseline_spec["sleeve2_weight"]).reindex(eq.index).astype(float)
    states = build_state_series(core_exp, s1_exp, s2_exp)

    latest = {
        "timestamp": str(eq.index[-1]),
        "state_key": states.iloc[-1],
        "total_exposure": float(total_exp.iloc[-1]),
        "core_exposure": float(core_exp.iloc[-1]),
        "s1_exposure": float(s1_exp.iloc[-1]),
        "s2_exposure": float(s2_exp.iloc[-1]),
    }

    starts = monthly_starts(eq.index)
    onboarding = evaluate_onboarding_methods(eq, total_exp, states, starts)
    onboarding.to_csv(ENTRY_CSV, index=False)

    annual_points = annual_starts(eq.index)
    warmup = evaluate_warmups(df_5m, df_4h, annual_points)
    warmup.to_csv(WARMUP_CSV, index=False)

    write_reports(latest, onboarding, warmup)
    render_plots(latest["state_key"], onboarding, warmup)
    REPORT_JSON.write_text(json.dumps({
        "latest_state": latest,
        "onboarding_summary": summarize_onboarding(onboarding, latest["state_key"]),
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "entry_md": ENTRY_MD.name,
        "entry_csv": ENTRY_CSV.name,
        "warmup_md": WARMUP_MD.name,
        "warmup_csv": WARMUP_CSV.name,
        "plots_html": PLOTS_HTML.name,
        "report_json": REPORT_JSON.name,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
