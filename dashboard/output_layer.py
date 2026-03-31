#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Output/render layer for the dashboard package."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Dict

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig_dashboard")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parent
OUTDIR = ROOT / "output"
LATEST_PNG_PATH = OUTDIR / "current_signal_latest.png"
JSON_PATH = OUTDIR / "current_signal.json"
MD_PATH = OUTDIR / "current_signal.md"


def _fmt(x: float) -> str:
    return f"{x:.2f}"


def render_markdown(snapshot: Dict, decision: Dict) -> str:
    t = decision["targets"]
    fr = snapshot["data_freshness"]
    lines = [
        "# Current Signal",
        "",
        f"- Time: `{snapshot['timestamp']}`",
        f"- State: `{snapshot['state']}`",
        f"- Portfolio state: `{snapshot['portfolio_state']}`",
        f"- Core Risk-Off state: `{snapshot['core_riskoff_state']}`",
        "",
        "## Exposure",
        "",
        f"- Core = `{snapshot['core_exposure']:.2f}`",
        f"- Sleeve1 = `{snapshot['sleeve1_exposure']:.2f}`",
        f"- Sleeve2 = `{snapshot['sleeve2_exposure']:.2f}`",
        f"- Total = `{snapshot['total_exposure']:.2f}`",
        f"- Cap headroom = `{snapshot['cap_headroom']:.2f}x`",
        "",
        "## Notional",
        "",
        f"- Account equity = `{decision['account_equity_usdt']:.2f} USDT`",
        f"- Current notional = `{decision['current_notional_usdt']:.2f} USDT`",
        f"- Target total notional = `{t['total_target_notional']:.2f} USDT`",
        f"- Delta = `{decision['delta_usdt']:+.2f} USDT`",
        f"- Action = `{decision['action']}`",
        f"- Order = `{decision['order_text']}`",
        "",
        "## Memo",
        "",
        f"- Suggestion = `{decision['suggestion']}`",
        f"- Governance alert = `{snapshot['governance_alert_level']}`",
        f"- Preferred onboarding = `{snapshot['preferred_onboarding']}`",
        "",
        "## Data Freshness",
        "",
        f"- Generated at = `{fr['generated_at_utc']}`",
        f"- Last 5m bar = `{fr['last_5m_bar_utc']}`",
        f"- Last 4h bar = `{fr['last_4h_bar_utc']}`",
        f"- Last 1h bar = `{fr.get('last_1h_bar_utc', 'n/a')}`",
        f"- Last 1d bar = `{fr.get('last_1d_bar_utc', 'n/a')}`",
        f"- 5m lag = `{fr['lag_5m_minutes']:.1f} min`",
        f"- 4h lag = `{fr['lag_4h_minutes']:.1f} min`",
        f"- Missing 5m gaps = `{fr['missing_5m_bar_gaps']}`",
        f"- Missing 4h gaps = `{fr['missing_4h_bar_gaps']}`",
        f"- Is stale = `{fr['is_stale']}`",
    ]
    return "\n".join(lines)


def render_png(snapshot: Dict, decision: Dict) -> Path:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    ts_label = (
        str(snapshot["timestamp"])
        .replace("-", "")
        .replace(":", "")
        .replace(" ", "_")
        .replace("+00:00", "UTC")
    )
    png_path = OUTDIR / f"current_signal_{ts_label}.png"
    recent_equity = snapshot["recent_equity"].astype(float)
    recent_exposure = snapshot["recent_total_exposure"].astype(float)
    equity_rebased = 100.0 * recent_equity / float(recent_equity.iloc[0])
    recent_ohlc = snapshot["recent_ohlc"].copy()
    exposure_df = pd.DataFrame(
        {
            "Layer": ["Core", "Sleeve1", "Sleeve2", "Total"],
            "Exposure": [
                snapshot["core_exposure"],
                snapshot["sleeve1_exposure"],
                snapshot["sleeve2_exposure"],
                snapshot["total_exposure"],
            ],
        }
    )

    fig = plt.figure(figsize=(16, 13), constrained_layout=True)
    gs = fig.add_gridspec(4, 2, height_ratios=[0.8, 1.6, 0.9, 0.9])

    ax_title = fig.add_subplot(gs[0, :])
    ax_price = fig.add_subplot(gs[1, :])
    ax_eq = fig.add_subplot(gs[2, 0])
    ax_exp = fig.add_subplot(gs[2, 1])
    ax_text = fig.add_subplot(gs[3, :])

    ax_title.axis("off")
    ax_title.text(0.01, 0.90, "Adopted BTC Mainline Current Signal", fontsize=20, fontweight="bold", ha="left", va="top")
    ax_title.text(0.01, 0.65, f"Time: {snapshot['timestamp']}", fontsize=11, ha="left")
    ax_title.text(
        0.01,
        0.42,
        (
            f"State: {snapshot['state']} | Portfolio: {snapshot['portfolio_state']} | "
            f"Risk-Off: {snapshot['core_riskoff_state']} | Alert: {snapshot['governance_alert_level']}"
        ),
        fontsize=11,
        ha="left",
    )
    ax_title.text(
        0.01,
        0.18,
        (
            f"Action: {decision['action']} | Order: {decision['order_text']} | "
            f"Suggestion: {decision['suggestion']}"
        ),
        fontsize=13,
        fontweight="bold",
        ha="left",
        color="#0f172a",
    )
    ax_title.text(
        0.99,
        0.90,
        (
            f"5m lag {snapshot['data_freshness']['lag_5m_minutes']:.1f}m | "
            f"4h lag {snapshot['data_freshness']['lag_4h_minutes']:.1f}m | "
            f"stale={snapshot['data_freshness']['is_stale']}"
        ),
        fontsize=10,
        ha="right",
        va="top",
        color="#475569",
    )

    ax_price.set_title("Recent 4H Candles / EMA250 / Core Flat / Sleeve Events")
    o = recent_ohlc["open"].astype(float)
    h = recent_ohlc["high"].astype(float)
    l = recent_ohlc["low"].astype(float)
    c = recent_ohlc["close"].astype(float)
    ema = recent_ohlc["ema250"].astype(float)
    x = mdates.date2num(recent_ohlc.index.to_pydatetime())
    candle_width = 0.10

    for start, end in snapshot["core_flat_spans"]:
        ax_price.axvspan(mdates.date2num(start.to_pydatetime()), mdates.date2num(end.to_pydatetime()), color="#e5e7eb", alpha=0.35)

    for xi, oi, hi, li, ci in zip(x, o, h, l, c):
        color = "#16a34a" if ci >= oi else "#dc2626"
        ax_price.vlines(xi, li, hi, color=color, linewidth=0.8, alpha=0.9)
        body_low = min(oi, ci)
        body_h = max(abs(ci - oi), 1e-6)
        ax_price.add_patch(Rectangle((xi - candle_width / 2, body_low), candle_width, body_h, facecolor=color, edgecolor=color, linewidth=0.8))

    ax_price.plot(recent_ohlc.index, ema.values, color="#2563eb", linewidth=1.8, label="EMA250")

    def mark_events(df: pd.DataFrame, color: str, marker_entry: str, marker_exit: str, label_entry: str, label_exit: str, ymode: str) -> None:
        if df is None or df.empty:
            return
        entries = df[df["event"] == "entry"]
        exits = df[df["event"] == "exit"]
        if not entries.empty:
            y = recent_ohlc.loc[entries["timestamp"], "low"].astype(float).values * (0.995 if ymode == "low" else 1.005)
            ax_price.scatter(entries["timestamp"], y, s=38, marker=marker_entry, color=color, label=label_entry, zorder=5)
        if not exits.empty:
            y = recent_ohlc.loc[exits["timestamp"], "high"].astype(float).values * (1.005 if ymode == "low" else 0.995)
            ax_price.scatter(exits["timestamp"], y, s=38, marker=marker_exit, color=color, label=label_exit, zorder=5)

    mark_events(snapshot["core_events"], "#0f172a", "^", "x", "Core/Re-entry In", "Core Flat", "low")
    mark_events(snapshot["s1_events"], "#059669", "o", "o", "S1 Entry", "S1 Exit", "low")
    mark_events(snapshot["s2_events"], "#d97706", "s", "s", "S2 Entry", "S2 Exit", "low")

    ax_price.grid(alpha=0.2)
    ax_price.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax_price.legend(loc="upper left", ncol=4, fontsize=9)

    ax_eq.plot(equity_rebased.index, equity_rebased.values, color="#0f172a", linewidth=2.0)
    ax_eq.set_title("Recent Equity (Rebased)")
    ax_eq.set_ylabel("Index = 100")
    ax_eq.grid(alpha=0.25)

    colors = ["#1d4ed8", "#059669", "#d97706", "#111827"]
    ax_exp.barh(exposure_df["Layer"], exposure_df["Exposure"], color=colors)
    ax_exp.axvline(snapshot["hard_cap"], color="#dc2626", linestyle="--", linewidth=1.5, label="Hard Cap 3.0x")
    ax_exp.set_xlim(0, max(snapshot["hard_cap"] + 0.2, exposure_df["Exposure"].max() + 0.2))
    ax_exp.set_title("Target Exposure")
    ax_exp.grid(axis="x", alpha=0.25)
    ax_exp.legend(loc="lower right")

    ax_text.axis("off")
    t = decision["targets"]
    body = "\n".join(
        [
            f"Account equity: {_fmt(decision['account_equity_usdt'])} USDT",
            f"Current actual notional: {_fmt(decision['current_notional_usdt'])} USDT",
            f"Core target notional: {_fmt(t['core_target_notional'])} USDT",
            f"Sleeve1 target notional: {_fmt(t['sleeve1_target_notional'])} USDT",
            f"Sleeve2 target notional: {_fmt(t['sleeve2_target_notional'])} USDT",
            f"Total target notional: {_fmt(t['total_target_notional'])} USDT",
            f"Delta: {decision['delta_usdt']:+.2f} USDT",
            f"Cap headroom: {_fmt(snapshot['cap_headroom'])}x",
            f"Drawdown: {_fmt(snapshot['current_drawdown_pct'])}% | Days since high: {_fmt(snapshot['days_since_equity_high'])}",
            f"3m cluster: {_fmt(snapshot['trailing_3m_cluster_loss_pct'])}% | 6m cluster: {_fmt(snapshot['trailing_6m_cluster_loss_pct'])}%",
            f"Preferred onboarding: {snapshot['preferred_onboarding']}",
            f"Last 5m bar: {snapshot['data_freshness']['last_5m_bar_utc']}",
            f"Last 4h bar: {snapshot['data_freshness']['last_4h_bar_utc']}",
            f"Last 1h bar: {snapshot['data_freshness'].get('last_1h_bar_utc', 'n/a')}",
            f"Last 1d bar: {snapshot['data_freshness'].get('last_1d_bar_utc', 'n/a')}",
            f"Missing gaps: 5m={snapshot['data_freshness']['missing_5m_bar_gaps']} | 4h={snapshot['data_freshness']['missing_4h_bar_gaps']}",
            "Price panel legend: grey zone = core flat period, black ^ = core/re-entry in, black x = flat, green o = Sleeve1, orange square = Sleeve2",
        ]
    )
    ax_text.text(0.01, 0.98, body, fontsize=12, ha="left", va="top", family="monospace")

    fig.savefig(png_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    shutil.copy2(png_path, LATEST_PNG_PATH)
    return png_path


def write_all(snapshot: Dict, decision: Dict) -> Dict[str, Path]:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    payload = {"snapshot": snapshot, "decision": decision}
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    MD_PATH.write_text(render_markdown(snapshot, decision), encoding="utf-8")
    png = render_png(snapshot, decision)
    return {"png": png, "png_latest": LATEST_PNG_PATH, "json": JSON_PATH, "md": MD_PATH}
