#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rolling start-point audit for the current adopted formal mainline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v92_const1x_deployment_audit import loss_cluster_diagnostics, path_diagnostics
from v123_formal_launch_and_layer2_weight_audit import (
    BASELINE_ID,
    SCENARIOS,
    WEIGHT_CANDIDATES,
    base_bundle,
    simulate_weight_combo,
)


OUT_DIR = Path("entry_and_warmup_audit")
REPORT_MD = OUT_DIR / "FORMAL_MAINLINE_ROLLING_START_AUDIT.md"
TABLE_CSV = OUT_DIR / "FORMAL_MAINLINE_ROLLING_START_TABLE.csv"
SUMMARY_JSON = OUT_DIR / "formal_mainline_rolling_start_summary.json"
CHART_DIR = Path("formal_mainline_rolling_start_charts")
INIT_EQUITY = 10000.0


def compute_subperiod_return(equity: pd.Series, months: int) -> float | None:
    if equity.empty:
        return None
    start = equity.index[0]
    target = start + pd.DateOffset(months=months)
    window = equity.loc[equity.index <= target]
    if len(window) < 2:
        return None
    return float(window.iloc[-1] / window.iloc[0] - 1.0) * 100.0


def find_recovery_days(equity: pd.Series) -> float | None:
    pdx = path_diagnostics(equity)
    episodes = pdx["worst_underwater_episodes"]
    if not episodes:
        return 0.0
    episode = episodes[0]
    value = episode.get("recovery_days_from_trough")
    return float(value) if value is not None else None


def monthly_starts(index: pd.Index, first_date: str = "2020-01-01") -> List[pd.Timestamp]:
    idx = pd.DatetimeIndex(index).sort_values().unique()
    start_anchor = pd.Timestamp(first_date, tz="UTC")
    month_starts = pd.date_range(start=start_anchor.normalize(), end=idx[-1].normalize(), freq="MS", tz="UTC")
    out: List[pd.Timestamp] = []
    for dt in month_starts:
        pos = idx.searchsorted(dt)
        if pos < len(idx):
            out.append(idx[pos])
    dedup = pd.DatetimeIndex(out).unique().sort_values()
    return list(dedup)


def annual_starts(index: pd.Index) -> List[pd.Timestamp]:
    years = list(range(2020, 2027))
    idx = pd.DatetimeIndex(index).sort_values().unique()
    out = []
    for year in years:
        dt = pd.Timestamp(f"{year}-01-01", tz="UTC")
        pos = idx.searchsorted(dt)
        if pos < len(idx):
            out.append(idx[pos])
    return list(pd.DatetimeIndex(out).unique().sort_values())


def build_rebased_slice(series: pd.Series, start: pd.Timestamp) -> pd.Series:
    sub = series.loc[series.index >= start].astype(float)
    if sub.empty:
        return sub
    return INIT_EQUITY * (sub / float(sub.iloc[0]))


def path_bundle(equity: pd.Series) -> Dict:
    clusters = loss_cluster_diagnostics(equity)
    pdx = path_diagnostics(equity)
    return {
        "worst_3m_cluster_return_pct": float(clusters["worst_3m_cluster_return_pct"]),
        "worst_6m_cluster_return_pct": float(clusters["worst_6m_cluster_return_pct"]),
        "recovery_days_from_maxdd": find_recovery_days(equity),
        "rolling_180d_worst_maxdd_pct": float(pdx["rolling_180d"]["worst_maxdd_pct"]),
    }


def compute_slice_metrics(equity: pd.Series) -> Dict:
    if len(equity) < 2:
        return {}
    returns = equity.pct_change().fillna(0.0)
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0) * 100.0
    elapsed_years = max((equity.index[-1] - equity.index[0]).total_seconds() / (365.25 * 24 * 3600), 1e-9)
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / elapsed_years) - 1.0) * 100.0
    dd = equity / equity.cummax() - 1.0
    maxdd = float(dd.min()) * 100.0
    sharpe = float((returns.mean() / returns.std()) * np.sqrt(6 * 365)) if returns.std() > 1e-12 else 0.0
    calmar = float(cagr / abs(maxdd)) if maxdd < 0 else 0.0
    return {
        "TotalReturn_pct": total_return,
        "CAGR_pct": cagr,
        "Sharpe": sharpe,
        "Calmar": calmar,
        "MaxDD_pct": maxdd,
    }


def make_chart(start: pd.Timestamp, data: Dict[str, pd.Series]) -> Path:
    label = start.strftime("%Y-%m-%d")
    out = CHART_DIR / f"rolling_start_{label}.html"
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.58, 0.42],
        subplot_titles=(f"Equity From {label}", "Exposure Composition"),
    )
    fig.add_trace(
        go.Scatter(x=data["equity"].index, y=data["equity"], mode="lines", name="Formal Equity", line=dict(color="#0f172a", width=2.4)),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=data["core_exposure"].index, y=data["core_exposure"] * 100.0, stackgroup="one", name="Core", line=dict(color="#1d4ed8", width=1.3)),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=data["s1_exposure"].index, y=data["s1_exposure"] * 100.0, stackgroup="one", name="Sleeve #1", line=dict(color="#059669", width=1.3)),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=data["s2_exposure"].index, y=data["s2_exposure"] * 100.0, stackgroup="one", name="Sleeve #2", line=dict(color="#f97316", width=1.3)),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(x=data["total_exposure"].index, y=data["total_exposure"] * 100.0, mode="lines", name="Total Exposure", line=dict(color="#7c3aed", width=2.0, dash="dot")),
        row=2,
        col=1,
    )
    fig.add_hline(y=300.0, row=2, col=1, line_width=1.2, line_dash="dash", line_color="#ef4444")
    fig.update_layout(template="plotly_white", hovermode="x unified", height=920, title=f"Formal Mainline Rolling Start: {label}")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Exposure %", row=2, col=1)
    out.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")
    return out


def main() -> None:
    CHART_DIR.mkdir(exist_ok=True)
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    default_bundle = base_bundle(df_5m, df_4h, SCENARIOS[0])
    baseline_spec = next(spec for spec in WEIGHT_CANDIDATES if spec["id"] == BASELINE_ID)
    baseline = simulate_weight_combo(default_bundle, baseline_spec)

    full_metrics = baseline["metrics"]
    full_path = baseline["path"]

    equity_full = baseline["combo_equity"].astype(float)
    total_exp_full = baseline["combo_exposure"].astype(float)
    core_exp_full = (default_bundle["base_core_exposure"] * baseline_spec["core_weight"]).reindex(equity_full.index).astype(float)
    s1_exp_full = (default_bundle["base_s1_weight"] * baseline_spec["sleeve1_weight"]).reindex(equity_full.index).astype(float)
    s2_exp_full = (default_bundle["base_s2_weight"] * baseline_spec["sleeve2_weight"]).reindex(equity_full.index).astype(float)

    rows = []
    chart_paths = []
    month_points = monthly_starts(equity_full.index)
    year_points = set(annual_starts(equity_full.index))

    for start in month_points:
        eq = build_rebased_slice(equity_full, start)
        total_exp = total_exp_full.loc[total_exp_full.index >= start]
        core_exp = core_exp_full.loc[core_exp_full.index >= start]
        s1_exp = s1_exp_full.loc[s1_exp_full.index >= start]
        s2_exp = s2_exp_full.loc[s2_exp_full.index >= start]

        if len(eq) < 50:
            continue

        metrics = compute_slice_metrics(eq)
        path = path_bundle(eq)
        row = {
            "start_date": start.strftime("%Y-%m-%d"),
            "bars": int(len(eq)),
            "months_observed": float((eq.index[-1] - eq.index[0]).days / 30.44),
            "ret_1m_pct": compute_subperiod_return(eq, 1),
            "ret_3m_pct": compute_subperiod_return(eq, 3),
            "ret_6m_pct": compute_subperiod_return(eq, 6),
            "ret_12m_pct": compute_subperiod_return(eq, 12),
            "total_return_pct": metrics["TotalReturn_pct"],
            "cagr_pct": metrics["CAGR_pct"],
            "calmar": metrics["Calmar"],
            "sharpe": metrics["Sharpe"],
            "maxdd_pct": metrics["MaxDD_pct"],
            "worst_3m_cluster_pct": path["worst_3m_cluster_return_pct"],
            "worst_6m_cluster_pct": path["worst_6m_cluster_return_pct"],
            "recovery_days_from_maxdd": path["recovery_days_from_maxdd"],
            "rolling_180d_worst_maxdd_pct": path["rolling_180d_worst_maxdd_pct"],
            "avg_total_exposure_pct": float(total_exp.mean() * 100.0),
            "avg_core_exposure_pct": float(core_exp.mean() * 100.0),
            "avg_sleeve1_exposure_pct": float(s1_exp.mean() * 100.0),
            "avg_sleeve2_exposure_pct": float(s2_exp.mean() * 100.0),
            "peak_total_exposure_pct": float(total_exp.max() * 100.0),
            "d_total_return_vs_full_pp": metrics["TotalReturn_pct"] - full_metrics["TotalReturn_pct"],
            "d_calmar_vs_full": metrics["Calmar"] - full_metrics["Calmar"],
            "d_maxdd_vs_full_pp": metrics["MaxDD_pct"] - full_metrics["MaxDD_pct"],
            "d_recovery_vs_full_days": (path["recovery_days_from_maxdd"] or 0.0) - (full_path["recovery_days_from_maxdd"] or 0.0),
        }
        rows.append(row)

        if start in year_points:
            chart_paths.append(
                {
                    "start_date": row["start_date"],
                    "path": str(
                        make_chart(
                            start,
                            {
                                "equity": eq,
                                "core_exposure": core_exp,
                                "s1_exposure": s1_exp,
                                "s2_exposure": s2_exp,
                                "total_exposure": total_exp,
                            },
                        )
                    ),
                }
            )

    table = pd.DataFrame(rows).sort_values("start_date").reset_index(drop=True)
    TABLE_CSV.write_text(table.to_csv(index=False), encoding="utf-8")

    yearly_table = table[table["start_date"].str.endswith("-01-01")].copy()
    summary = {
        "formal_full_sample": {
            "total_return_pct": float(full_metrics["TotalReturn_pct"]),
            "calmar": float(full_metrics["Calmar"]),
            "maxdd_pct": float(full_metrics["MaxDD_pct"]),
            "worst_3m_cluster_pct": float(full_path["worst_3m_cluster_return_pct"]),
            "worst_6m_cluster_pct": float(full_path["worst_6m_cluster_return_pct"]),
            "recovery_days_from_maxdd": float(full_path["recovery_days_from_maxdd"] or 0.0),
        },
        "monthly_start_count": int(len(table)),
        "annual_chart_count": int(len(chart_paths)),
        "best_calmar_start": table.sort_values("calmar", ascending=False).iloc[0].to_dict() if not table.empty else {},
        "worst_calmar_start": table.sort_values("calmar", ascending=True).iloc[0].to_dict() if not table.empty else {},
        "best_12m_start": table.dropna(subset=["ret_12m_pct"]).sort_values("ret_12m_pct", ascending=False).iloc[0].to_dict() if table["ret_12m_pct"].notna().any() else {},
        "worst_12m_start": table.dropna(subset=["ret_12m_pct"]).sort_values("ret_12m_pct", ascending=True).iloc[0].to_dict() if table["ret_12m_pct"].notna().any() else {},
        "chart_paths": chart_paths,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    lines = [
        "# Formal Mainline Rolling Start Audit",
        "",
        "- Scope: start-date sensitivity test on the current official mainline.",
        "- Mainline under test:",
        "  - `Core BTC holding + ConstAddOn[1.00x] + RangeRotation + core-only Risk-Off overlay`",
        "  - sell-side `EMA250`",
        "  - re-entry `Weekly RSI(14) <= 30 hold`",
        "  - posture `Core 1.00 / Sleeve1 1.00 / Sleeve2 1.00`",
        "",
        "## Full-Sample Reference",
        "",
        f"- Return: `{full_metrics['TotalReturn_pct']:.2f}%`",
        f"- Calmar: `{full_metrics['Calmar']:.3f}`",
        f"- MaxDD: `{full_metrics['MaxDD_pct']:.2f}%`",
        f"- Worst 3m cluster: `{full_path['worst_3m_cluster_return_pct']:.2f}%`",
        f"- Worst 6m cluster: `{full_path['worst_6m_cluster_return_pct']:.2f}%`",
        f"- Recovery from max DD: `{float(full_path['recovery_days_from_maxdd'] or 0.0):.1f} days`",
        "",
        "## Monthly Start Summary",
        "",
        f"- Monthly start points tested: `{len(table)}`",
        f"- Best Calmar start: `{summary['best_calmar_start'].get('start_date', 'n/a')}` -> `{summary['best_calmar_start'].get('calmar', np.nan):.3f}`",
        f"- Worst Calmar start: `{summary['worst_calmar_start'].get('start_date', 'n/a')}` -> `{summary['worst_calmar_start'].get('calmar', np.nan):.3f}`",
        f"- Best 12m start: `{summary['best_12m_start'].get('start_date', 'n/a')}` -> `{summary['best_12m_start'].get('ret_12m_pct', np.nan):.2f}%`",
        f"- Worst 12m start: `{summary['worst_12m_start'].get('start_date', 'n/a')}` -> `{summary['worst_12m_start'].get('ret_12m_pct', np.nan):.2f}%`",
        "",
        "## Annual Start Readout",
        "",
        "| Start | 1M | 3M | 6M | 12M | TotalReturn | Calmar | MaxDD | Worst3m | Worst6m | RecoveryDays | AvgTotalExp | dCalmar vs Full | dMaxDD vs Full |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in yearly_table.iterrows():
        lines.append(
            f"| {row['start_date']} | "
            f"{'' if pd.isna(row['ret_1m_pct']) else f'{row['ret_1m_pct']:.2f}%'} | "
            f"{'' if pd.isna(row['ret_3m_pct']) else f'{row['ret_3m_pct']:.2f}%'} | "
            f"{'' if pd.isna(row['ret_6m_pct']) else f'{row['ret_6m_pct']:.2f}%'} | "
            f"{'' if pd.isna(row['ret_12m_pct']) else f'{row['ret_12m_pct']:.2f}%'} | "
            f"{row['total_return_pct']:.2f}% | {row['calmar']:.3f} | {row['maxdd_pct']:.2f}% | "
            f"{row['worst_3m_cluster_pct']:.2f}% | {row['worst_6m_cluster_pct']:.2f}% | {row['recovery_days_from_maxdd'] if not pd.isna(row['recovery_days_from_maxdd']) else ''} | "
            f"{row['avg_total_exposure_pct']:.2f}% | {row['d_calmar_vs_full']:+.3f} | {row['d_maxdd_vs_full_pp']:+.2f}pp |"
        )
        chart_path = next((item["path"] for item in chart_paths if item["start_date"] == row["start_date"]), None)
        if chart_path:
            lines.append(f"  Chart: [{row['start_date']}](/Users/zhao/Desktop/LG/trading%20and%20programming/02_%E4%BA%A4%E6%98%93%E7%B3%BB%E7%BB%9F_crpyto/trend_system_v1.0/{chart_path})")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"report": REPORT_MD.name, "table": TABLE_CSV.name, "summary": SUMMARY_JSON.name, "chart_dir": str(CHART_DIR)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
