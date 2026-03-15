#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build an interactive HTML report for the current aligned core Risk-Off level study."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from plotly import graph_objects as go
from plotly import io as pio

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_core_riskoff_level_study import (
    build_targets,
    combine_core_and_overlay,
    current_research_optimal,
    load_overlay_artifact,
    simulate_core,
)

REPORT_JSON = Path("btc_core_riskoff_level_report.json")
OUTPUT_HTML = Path("btc_core_riskoff_level_report.html")


def drawdown_pct(equity: pd.Series) -> pd.Series:
    return (equity / equity.cummax() - 1.0) * 100.0


def parse_structure_label(label: str) -> Tuple[int, float]:
    tail = label.replace("Core+AddOnOverlay+", "")
    ema_part, off_part = tail.split("_OFF_")
    return int(ema_part.replace("EMA", "")), float(off_part)


def best_partial_key(report: Dict) -> str:
    keys = [
        key for key in report["grid_order"]
        if not key.endswith("_0.00")
    ]
    return max(
        keys,
        key=lambda k: (
            report["default_bundle"]["schemes"][k]["metrics"]["Calmar"],
            report["default_bundle"]["schemes"][k]["metrics"]["Sharpe"],
        ),
    )


def build_selected_timeseries(report: Dict) -> Dict[str, pd.Series]:
    overlay = load_overlay_artifact()
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    params = current_research_optimal(
        entry_execution_mode="next_bar_open",
        intrabar_execution_model="legacy_bar_extrema",
        intrabar_path_mode="midpoint",
    )

    preferred_key = report["judgment"]["preferred_structure"]
    partial_key = best_partial_key(report)
    needed = {
        "B&H": overlay["bh_equity"],
        "Core+AddOnOverlay": overlay["addon_equity"],
        "NoCore_SwitchingOverlay": overlay["switching_equity"],
    }

    targets = build_targets(df_4h, overlay["index"], params)
    for key in [preferred_key, partial_key]:
        ema_len, off_weight = parse_structure_label(key)
        target = targets[f"EMA{ema_len}_OFF_{off_weight:.2f}"]
        core = simulate_core(df_5m, df_4h, target, params, "next_bar_open")
        combo = combine_core_and_overlay(
            core["equity"]["equity"],
            core["equity"]["exposure"],
            overlay["overlay_delta"],
            overlay["overlay_avg_exposure"],
        )
        needed[key] = combo["equity"]
    return needed


def build_table_html(columns: List[str], rows: List[List[str]]) -> str:
    head = "".join(f"<th>{col}</th>" for col in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def metrics_rows(report: Dict, selected_keys: List[str]) -> List[List[str]]:
    rows = []
    schemes = report["default_bundle"]["schemes"]
    for key in selected_keys:
        item = schemes[key]
        metrics = item["metrics"]
        delta_addon = item["delta_vs_addon"]
        rows.append([
            key,
            f"{metrics['TotalReturn_pct']:.2f}",
            f"{metrics['CAGR_pct']:.2f}",
            f"{metrics['Sharpe']:.3f}",
            f"{metrics['Calmar']:.3f}",
            f"{metrics['MaxDD_pct']:.2f}",
            f"{metrics['PF']:.3f}",
            f"{metrics['Exposure_pct']:.1f}",
            f"{delta_addon['Return_pct']:+.2f}",
            f"{delta_addon['Sharpe']:+.3f}",
            f"{delta_addon['Calmar']:+.3f}",
            f"{delta_addon['MaxDD_improvement_pct']:+.2f}",
        ])
    return rows


def yearly_rows(report: Dict, selected_keys: List[str]) -> List[List[str]]:
    schemes = report["default_bundle"]["schemes"]
    years = sorted({
        row["year"]
        for key in selected_keys
        for row in schemes[key]["yearly_returns"]
    })
    rows = []
    for year in years:
        row = [str(year)]
        for key in selected_keys:
            ret = next(
                (x["Return_pct"] for x in schemes[key]["yearly_returns"] if x["year"] == year),
                None,
            )
            row.append("" if ret is None else f"{ret:.2f}")
        rows.append(row)
    return rows


def risk_rows(report: Dict, preferred_key: str) -> List[List[str]]:
    rows = []
    for row in report["selected_risk_windows"]:
        rows.append([
            row["window"],
            f"{row['B&H']:.2f}",
            f"{row['Core+AddOnOverlay']:.2f}",
            f"{row['NoCore_SwitchingOverlay']:.2f}",
            f"{row[preferred_key]:.2f}",
        ])
    return rows


def grid_heatmap_figure(report: Dict) -> go.Figure:
    schemes = report["default_bundle"]["schemes"]
    x_vals = [f"{w:.2f}" for w in report["candidates"]["core_off_weights"]]
    y_vals = [str(x) for x in report["candidates"]["ema_lens"]]
    z = []
    text = []
    for ema_len in report["candidates"]["ema_lens"]:
        z_row = []
        text_row = []
        for off_weight in report["candidates"]["core_off_weights"]:
            key = f"Core+AddOnOverlay+EMA{ema_len}_OFF_{off_weight:.2f}"
            m = schemes[key]["metrics"]
            z_row.append(m["Calmar"])
            text_row.append(
                f"{key}<br>Return {m['TotalReturn_pct']:.2f}%"
                f"<br>Sharpe {m['Sharpe']:.3f}<br>MaxDD {m['MaxDD_pct']:.2f}%"
            )
        z.append(z_row)
        text.append(text_row)
    fig = go.Figure(
        data=go.Heatmap(
            x=x_vals,
            y=y_vals,
            z=z,
            text=text,
            hovertemplate="%{text}<extra></extra>",
            colorscale="Blues",
        )
    )
    fig.update_layout(
        title="Calmar Grid: EMA vs Core-Off Weight",
        xaxis_title="core_off_weight",
        yaxis_title="EMA Length",
    )
    return fig


def build_html(report: Dict, series_map: Dict[str, pd.Series], output_path: Path) -> None:
    preferred_key = report["judgment"]["preferred_structure"]
    partial_key = best_partial_key(report)
    selected_keys = ["B&H", "Core+AddOnOverlay", "NoCore_SwitchingOverlay", preferred_key, partial_key]
    idx = [ts.isoformat() for ts in next(iter(series_map.values())).index]

    fig_equity = go.Figure()
    for key in selected_keys:
        fig_equity.add_trace(go.Scatter(x=idx, y=series_map[key], mode="lines", name=key))
    fig_equity.update_layout(
        title="Equity Curves",
        xaxis_title="Time",
        yaxis_title="Equity",
        hovermode="x unified",
    )

    fig_dd = go.Figure()
    for key in selected_keys:
        fig_dd.add_trace(
            go.Scatter(
                x=idx,
                y=drawdown_pct(series_map[key]),
                mode="lines",
                name=key,
            )
        )
    fig_dd.update_layout(
        title="Drawdown Curves",
        xaxis_title="Time",
        yaxis_title="Drawdown %",
        hovermode="x unified",
    )

    years = [row[0] for row in yearly_rows(report, selected_keys)]
    fig_year = go.Figure()
    for key in selected_keys:
        vals = [
            next(
                (r["Return_pct"] for r in report["default_bundle"]["schemes"][key]["yearly_returns"] if str(r["year"]) == y),
                None,
            )
            for y in years
        ]
        fig_year.add_trace(go.Bar(name=key, x=years, y=vals))
    fig_year.update_layout(
        title="Yearly Returns",
        barmode="group",
        xaxis_title="Year",
        yaxis_title="Return %",
    )

    fig_grid = grid_heatmap_figure(report)

    metrics_html = build_table_html(
        ["Scheme", "Return%", "CAGR%", "Sharpe", "Calmar", "MaxDD%", "PF", "Exposure%", "dRet vs AddOn", "dSharpe", "dCalmar", "dMaxDD improve"],
        metrics_rows(report, selected_keys),
    )
    yearly_html = build_table_html(["Year"] + selected_keys, yearly_rows(report, selected_keys))
    risk_html = build_table_html(
        ["Window", "B&H", "AddOn-only", "No-core", "Preferred with-core"],
        risk_rows(report, preferred_key),
    )

    summary_points = [
        f"Recommended core_off_weight: {report['judgment']['recommended_core_off_weight']}",
        f"Preferred structure: {preferred_key}",
        f"With-core vs no-core: {report['judgment']['with_core_vs_no_core']}",
        f"Promotion status: {report['judgment']['promotion_status']}",
    ]
    summary_html = "".join(f"<li>{point}</li>" for point in summary_points)

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>BTC Core Risk-Off Level Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; color: #111; }}
h1, h2 {{ margin-bottom: 8px; }}
p, li {{ line-height: 1.5; }}
.section {{ margin-bottom: 28px; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 12px; }}
th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
.code {{ font-family: Consolas, monospace; background: #f3f3f3; padding: 2px 4px; }}
</style>
</head>
<body>
<div class="section">
<h1>BTC Core Risk-Off Level Report</h1>
<h2>Conclusion</h2>
<p><strong>Single question:</strong> how far the BTC core should be reduced when Risk-Off is active, and whether a with-core framework still beats a no-core framework.</p>
<p><strong>Recommended core_off_weight:</strong> {report['judgment']['recommended_core_off_weight']}</p>
<p><strong>Preferred structure:</strong> {preferred_key}</p>
<p><strong>Structural call:</strong> {report['judgment']['with_core_vs_no_core']}</p>
<ul>{summary_html}</ul>
</div>
<div class="section">
<h2>Locked Baseline</h2>
<p><strong>research_optimal:</strong> <span class="code">lb20_stop3.2_trail5.0_beoff</span></p>
<p><strong>Default tuple:</strong> <span class="code">{report['default_tuple']}</span></p>
<p><strong>Stress tuple:</strong> <span class="code">{report['stress_tuple']}</span></p>
<p><strong>Study scope:</strong> {report['study_scope']}</p>
</div>
<div class="section"><h2>Equity Curves</h2>{pio.to_html(fig_equity, full_html=False, include_plotlyjs=True)}</div>
<div class="section"><h2>Drawdown Curves</h2>{pio.to_html(fig_dd, full_html=False, include_plotlyjs=False)}</div>
<div class="section"><h2>Core-Off Grid</h2>{pio.to_html(fig_grid, full_html=False, include_plotlyjs=False)}</div>
<div class="section"><h2>Yearly Returns</h2>{pio.to_html(fig_year, full_html=False, include_plotlyjs=False)}</div>
<div class="section"><h2>Metrics Table</h2>{metrics_html}</div>
<div class="section"><h2>Yearly Table</h2>{yearly_html}</div>
<div class="section"><h2>Risk Windows</h2>{risk_html}</div>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")


def main() -> None:
    report = json.loads(REPORT_JSON.read_text(encoding="utf-8"))
    series_map = build_selected_timeseries(report)
    build_html(report, series_map, OUTPUT_HTML)
    print(json.dumps({
        "output_html": str(OUTPUT_HTML),
        "preferred_structure": report["judgment"]["preferred_structure"],
        "recommended_core_off_weight": report["judgment"]["recommended_core_off_weight"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
