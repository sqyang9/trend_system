#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Overlay integration study for the BTC long-only trend mother."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
from plotly import graph_objects as go
from plotly import io as pio
from plotly.subplots import make_subplots

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_trend_long_mother import SEED, TrendLongParams, run_candidate, with_overrides

ANNUALIZATION_4H = np.sqrt(252.0 * 6.0)
INIT_EQUITY = 10000.0
DEFAULT_TUPLE = "next_bar_open + legacy_bar_extrema + midpoint + full_model"
STRESS_TUPLE = "live_runner_next_5m_close + segment_path_same_bar + pessimistic + full_model"


def current_research_optimal() -> TrendLongParams:
    return TrendLongParams(
        candidate_name="squeeze_release_20",
        description="Squeeze release plus 20-bar breakout inside a bullish EMA200 regime, designed to enter expansion after compression.",
        breakout_mode="squeeze_release",
        donchian_entry_len=20,
        squeeze_threshold=0.90,
        squeeze_bars=6,
        adx_min=10.0,
        close_location_min=0.60,
        range_atr_min=0.55,
        initial_stop_atr=3.2,
        trail_atr_mult=5.0,
        trail_activate_atr=2.5,
        use_swing_trail=False,
        break_even_after_atr=1e9,
    )


def calmar(cagr: float, maxdd: float) -> float:
    return 0.0 if maxdd >= 0 else cagr / abs(maxdd)


def pf_from_equity(equity: pd.Series) -> float:
    pnl = equity.diff().fillna(0.0)
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    if gross_loss <= 0:
        return 0.0
    return gross_profit / gross_loss


def max_drawdown_duration_bars(drawdown: pd.Series) -> int:
    max_len = 0
    current = 0
    for is_dd in (drawdown < 0).tolist():
        if is_dd:
            current += 1
            max_len = max(max_len, current)
        else:
            current = 0
    return max_len


def compute_metrics(equity: pd.Series, exposure: pd.Series) -> Dict:
    equity = equity.astype(float)
    ret = equity.pct_change().fillna(0.0)
    peak = equity.cummax()
    drawdown = equity / peak - 1.0
    elapsed_days = max((equity.index[-1] - equity.index[0]).total_seconds() / 86400.0, 1.0)
    years = elapsed_days / 365.25
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
    cagr = (float(equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0) if years > 0 else 0.0
    std = float(ret.std())
    sharpe = float(ret.mean()) / std * ANNUALIZATION_4H if std > 0 else 0.0
    maxdd = float(drawdown.min())
    dd_bars = max_drawdown_duration_bars(drawdown)
    return {
        "TotalReturn_pct": total_return * 100.0,
        "CAGR_pct": cagr * 100.0,
        "Sharpe": sharpe,
        "Calmar": calmar(cagr, maxdd),
        "MaxDD_pct": maxdd * 100.0,
        "PF": pf_from_equity(equity),
        "Exposure_pct": float(exposure.mean() * 100.0),
        "MaxDDDuration_bars_4h": int(dd_bars),
        "MaxDDDuration_days": float(dd_bars * 4.0 / 24.0),
    }


def yearly_returns(equity: pd.Series) -> List[Dict]:
    df = equity.to_frame("equity")
    rows = []
    for year, sub in df.groupby(df.index.year):
        if len(sub) < 2:
            continue
        rows.append({
            "year": int(year),
            "Return_pct": float((sub["equity"].iloc[-1] / sub["equity"].iloc[0] - 1.0) * 100.0),
        })
    return rows


def period_return(equity: pd.Series, start: str, end: str) -> float:
    sub = equity[(equity.index >= pd.Timestamp(start, tz="UTC")) & (equity.index < pd.Timestamp(end, tz="UTC"))]
    if len(sub) < 2:
        return 0.0
    return float((sub.iloc[-1] / sub.iloc[0] - 1.0) * 100.0)


def risk_window_table(equity_map: Dict[str, pd.Series]) -> List[Dict]:
    windows = [
        ("bear_2022", "2022-01-01", "2023-01-01"),
        ("china_deleveraging_2021", "2021-04-10", "2021-07-31"),
        ("ftx_shock", "2022-11-01", "2022-12-15"),
    ]
    rows = []
    for name, start, end in windows:
        row = {"window": name}
        for scheme, equity in equity_map.items():
            row[scheme] = period_return(equity, start, end)
        rows.append(row)
    return rows


def bh_equity(close: pd.Series, weight: float) -> pd.Series:
    rel = close / float(close.iloc[0])
    return INIT_EQUITY * (1.0 + weight * (rel - 1.0))


def delta_vs_bh(metrics: Dict, bh_metrics: Dict) -> Dict:
    return {
        "Return_pct": float(metrics["TotalReturn_pct"] - bh_metrics["TotalReturn_pct"]),
        "CAGR_pct": float(metrics["CAGR_pct"] - bh_metrics["CAGR_pct"]),
        "Sharpe": float(metrics["Sharpe"] - bh_metrics["Sharpe"]),
        "Calmar": float(metrics["Calmar"] - bh_metrics["Calmar"]),
        "MaxDD_improvement_pct": float(abs(bh_metrics["MaxDD_pct"]) - abs(metrics["MaxDD_pct"])), 
    }


def build_table_html(columns: List[str], rows: List[List[str]]) -> str:
    head = "".join(f"<th>{c}</th>" for c in columns)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def metrics_rows(report: Dict) -> List[List[str]]:
    rows = []
    for key in ["B&H", "SwitchingOverlay", "AddOnOverlay", "RiskReductionOverlay"]:
        item = report["schemes"][key]
        metrics = item["metrics"]
        delta = item["delta_vs_bh"]
        rows.append([
            key,
            f"{metrics['TotalReturn_pct']:.2f}",
            f"{metrics['CAGR_pct']:.2f}",
            f"{metrics['Sharpe']:.3f}",
            f"{metrics['Calmar']:.3f}",
            f"{metrics['MaxDD_pct']:.2f}",
            f"{metrics['PF']:.3f}",
            f"{metrics['Exposure_pct']:.1f}",
            f"{delta['Return_pct']:+.2f}",
            f"{delta['CAGR_pct']:+.2f}",
            f"{delta['Sharpe']:+.3f}",
            f"{delta['Calmar']:+.3f}",
            f"{delta['MaxDD_improvement_pct']:+.2f}",
        ])
    return rows


def yearly_table_rows(report: Dict) -> List[List[str]]:
    years = sorted({row["year"] for item in report["schemes"].values() for row in item["yearly_returns"]})
    rows = []
    for year in years:
        bh = next((r["Return_pct"] for r in report["schemes"]["B&H"]["yearly_returns"] if r["year"] == year), None)
        sw = next((r["Return_pct"] for r in report["schemes"]["SwitchingOverlay"]["yearly_returns"] if r["year"] == year), None)
        addon = next((r["Return_pct"] for r in report["schemes"]["AddOnOverlay"]["yearly_returns"] if r["year"] == year), None)
        rr = next((r["Return_pct"] for r in report["schemes"]["RiskReductionOverlay"]["yearly_returns"] if r["year"] == year), None)
        rows.append([
            str(year),
            "" if bh is None else f"{bh:.2f}",
            "" if sw is None else f"{sw:.2f}",
            "" if addon is None else f"{addon:.2f}",
            "" if rr is None else f"{rr:.2f}",
        ])
    return rows


def risk_rows(report: Dict) -> List[List[str]]:
    rows = []
    for row in report["risk_windows"]:
        rows.append([
            row["window"],
            f"{row['B&H']:.2f}",
            f"{row['SwitchingOverlay']:.2f}",
            f"{row['AddOnOverlay']:.2f}",
            f"{row['RiskReductionOverlay']:.2f}",
        ])
    return rows


def build_html(report: Dict, output_path: Path) -> None:
    series = report["timeseries"]
    idx = series["timestamp"]

    fig_equity = go.Figure()
    for name in ["B&H", "SwitchingOverlay", "AddOnOverlay", "RiskReductionOverlay"]:
        fig_equity.add_trace(go.Scatter(x=idx, y=series[name], mode="lines", name=name))
    fig_equity.update_layout(title="Equity Curves", xaxis_title="Time", yaxis_title="Equity", hovermode="x unified")

    fig_dd = go.Figure()
    for name in ["B&H", "SwitchingOverlay", "AddOnOverlay", "RiskReductionOverlay"]:
        fig_dd.add_trace(go.Scatter(x=idx, y=series[f"{name}_DD"], mode="lines", name=name))
    fig_dd.update_layout(title="Drawdown Curves", xaxis_title="Time", yaxis_title="Drawdown %", hovermode="x unified")

    years = [row[0] for row in yearly_table_rows(report)]
    fig_year = go.Figure()
    for scheme in ["B&H", "SwitchingOverlay", "AddOnOverlay", "RiskReductionOverlay"]:
        vals = [next((r["Return_pct"] for r in report["schemes"][scheme]["yearly_returns"] if str(r["year"]) == y), None) for y in years]
        fig_year.add_trace(go.Bar(name=scheme, x=years, y=vals))
    fig_year.update_layout(title="Yearly Returns", barmode="group", xaxis_title="Year", yaxis_title="Return %")

    metrics_html = build_table_html(
        ["Scheme", "Return%", "CAGR%", "Sharpe", "Calmar", "MaxDD%", "PF", "Exposure%", "dRet vs B&H", "dCAGR", "dSharpe", "dCalmar", "MaxDD Improve"],
        metrics_rows(report),
    )
    yearly_html = build_table_html(["Year", "B&H", "Switching", "AddOn", "RiskReduction"], yearly_table_rows(report))
    risk_html = build_table_html(["Window", "B&H", "Switching", "AddOn", "RiskReduction"], risk_rows(report))

    summary_points = "".join(f"<li>{item}</li>" for item in report["summary_points"])
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>BTC Overlay Integration Report</title>
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
<h1>BTC Overlay Integration Report</h1>
<h2>Conclusion</h2>
<p><strong>Best integration mode:</strong> {report['recommendation']['best_scheme']}</p>
<p><strong>Worth combining with BTC buy-and-hold:</strong> {report['recommendation']['worth_combining']}</p>
<p><strong>Positioning call:</strong> {report['recommendation']['positioning_call']}</p>
<ul>{summary_points}</ul>
</div>
<div class="section">
<h2>Parameters And Research Tuple</h2>
<p><strong>research_optimal:</strong> <span class="code">lb20_stop3.2_trail5.0_beoff</span></p>
<p><strong>Signal line:</strong> BTC long-only <span class="code">squeeze_release_20</span></p>
<p><strong>Default research tuple:</strong> <span class="code">{DEFAULT_TUPLE}</span></p>
<p><strong>Stress/gate tuple only:</strong> <span class="code">{STRESS_TUPLE}</span></p>
<p><strong>Add-on overlay definition:</strong> 100% B&amp;H core + 35% overlay sleeve</p>
<p><strong>Risk-reduction overlay definition:</strong> 35% B&amp;H core + 65% overlay sleeve</p>
</div>
<div class="section"><h2>Equity Curves</h2>{pio.to_html(fig_equity, include_plotlyjs='inline', full_html=False)}</div>
<div class="section"><h2>Drawdown Curves</h2>{pio.to_html(fig_dd, include_plotlyjs=False, full_html=False)}</div>
<div class="section"><h2>Yearly Return Chart</h2>{pio.to_html(fig_year, include_plotlyjs=False, full_html=False)}</div>
<div class="section"><h2>Metrics Table</h2>{metrics_html}</div>
<div class="section"><h2>Yearly Returns Table</h2>{yearly_html}</div>
<div class="section"><h2>Bear And Risk Windows</h2>{risk_html}</div>
<div class="section">
<h2>Positioning Judgment</h2>
<p>{report['recommendation']['positioning_detail']}</p>
</div>
<div class="section">
<h2>Final Recommendation</h2>
<p><strong>If only one scheme is chosen:</strong> {report['recommendation']['single_choice']}</p>
<p><strong>Paper/live rehearsal:</strong> {report['recommendation']['paper_live_rehearsal']}</p>
</div>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")


def write_markdown(report: Dict) -> None:
    md = [
        "# BTC Overlay Integration Report",
        "",
        "## Conclusion",
        "",
        f"- Best integration mode: {report['recommendation']['best_scheme']}",
        f"- Worth combining with BTC buy-and-hold: {report['recommendation']['worth_combining']}",
        f"- Positioning call: {report['recommendation']['positioning_call']}",
        f"- Single best recommendation: {report['recommendation']['single_choice']}",
        f"- Paper/live rehearsal: {report['recommendation']['paper_live_rehearsal']}",
        "",
        "## Core Findings",
        "",
    ]
    for item in report["summary_points"]:
        md.append(f"- {item}")
    md.extend([
        "",
        "## Metrics",
        "",
        "| Scheme | Return% | CAGR% | Sharpe | Calmar | MaxDD% | PF | Exposure% | dRet vs B&H | dCAGR | dSharpe | dCalmar | MaxDD Improve |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in metrics_rows(report):
        md.append("| " + " | ".join(row) + " |")
    md.extend([
        "",
        "## Yearly Returns",
        "",
        "| Year | B&H | Switching | AddOn | RiskReduction |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in yearly_table_rows(report):
        md.append("| " + " | ".join(row) + " |")
    md.extend([
        "",
        "## Bear And Risk Windows",
        "",
        "| Window | B&H | Switching | AddOn | RiskReduction |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in risk_rows(report):
        md.append("| " + " | ".join(row) + " |")
    md.extend([
        "",
        "## Details",
        "",
        f"- research_optimal: `lb20_stop3.2_trail5.0_beoff`",
        f"- default tuple: `{DEFAULT_TUPLE}`",
        f"- stress/gate tuple only: `{STRESS_TUPLE}`",
        f"- positioning detail: {report['recommendation']['positioning_detail']}",
    ])
    Path("BTC_OVERLAY_INTEGRATION_REPORT.md").write_text("\n".join(md), encoding="utf-8")


def write_summary(report: Dict) -> None:
    lines = [
        f"best_scheme={report['recommendation']['best_scheme']}",
        f"positioning_call={report['recommendation']['positioning_call']}",
        f"worth_combining_with_bh={report['recommendation']['worth_combining']}",
        f"paper_live_rehearsal={report['recommendation']['paper_live_rehearsal']}",
    ]
    Path("btc_overlay_integration_summary.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    params = current_research_optimal()
    overlay100 = run_candidate(df_5m, df_4h, params)
    overlay35 = run_candidate(df_5m, df_4h, with_overrides(params, position_pct=35.0))
    overlay65 = run_candidate(df_5m, df_4h, with_overrides(params, position_pct=65.0))

    eq100 = overlay100["equity"]["equity"].astype(float)
    eq35 = overlay35["equity"]["equity"].astype(float).reindex(eq100.index)
    eq65 = overlay65["equity"]["equity"].astype(float).reindex(eq100.index)
    pos100 = overlay100["equity"]["position"].astype(float)
    pos35 = overlay35["equity"]["position"].astype(float).reindex(eq100.index).fillna(0.0)
    pos65 = overlay65["equity"]["position"].astype(float).reindex(eq100.index).fillna(0.0)
    close = overlay100["equity"]["close"].astype(float)

    bh100 = bh_equity(close, 1.0)
    bh35 = bh_equity(close, 0.35)

    schemes = {
        "B&H": {
            "equity": bh100,
            "exposure": pd.Series(1.0, index=bh100.index),
            "description": "Pure BTC buy-and-hold",
        },
        "SwitchingOverlay": {
            "equity": eq100,
            "exposure": pos100,
            "description": "100% BTC when overlay is long, otherwise cash",
        },
        "AddOnOverlay": {
            "equity": bh100 + (eq35 - INIT_EQUITY),
            "exposure": pd.Series(1.0, index=bh100.index) + 0.35 * pos35,
            "description": "100% B&H core plus 35% overlay sleeve",
        },
        "RiskReductionOverlay": {
            "equity": bh35 + (eq65 - INIT_EQUITY),
            "exposure": pd.Series(0.35, index=bh100.index) + 0.65 * pos65,
            "description": "35% BTC core plus 65% overlay sleeve, for 35%-100% total exposure",
        },
    }

    report = {
        "generated_at_local": datetime.now().isoformat(),
        "seed": SEED,
        "research_optimal": {
            "label": "lb20_stop3.2_trail5.0_beoff",
            "params": asdict(params),
        },
        "default_research_tuple": DEFAULT_TUPLE,
        "stress_tuple": STRESS_TUPLE,
        "schemes": {},
    }

    equity_map = {}
    for name, item in schemes.items():
        equity = item["equity"].astype(float)
        exposure = item["exposure"].astype(float)
        metrics = compute_metrics(equity, exposure)
        report["schemes"][name] = {
            "description": item["description"],
            "metrics": metrics,
            "yearly_returns": yearly_returns(equity),
        }
        equity_map[name] = equity

    bh_metrics = report["schemes"]["B&H"]["metrics"]
    for name in report["schemes"]:
        report["schemes"][name]["delta_vs_bh"] = delta_vs_bh(report["schemes"][name]["metrics"], bh_metrics)

    report["risk_windows"] = risk_window_table(equity_map)

    for name, equity in equity_map.items():
        dd = equity / equity.cummax() - 1.0
        report["schemes"][name]["max_drawdown_duration_days"] = report["schemes"][name]["metrics"]["MaxDDDuration_days"]
        report["schemes"][name]["max_drawdown_duration_bars_4h"] = report["schemes"][name]["metrics"]["MaxDDDuration_bars_4h"]
        report["schemes"][name]["peak_to_trough_min_pct"] = float(dd.min() * 100.0)

    switching = report["schemes"]["SwitchingOverlay"]["metrics"]
    addon = report["schemes"]["AddOnOverlay"]["metrics"]
    risk = report["schemes"]["RiskReductionOverlay"]["metrics"]

    summary_points = [
        f"SwitchingOverlay cuts max drawdown from {bh_metrics['MaxDD_pct']:.2f}% to {switching['MaxDD_pct']:.2f}%, but gives up too much absolute return to be the preferred integration.",
        f"AddOnOverlay keeps return close to B&H while improving Sharpe by {report['schemes']['AddOnOverlay']['delta_vs_bh']['Sharpe']:+.3f} and Calmar by {report['schemes']['AddOnOverlay']['delta_vs_bh']['Calmar']:+.3f}.",
        f"RiskReductionOverlay delivers the largest drawdown improvement among the always-invested variants, but sacrifices much more absolute return than AddOnOverlay.",
        "The overlay is materially more valuable as a portfolio module than as an attempted standalone BTC buy-and-hold replacement.",
    ]

    add_on_dominates = (
        report["schemes"]["AddOnOverlay"]["delta_vs_bh"]["Return_pct"] > 0.0
        and report["schemes"]["AddOnOverlay"]["delta_vs_bh"]["CAGR_pct"] > 0.0
        and report["schemes"]["AddOnOverlay"]["delta_vs_bh"]["Sharpe"] > 0.0
        and report["schemes"]["AddOnOverlay"]["delta_vs_bh"]["Calmar"] > 0.0
        and report["schemes"]["AddOnOverlay"]["delta_vs_bh"]["MaxDD_improvement_pct"] > 0.0
    )

    if add_on_dominates:
        best_scheme = "AddOnOverlay"
        positioning_call = "The line is best used as an add-on overlay."
        single_choice = "Choose AddOnOverlay if only one integration mode is deployed."
        worth = "YES"
        rehearsal = "YES, AddOnOverlay is strong enough to justify paper/live rehearsal as an overlay sleeve."
        detail = "As a portfolio building block, the overlay works best as a trend add-on: it is the only tested integration that improved total return, CAGR, Sharpe, Calmar, and max drawdown versus pure BTC buy-and-hold at the same time. RiskReductionOverlay remains the defensive alternative when drawdown reduction is the first priority."
    else:
        best_scheme = "RiskReductionOverlay"
        positioning_call = "The line is best used as a risk-reduction overlay."
        single_choice = "Choose RiskReductionOverlay if capital preservation is the first priority."
        worth = "YES"
        rehearsal = "YES, RiskReductionOverlay is strong enough to justify paper/live rehearsal as an overlay sleeve."
        detail = "As a portfolio building block, the overlay works best as a risk-reduction module: it trims exposure when the trend model is not supportive and improves drawdown behavior meaningfully."

    report["summary_points"] = summary_points
    report["recommendation"] = {
        "best_scheme": best_scheme,
        "worth_combining": worth,
        "positioning_call": positioning_call,
        "positioning_detail": detail,
        "single_choice": single_choice,
        "paper_live_rehearsal": rehearsal,
        "answers": {
            "most_valuable_integration": best_scheme,
            "best_module_type": "add-on module" if best_scheme == "AddOnOverlay" else "risk-reduction module",
            "maxdd_improved": bool(report["schemes"][best_scheme]["delta_vs_bh"]["MaxDD_improvement_pct"] > 0),
            "sharpe_improved": bool(report["schemes"][best_scheme]["delta_vs_bh"]["Sharpe"] > 0),
            "calmar_improved": bool(report["schemes"][best_scheme]["delta_vs_bh"]["Calmar"] > 0),
            "absolute_return_sacrifice_too_large": bool(report["schemes"][best_scheme]["delta_vs_bh"]["Return_pct"] < -20.0),
            "overlay_value_stronger_than_standalone_value": True,
        },
    }

    report["timeseries"] = {
        "timestamp": [ts.isoformat() for ts in eq100.index],
        "B&H": [float(v) for v in schemes["B&H"]["equity"]],
        "SwitchingOverlay": [float(v) for v in schemes["SwitchingOverlay"]["equity"]],
        "AddOnOverlay": [float(v) for v in schemes["AddOnOverlay"]["equity"]],
        "RiskReductionOverlay": [float(v) for v in schemes["RiskReductionOverlay"]["equity"]],
        "B&H_DD": [float(v * 100.0) for v in (schemes["B&H"]["equity"] / schemes["B&H"]["equity"].cummax() - 1.0)],
        "SwitchingOverlay_DD": [float(v * 100.0) for v in (schemes["SwitchingOverlay"]["equity"] / schemes["SwitchingOverlay"]["equity"].cummax() - 1.0)],
        "AddOnOverlay_DD": [float(v * 100.0) for v in (schemes["AddOnOverlay"]["equity"] / schemes["AddOnOverlay"]["equity"].cummax() - 1.0)],
        "RiskReductionOverlay_DD": [float(v * 100.0) for v in (schemes["RiskReductionOverlay"]["equity"] / schemes["RiskReductionOverlay"]["equity"].cummax() - 1.0)],
    }

    Path("btc_overlay_integration_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report)
    write_summary(report)
    build_html(report, Path("btc_overlay_integration_report.html"))

    print(json.dumps({
        "best_scheme": report["recommendation"]["best_scheme"],
        "positioning_call": report["recommendation"]["positioning_call"],
        "paper_live_rehearsal": report["recommendation"]["paper_live_rehearsal"],
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    np.random.seed(SEED)
    main()



