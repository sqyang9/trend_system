#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate 6-month historical signal atlas charts for the adopted BTC mainline."""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig_historical_signal_atlas")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle

REPO_ROOT = Path(__file__).resolve().parents[1]
LIVE_ROOT = REPO_ROOT / "live_operating_layer"
DASHBOARD_ROOT = REPO_ROOT / "dashboard"
for p in (REPO_ROOT, LIVE_ROOT, DASHBOARD_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from v85_research_suite_v2 import ensure_datetime
from v90_asset_management_system_aligned import current_research_optimal as riskoff_current_research_optimal
from v121_coreonly_riskoff_sellside_ema_audit import build_indicators, build_target
from v123_formal_launch_and_layer2_weight_audit import SCENARIOS, base_bundle, simulate_weight_combo
from live_operating_layer.v132_live_operating_layer import ADOPTED_POSTURE


ROOT = Path(__file__).resolve().parent
OUTDIR = ROOT / "output"
INDEX_CSV = OUTDIR / "atlas_index.csv"
SUMMARY_MD = OUTDIR / "atlas_summary.md"


def transition_events(series: pd.Series, active_fn) -> pd.DataFrame:
    cur = series.astype(float)
    prev = cur.shift(1).fillna(cur.iloc[0])
    rows = []
    for ts, p, c in zip(cur.index, prev, cur):
        was_active = active_fn(float(p))
        is_active = active_fn(float(c))
        if not was_active and is_active:
            rows.append({"timestamp": pd.Timestamp(ts), "event": "entry", "value": float(c)})
        elif was_active and not is_active:
            rows.append({"timestamp": pd.Timestamp(ts), "event": "exit", "value": float(c)})
    return pd.DataFrame(rows)


def contiguous_flat_spans(series: pd.Series) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    flat = series.astype(float) <= 1e-9
    spans: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    start = None
    prev_ts = None
    for ts, is_flat in flat.items():
        if is_flat and start is None:
            start = pd.Timestamp(ts)
        if not is_flat and start is not None:
            spans.append((start, pd.Timestamp(prev_ts if prev_ts is not None else ts)))
            start = None
        prev_ts = ts
    if start is not None and prev_ts is not None:
        spans.append((start, pd.Timestamp(prev_ts)))
    return spans


def load_full_history() -> tuple[pd.DataFrame, pd.DataFrame]:
    file_5m = DASHBOARD_ROOT / "data" / "btc_usdt_swap_5m.csv"
    file_4h = DASHBOARD_ROOT / "data" / "btc_usdt_swap_4h.csv"
    df_5m = ensure_datetime(pd.read_csv(file_5m))
    df_4h = ensure_datetime(pd.read_csv(file_4h))
    return df_5m, df_4h


def build_full_package() -> dict:
    df_5m, df_4h = load_full_history()
    scenario = SCENARIOS[0]
    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    indicators = build_indicators(df_4h, riskoff_params, 250)
    core_target_unit = build_target(
        indicators,
        {
            "reentry_family": "weekly_rsi_hold",
            "rsi_period": 14,
            "threshold": 30.0,
            "ema_len": 250,
        },
    )
    bundle = base_bundle(df_5m, df_4h, scenario)
    sim = simulate_weight_combo(bundle, ADOPTED_POSTURE)

    idx = sim["combo_equity"].index
    recent = df_4h.set_index("timestamp").sort_index().copy()
    recent["ema250"] = indicators["ema"].reindex(recent.index).astype(float)
    recent["core_target"] = (
        core_target_unit.reindex(recent.index).ffill().fillna(1.0).astype(float) * ADOPTED_POSTURE["core_weight"]
    )
    recent["s1_weight"] = (
        (bundle["base_s1_weight"] * ADOPTED_POSTURE["sleeve1_weight"]).reindex(recent.index).fillna(0.0).astype(float)
    )
    recent["s2_weight"] = (
        (bundle["base_s2_weight"] * ADOPTED_POSTURE["sleeve2_weight"]).reindex(recent.index).fillna(0.0).astype(float)
    )
    equity = sim["combo_equity"].reindex(recent.index).ffill().bfill().astype(float)
    total_exposure = sim["combo_exposure"].reindex(recent.index).ffill().bfill().astype(float)

    return {
        "ohlc": recent[["open", "high", "low", "close", "ema250", "core_target", "s1_weight", "s2_weight"]],
        "equity": equity,
        "total_exposure": total_exposure,
        "core_events": transition_events(recent["core_target"], lambda x: x > 1e-9),
        "s1_events": transition_events(recent["s1_weight"], lambda x: x > 1e-9),
        "s2_events": transition_events(recent["s2_weight"], lambda x: x > 1e-9),
        "core_flat_spans": contiguous_flat_spans(recent["core_target"]),
    }


def iter_six_month_windows(index: pd.DatetimeIndex) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    start = pd.Timestamp(index.min())
    end = pd.Timestamp(index.max())
    anchors = [start]
    cur = start + pd.DateOffset(months=6)
    while cur <= end:
        anchors.append(pd.Timestamp(cur))
        cur = cur + pd.DateOffset(months=6)
    windows: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for anchor in anchors:
        left_pos = index.searchsorted(anchor)
        if left_pos >= len(index):
            continue
        left = pd.Timestamp(index[left_pos])
        nominal_right = anchor + pd.DateOffset(months=6)
        right_pos = index.searchsorted(nominal_right, side="left") - 1
        if right_pos < left_pos:
            right_pos = len(index) - 1
        right = pd.Timestamp(index[min(right_pos, len(index) - 1)])
        if right <= left:
            continue
        windows.append((left, right))
    return windows


def subset_events(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    mask = (df["timestamp"] >= start) & (df["timestamp"] <= end)
    return df.loc[mask].copy()


def draw_labeled_events(ax, price_df: pd.DataFrame, events: pd.DataFrame, kind: str) -> None:
    if events.empty:
        return
    price_index = price_df.index
    ypad = float((price_df["high"].max() - price_df["low"].min()) * 0.02)
    spec = {
        "core_entry": {"marker": "^", "color": "#111827", "text": "RE", "va": "top"},
        "core_exit": {"marker": "x", "color": "#111827", "text": "FLAT", "va": "bottom"},
        "s1_entry": {"marker": "o", "color": "#059669", "text": "S1B", "va": "top"},
        "s1_exit": {"marker": "o", "color": "#059669", "text": "S1S", "va": "bottom"},
        "s2_entry": {"marker": "s", "color": "#d97706", "text": "S2B", "va": "top"},
        "s2_exit": {"marker": "s", "color": "#d97706", "text": "S2S", "va": "bottom"},
    }[kind]

    for _, row in events.iterrows():
        ts = pd.Timestamp(row["timestamp"])
        if ts not in price_index:
            continue
        if spec["va"] == "top":
            y = float(price_df.loc[ts, "low"]) - ypad
            text_y = y - ypad * 0.2
        else:
            y = float(price_df.loc[ts, "high"]) + ypad
            text_y = y + ypad * 0.2
        ax.scatter([ts], [y], s=40, marker=spec["marker"], color=spec["color"], zorder=5)
        ax.text(ts, text_y, spec["text"], color=spec["color"], fontsize=8, ha="center", va=spec["va"])


def render_window(
    window_id: int,
    start: pd.Timestamp,
    end: pd.Timestamp,
    package: dict,
) -> dict:
    ohlc = package["ohlc"].loc[(package["ohlc"].index >= start) & (package["ohlc"].index <= end)].copy()
    equity = package["equity"].loc[(package["equity"].index >= start) & (package["equity"].index <= end)].copy()
    exposure = package["total_exposure"].loc[(package["total_exposure"].index >= start) & (package["total_exposure"].index <= end)].copy()
    if ohlc.empty or equity.empty:
        return {}

    core_events = subset_events(package["core_events"], start, end)
    s1_events = subset_events(package["s1_events"], start, end)
    s2_events = subset_events(package["s2_events"], start, end)
    flat_spans = [(a, b) for a, b in package["core_flat_spans"] if b >= start and a <= end]

    rebased = 100.0 * equity.astype(float) / float(equity.iloc[0])

    fig = plt.figure(figsize=(18, 12), constrained_layout=True)
    gs = fig.add_gridspec(3, 1, height_ratios=[2.5, 1.1, 0.7])
    ax_price = fig.add_subplot(gs[0, 0])
    ax_eq = fig.add_subplot(gs[1, 0], sharex=ax_price)
    ax_meta = fig.add_subplot(gs[2, 0])

    ax_price.set_title(
        f"Adopted Mainline Historical Signal Atlas | Window {window_id:02d} | "
        f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}"
    )

    x = mdates.date2num(ohlc.index.to_pydatetime())
    candle_width = 0.10
    o = ohlc["open"].astype(float)
    h = ohlc["high"].astype(float)
    l = ohlc["low"].astype(float)
    c = ohlc["close"].astype(float)

    for a, b in flat_spans:
        left = max(a, start)
        right = min(b, end)
        ax_price.axvspan(
            mdates.date2num(left.to_pydatetime()),
            mdates.date2num(right.to_pydatetime()),
            color="#e5e7eb",
            alpha=0.35,
        )

    for xi, oi, hi, li, ci in zip(x, o, h, l, c):
        color = "#16a34a" if ci >= oi else "#dc2626"
        ax_price.vlines(xi, li, hi, color=color, linewidth=0.8, alpha=0.95)
        body_low = min(oi, ci)
        body_h = max(abs(ci - oi), 1e-6)
        ax_price.add_patch(
            Rectangle(
                (xi - candle_width / 2, body_low),
                candle_width,
                body_h,
                facecolor=color,
                edgecolor=color,
                linewidth=0.8,
            )
        )

    ax_price.plot(ohlc.index, ohlc["ema250"].astype(float).values, color="#2563eb", linewidth=1.8, label="EMA250")

    draw_labeled_events(ax_price, ohlc, core_events[core_events["event"] == "entry"], "core_entry")
    draw_labeled_events(ax_price, ohlc, core_events[core_events["event"] == "exit"], "core_exit")
    draw_labeled_events(ax_price, ohlc, s1_events[s1_events["event"] == "entry"], "s1_entry")
    draw_labeled_events(ax_price, ohlc, s1_events[s1_events["event"] == "exit"], "s1_exit")
    draw_labeled_events(ax_price, ohlc, s2_events[s2_events["event"] == "entry"], "s2_entry")
    draw_labeled_events(ax_price, ohlc, s2_events[s2_events["event"] == "exit"], "s2_exit")

    ax_price.grid(alpha=0.2)
    ax_price.legend(loc="upper left")
    ax_price.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    ax_price.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    ax_eq.plot(rebased.index, rebased.values, color="#111827", linewidth=2.0, label="Equity (rebased=100)")
    ax_eq.fill_between(rebased.index, rebased.values, 100.0, color="#94a3b8", alpha=0.15)
    ax_eq.set_ylabel("Equity")
    ax_eq.grid(alpha=0.25)
    ax_eq.legend(loc="upper left")

    ax_meta.axis("off")
    meta_lines = [
        f"Bars: {len(ohlc)}",
        f"Window return: {rebased.iloc[-1] - 100.0:+.2f}%",
        f"Window max drawdown: {((equity / equity.cummax() - 1.0) * 100.0).min():.2f}%",
        f"Avg total exposure: {exposure.mean():.2f}",
        f"Core entry/exit: {int((core_events['event'] == 'entry').sum())}/{int((core_events['event'] == 'exit').sum())}",
        f"S1 buy/sell: {int((s1_events['event'] == 'entry').sum())}/{int((s1_events['event'] == 'exit').sum())}",
        f"S2 buy/sell: {int((s2_events['event'] == 'entry').sum())}/{int((s2_events['event'] == 'exit').sum())}",
        "Legend: grey zone=core flat | RE=core/re-entry restore | FLAT=core flat | S1B/S1S | S2B/S2S",
    ]
    ax_meta.text(0.01, 0.95, "\n".join(meta_lines), va="top", ha="left", fontsize=11, family="monospace")

    filename = f"{window_id:02d}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.png"
    path = OUTDIR / filename
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)

    return {
        "window_id": window_id,
        "start_utc": str(start),
        "end_utc": str(end),
        "bars": len(ohlc),
        "window_return_pct": float(rebased.iloc[-1] - 100.0),
        "window_maxdd_pct": float(((equity / equity.cummax() - 1.0) * 100.0).min()),
        "avg_total_exposure": float(exposure.mean()),
        "core_entry_count": int((core_events["event"] == "entry").sum()),
        "core_exit_count": int((core_events["event"] == "exit").sum()),
        "s1_buy_count": int((s1_events["event"] == "entry").sum()),
        "s1_sell_count": int((s1_events["event"] == "exit").sum()),
        "s2_buy_count": int((s2_events["event"] == "entry").sum()),
        "s2_sell_count": int((s2_events["event"] == "exit").sum()),
        "png_path": str(path),
    }


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    package = build_full_package()
    windows = iter_six_month_windows(pd.DatetimeIndex(package["ohlc"].index))
    rows = []
    for i, (start, end) in enumerate(windows, start=1):
        row = render_window(i, start, end, package)
        if row:
            rows.append(row)

    table = pd.DataFrame(rows)
    if table.empty:
        raise RuntimeError("no historical windows rendered")

    table.to_csv(INDEX_CSV, index=False)
    lines = [
        "# Historical Signal Atlas Summary",
        "",
        f"- windows rendered: `{len(table)}`",
        f"- first start: `{table['start_utc'].iloc[0]}`",
        f"- last end: `{table['end_utc'].iloc[-1]}`",
        "",
        "## Outputs",
        "",
        f"- index: `{INDEX_CSV.name}`",
        "- png files: `output/*.png`",
        "",
        "## Notes",
        "",
        "- Each PNG covers a 6-month 4h window.",
        "- Equity is rebased to 100 at each window start.",
        "- Core flat spans are shaded grey.",
        "- Core restore is marked `RE`; core flattening is marked `FLAT`.",
        "- Sleeve markers use text labels: `S1B`, `S1S`, `S2B`, `S2S`.",
    ]
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Rendered {len(table)} atlas windows into {OUTDIR}")


if __name__ == "__main__":
    main()
