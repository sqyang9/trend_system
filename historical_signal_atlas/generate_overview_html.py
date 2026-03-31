#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate an interactive overview HTML for the historical signal atlas."""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from generate_historical_signal_atlas import build_full_package


ROOT = Path(__file__).resolve().parent
OUTDIR = ROOT / "output"
INDEX_CSV = OUTDIR / "atlas_index.csv"
HTML_PATH = OUTDIR / "historical_signal_atlas_overview.html"


def build_price_figure(package: dict) -> str:
    ohlc = package["ohlc"].copy()
    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=ohlc.index,
            open=ohlc["open"],
            high=ohlc["high"],
            low=ohlc["low"],
            close=ohlc["close"],
            name="BTC 4H",
            increasing_line_color="#16a34a",
            decreasing_line_color="#dc2626",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ohlc.index,
            y=ohlc["ema250"],
            mode="lines",
            name="EMA250",
            line=dict(width=1.8, color="#2563eb"),
        )
    )

    shapes = []
    for start, end in package["core_flat_spans"]:
        shapes.append(
            dict(
                type="rect",
                xref="x",
                yref="paper",
                x0=start,
                x1=end,
                y0=0,
                y1=1,
                fillcolor="rgba(203,213,225,0.35)",
                line=dict(width=0),
                layer="below",
            )
        )

    def add_events(df: pd.DataFrame, event_type: str, name: str, color: str, symbol: str, text: str, use_low: bool) -> None:
        if df.empty:
            return
        sub = df[df["event"] == event_type].copy()
        if sub.empty:
            return
        sub = sub[sub["timestamp"].isin(ohlc.index)]
        if sub.empty:
            return
        ref_col = "low" if use_low else "high"
        y = ohlc.loc[sub["timestamp"], ref_col].astype(float)
        factor = 0.992 if use_low else 1.008
        position = "top center" if use_low else "bottom center"
        fig.add_trace(
            go.Scatter(
                x=sub["timestamp"],
                y=y * factor,
                mode="markers+text",
                name=name,
                text=[text] * len(sub),
                textposition=position,
                marker=dict(size=8, color=color, symbol=symbol),
            )
        )

    add_events(package["core_events"], "entry", "Core Restore", "#111827", "triangle-up", "RE", True)
    add_events(package["core_events"], "exit", "Core Flat", "#111827", "x", "FLAT", False)
    add_events(package["s1_events"], "entry", "Sleeve1 Buy", "#059669", "circle", "S1B", True)
    add_events(package["s1_events"], "exit", "Sleeve1 Sell", "#059669", "circle-open", "S1S", False)
    add_events(package["s2_events"], "entry", "Sleeve2 Buy", "#d97706", "square", "S2B", True)
    add_events(package["s2_events"], "exit", "Sleeve2 Sell", "#d97706", "square-open", "S2S", False)

    fig.update_layout(
        template="plotly_white",
        height=820,
        title="Full-History 4H BTC / EMA250 / Core Flat / Sleeve Events",
        hovermode="x unified",
        xaxis=dict(rangeslider=dict(visible=True)),
        yaxis=dict(title="Price"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        margin=dict(l=60, r=30, t=90, b=40),
        shapes=shapes,
    )
    return fig.to_html(full_html=False, include_plotlyjs=True)


def build_top_figure(package: dict) -> str:
    ohlc = package["ohlc"]
    equity = package["equity"].astype(float)
    exposure = package["total_exposure"].astype(float)
    btc_rebased = 100.0 * ohlc["close"].astype(float) / float(ohlc["close"].iloc[0])
    eq_rebased = 100.0 * equity / float(equity.iloc[0])
    underwater = (equity / equity.cummax() - 1.0) * 100.0

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.52, 0.24, 0.24],
        subplot_titles=("Full-History Equity (Log Scale)", "Underwater", "Total Exposure"),
    )
    fig.add_trace(
        go.Scatter(
            x=eq_rebased.index,
            y=eq_rebased.values,
            mode="lines",
            name="Mainline Equity (rebased)",
            line=dict(width=2.2, color="#111827"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=btc_rebased.index,
            y=btc_rebased.values,
            mode="lines",
            name="BTC Close (rebased)",
            line=dict(width=1.6, color="#2563eb"),
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=underwater.index,
            y=underwater.values,
            mode="lines",
            name="Underwater",
            line=dict(width=1.5, color="#dc2626"),
            showlegend=False,
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=exposure.index,
            y=exposure.values,
            mode="lines",
            name="Total Exposure",
            line=dict(width=1.5, color="#059669"),
            showlegend=False,
        ),
        row=3,
        col=1,
    )
    fig.add_hline(y=3.0, line_dash="dash", line_color="#b91c1c", row=3, col=1)
    fig.update_layout(
        template="plotly_white",
        height=980,
        hovermode="x unified",
        title="Historical Signal Atlas Overview",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0),
        margin=dict(l=60, r=30, t=90, b=40),
    )
    fig.update_yaxes(type="log", title_text="Index = 100", row=1, col=1)
    fig.update_yaxes(title_text="Underwater %", row=2, col=1)
    fig.update_yaxes(title_text="Exposure", row=3, col=1)
    return fig.to_html(full_html=False, include_plotlyjs=False)


def build_window_card(row: pd.Series) -> str:
    png_name = Path(str(row["png_path"])).name
    title = f"Window {int(row['window_id']):02d} | {row['start_utc']} -> {row['end_utc']}"
    stats = (
        f"Bars {int(row['bars'])} | "
        f"Return {row['window_return_pct']:+.2f}% | "
        f"MaxDD {row['window_maxdd_pct']:.2f}% | "
        f"AvgExp {row['avg_total_exposure']:.2f} | "
        f"Core {int(row['core_entry_count'])}/{int(row['core_exit_count'])} | "
        f"S1 {int(row['s1_buy_count'])}/{int(row['s1_sell_count'])} | "
        f"S2 {int(row['s2_buy_count'])}/{int(row['s2_sell_count'])}"
    )
    return f"""
<section class="window-card" id="window-{int(row['window_id']):02d}">
  <h2>{html.escape(title)}</h2>
  <p class="stats">{html.escape(stats)}</p>
  <img src="{html.escape(png_name)}" alt="{html.escape(title)}" />
</section>
"""


def main() -> None:
    if not INDEX_CSV.exists():
        raise FileNotFoundError(f"missing atlas index: {INDEX_CSV}")

    package = build_full_package()
    table = pd.read_csv(INDEX_CSV)

    nav = " ".join(
        f'<a href="#window-{int(r.window_id):02d}">{int(r.window_id):02d}</a>'
        for r in table.itertuples(index=False)
    )
    cards = "\n".join(build_window_card(row) for _, row in table.iterrows())
    price_chart = build_price_figure(package)
    top_chart = build_top_figure(package)

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Historical Signal Atlas Overview</title>
  <style>
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f8fafc;
      color: #0f172a;
    }}
    .wrap {{
      max-width: 1600px;
      margin: 0 auto;
      padding: 24px 20px 60px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 34px;
    }}
    .sub {{
      margin: 0 0 20px;
      color: #475569;
      line-height: 1.5;
    }}
    .nav {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 16px 0 28px;
    }}
    .nav a {{
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      background: #e2e8f0;
      color: #0f172a;
      text-decoration: none;
      font-size: 13px;
    }}
    .window-card {{
      margin: 28px 0 38px;
      padding: 16px;
      border-radius: 18px;
      background: white;
      box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
    }}
    .window-card h2 {{
      margin: 0 0 8px;
      font-size: 20px;
    }}
    .stats {{
      margin: 0 0 14px;
      color: #475569;
      font-size: 14px;
    }}
    .window-card img {{
      display: block;
      width: 100%;
      height: auto;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      background: white;
    }}
    .chart-block {{
      margin: 18px 0 30px;
      padding: 18px;
      border-radius: 18px;
      background: white;
      box-shadow: 0 10px 25px rgba(15, 23, 42, 0.06);
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Historical Signal Atlas Overview</h1>
    <p class="sub">
      The page starts with two zoomable Plotly views: a full-history 4h BTC signal map and a full-history equity panel.
      Below them, all 6-month signal atlas windows are stitched in chronological order.
      The equity chart uses log scale so long-horizon compounding remains readable.
    </p>
    <div class="nav">{nav}</div>
    <div class="chart-block" id="price-chart-block">{price_chart}</div>
    <div class="chart-block" id="equity-chart-block">{top_chart}</div>
    {cards}
  </div>
  <script>
    function parseX(v) {{
      return new Date(v).getTime();
    }}

    function collectVisibleIndices(xArr, x0, x1) {{
      const idx = [];
      for (let i = 0; i < xArr.length; i++) {{
        const ts = parseX(xArr[i]);
        if (ts >= x0 && ts <= x1) idx.push(i);
      }}
      return idx;
    }}

    function padLinear(minVal, maxVal) {{
      if (!isFinite(minVal) || !isFinite(maxVal)) return null;
      if (minVal === maxVal) {{
        const d = Math.abs(minVal) * 0.02 || 1;
        return [minVal - d, maxVal + d];
      }}
      const pad = (maxVal - minVal) * 0.06;
      return [minVal - pad, maxVal + pad];
    }}

    function padLog(minVal, maxVal) {{
      if (!isFinite(minVal) || !isFinite(maxVal) || minVal <= 0 || maxVal <= 0) return null;
      const lo = Math.log10(minVal);
      const hi = Math.log10(maxVal);
      const span = Math.max(hi - lo, 0.08);
      return [lo - span * 0.05, hi + span * 0.05];
    }}

    function getPlotDiv(blockId) {{
      const block = document.getElementById(blockId);
      return block ? block.querySelector('.js-plotly-plot') : null;
    }}

    function autorangePriceChart(gd) {{
      if (!gd || !gd._fullLayout || !gd._fullLayout.xaxis || !gd._fullLayout.xaxis.range) return;
      const range = gd._fullLayout.xaxis.range;
      const x0 = parseX(range[0]);
      const x1 = parseX(range[1]);
      const candle = gd.data[0];
      if (!candle || !candle.x) return;
      const idx = collectVisibleIndices(candle.x, x0, x1);
      if (!idx.length) return;
      let minY = Infinity;
      let maxY = -Infinity;
      idx.forEach(i => {{
        const lo = Number(candle.low[i]);
        const hi = Number(candle.high[i]);
        if (isFinite(lo)) minY = Math.min(minY, lo);
        if (isFinite(hi)) maxY = Math.max(maxY, hi);
      }});
      gd.data.forEach(trace => {{
        if (!trace.x || !trace.y) return;
        const vis = collectVisibleIndices(trace.x, x0, x1);
        vis.forEach(i => {{
          const y = Number(trace.y[i]);
          if (isFinite(y)) {{
            minY = Math.min(minY, y);
            maxY = Math.max(maxY, y);
          }}
        }});
      }});
      const padded = padLinear(minY, maxY);
      if (padded) Plotly.relayout(gd, {{'yaxis.range': padded}});
    }}

    function autorangeEquityChart(gd) {{
      if (!gd || !gd._fullLayout || !gd._fullLayout.xaxis3 || !gd._fullLayout.xaxis3.range) return;
      const range = gd._fullLayout.xaxis3.range;
      const x0 = parseX(range[0]);
      const x1 = parseX(range[1]);
      const updates = {{}};

      function collectTraceRange(traceIndex, axisName, isLog) {{
        const trace = gd.data[traceIndex];
        if (!trace || !trace.x || !trace.y) return;
        const vis = collectVisibleIndices(trace.x, x0, x1);
        if (!vis.length) return;
        let minY = Infinity;
        let maxY = -Infinity;
        vis.forEach(i => {{
          const y = Number(trace.y[i]);
          if (isFinite(y)) {{
            minY = Math.min(minY, y);
            maxY = Math.max(maxY, y);
          }}
        }});
        const padded = isLog ? padLog(minY, maxY) : padLinear(minY, maxY);
        if (padded) updates[axisName + '.range'] = padded;
      }}

      collectTraceRange(0, 'yaxis', true);
      collectTraceRange(1, 'yaxis', true);
      collectTraceRange(2, 'yaxis2', false);
      collectTraceRange(3, 'yaxis3', false);

      if (Object.keys(updates).length) Plotly.relayout(gd, updates);
    }}

    function bindAutorange(blockId, fn) {{
      const gd = getPlotDiv(blockId);
      if (!gd) return;
      gd.on('plotly_relayout', function(ev) {{
        if (!ev) return;
        if (
          ev['xaxis.range[0]'] !== undefined || ev['xaxis.range[1]'] !== undefined ||
          ev['xaxis3.range[0]'] !== undefined || ev['xaxis3.range[1]'] !== undefined ||
          ev['xaxis.autorange'] !== undefined || ev['xaxis3.autorange'] !== undefined
        ) {{
          fn(gd);
        }}
      }});
      setTimeout(function() {{ fn(gd); }}, 150);
    }}

    window.addEventListener('load', function() {{
      bindAutorange('price-chart-block', autorangePriceChart);
      bindAutorange('equity-chart-block', autorangeEquityChart);
    }});
  </script>
</body>
</html>
"""
    HTML_PATH.write_text(html_text, encoding="utf-8")
    print(f"Wrote {HTML_PATH}")


if __name__ == "__main__":
    main()
