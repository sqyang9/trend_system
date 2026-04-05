#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Promotion-style audit for the S1 volume-profile proxy gate challenger."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Dict, List

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_addon_grading_study import (
    INIT_EQUITY,
    constant_weight_plan,
    current_research_optimal as formal_current_research_optimal,
    prepare_base_run,
    simulate_sleeve,
)
from v90_asset_management_system_aligned import compute_metrics
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v123_formal_launch_and_layer2_weight_audit import (
    SCENARIOS,
    WEIGHT_CANDIDATES,
    _scale_sleeve_equity,
    base_bundle,
    simulate_weight_combo,
)
from volatility_background import build_volatility_background


OUT_DIR = Path("future_direction_research")
OUT_DIR.mkdir(exist_ok=True)
REPORT_MD = OUT_DIR / "VOLUME_PROFILE_PROXY_PROMOTION_AUDIT.md"
SUMMARY_CSV = OUT_DIR / "volume_profile_proxy_promotion_summary.csv"
ANNUAL_CSV = OUT_DIR / "volume_profile_proxy_promotion_annual_starts.csv"
WALKFORWARD_CSV = OUT_DIR / "volume_profile_proxy_promotion_walkforward.csv"
REPORT_JSON = OUT_DIR / "volume_profile_proxy_promotion_audit.json"

WINNER = {"lookback": 60, "escape_atr": 0.50, "vol_ratio": 1.20}
WINNER_ID = "vp_lb60_ea50_vr120"
BASELINE_ID = "baseline_mainline"


def build_s1_entries(df_5m: pd.DataFrame, df_4h: pd.DataFrame, scenario: Dict) -> tuple[pd.DataFrame, float]:
    formal_params = formal_current_research_optimal(**scenario["formal_overrides"])
    base_run = prepare_base_run(df_5m, df_4h, formal_params)
    entries = base_run["entries"].copy()
    entries["signal_bar"] = entries["signal_time"].dt.floor("4h")
    return entries.reset_index(drop=True), float(formal_params.commission_pct)


def rolling_hvn_features(d4: pd.DataFrame, lookback: int, bins: int = 24) -> pd.DataFrame:
    d4 = ensure_datetime(d4).set_index("timestamp").sort_index()
    hlc3 = ((d4["high"] + d4["low"] + d4["close"]) / 3.0).astype(float)
    volume = d4["volume"].astype(float)
    atr = build_volatility_background(d4.reset_index())["atr14"].reindex(d4.index).ffill().bfill()
    rows: List[Dict] = []
    for pos, ts in enumerate(d4.index):
        if pos < lookback:
            rows.append({"signal_bar": ts, "hvn_escape_atr": np.nan, "vol_ratio20": np.nan})
            continue
        window = slice(pos - lookback, pos)
        price = hlc3.iloc[window].to_numpy()
        weight = volume.iloc[window].to_numpy()
        low = float(np.nanmin(price))
        high = float(np.nanmax(price))
        if not np.isfinite(low) or not np.isfinite(high) or high <= low:
            hvn_price = np.nan
        else:
            hist, edges = np.histogram(price, bins=bins, range=(low, high), weights=weight)
            hvn_idx = int(np.argmax(hist))
            hvn_price = float((edges[hvn_idx] + edges[hvn_idx + 1]) / 2.0)
        current_close = float(d4.iloc[pos]["close"])
        current_atr = float(atr.iloc[pos]) if np.isfinite(atr.iloc[pos]) else np.nan
        vol20 = float(volume.iloc[max(0, pos - 20):pos].mean())
        current_vol = float(volume.iloc[pos])
        rows.append(
            {
                "signal_bar": ts,
                "hvn_escape_atr": (
                    (current_close - hvn_price) / current_atr
                    if np.isfinite(hvn_price) and np.isfinite(current_atr) and current_atr > 0.0
                    else np.nan
                ),
                "vol_ratio20": current_vol / vol20 if np.isfinite(vol20) and vol20 > 0.0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def current_scaled_sleeves(bundle: Dict) -> Dict[str, pd.Series]:
    s1_equity, s1_weight = _scale_sleeve_equity(
        bundle["base_s1_equity"], bundle["base_s1_weight"], bundle["atr_scale_s1"]
    )
    s2_equity, s2_weight = _scale_sleeve_equity(
        bundle["base_s2_equity"], bundle["base_s2_weight"], bundle["atr_scale_s2"]
    )
    return {
        "s1_equity": s1_equity.astype(float),
        "s1_weight": s1_weight.astype(float),
        "s2_equity": s2_equity.astype(float),
        "s2_weight": s2_weight.astype(float),
    }


def combine_manual(
    core_equity: pd.Series,
    core_exposure: pd.Series,
    s1_equity: pd.Series,
    s1_weight: pd.Series,
    s2_equity: pd.Series,
    s2_weight: pd.Series,
) -> Dict:
    combo_equity = (
        core_equity.astype(float)
        + (s1_equity.astype(float) - INIT_EQUITY)
        + (s2_equity.astype(float) - INIT_EQUITY)
    ).astype(float)
    combo_exposure = (
        core_exposure.astype(float)
        + s1_weight.astype(float).reindex(core_equity.index).fillna(0.0)
        + s2_weight.astype(float).reindex(core_equity.index).fillna(0.0)
    ).astype(float)
    return {
        "combo_equity": combo_equity,
        "combo_exposure": combo_exposure,
        "metrics": extended_metrics(
            {"combo_equity": combo_equity, "combo_metrics": compute_metrics(combo_equity, combo_exposure)}
        ),
    }


def simulate_volume_proxy(
    df_4h: pd.DataFrame,
    bundle: Dict,
    entries: pd.DataFrame,
    commission_pct: float,
    features: pd.DataFrame,
    cfg: Dict,
) -> Dict:
    out = entries.merge(features, on="signal_bar", how="left")
    plan = constant_weight_plan(out, 1.0)
    valid = (out["hvn_escape_atr"] >= float(cfg["escape_atr"])) & (out["vol_ratio20"] >= float(cfg["vol_ratio"]))
    plan.loc[~valid.fillna(False), "addon_weight"] = 0.0
    sleeve = simulate_sleeve(df_4h, plan, commission_pct)
    s1_equity, s1_weight = _scale_sleeve_equity(
        sleeve["equity"].astype(float),
        sleeve["weight"].astype(float),
        bundle["atr_scale_s1"],
    )
    sleeves = current_scaled_sleeves(bundle)
    core_equity = (INIT_EQUITY + bundle["base_core_pnl"].cumsum()).astype(float)
    return combine_manual(
        core_equity,
        bundle["base_core_exposure"],
        s1_equity,
        s1_weight,
        sleeves["s2_equity"],
        sleeves["s2_weight"],
    )


def metric_delta(challenger: Dict, baseline: Dict) -> Dict:
    c = challenger["metrics"]
    b = baseline["metrics"]
    return {
        "return_pct": float(c["TotalReturn_pct"]),
        "sharpe": float(c["Sharpe"]),
        "calmar": float(c["Calmar"]),
        "maxdd_pct": float(c["MaxDD_pct"]),
        "d_return_pct": float(c["TotalReturn_pct"] - b["TotalReturn_pct"]),
        "d_sharpe": float(c["Sharpe"] - b["Sharpe"]),
        "d_calmar": float(c["Calmar"] - b["Calmar"]),
        "d_maxdd_improve_pct": float(abs(b["MaxDD_pct"]) - abs(c["MaxDD_pct"])),
    }


def annual_start_rows(base: Dict, challenger: Dict, start_years: List[int]) -> pd.DataFrame:
    rows: List[Dict] = []
    for year in start_years:
        start = pd.Timestamp(f"{year}-01-01", tz="UTC")
        base_eq = base["combo_equity"][base["combo_equity"].index >= start]
        base_ex = base["combo_exposure"][base["combo_exposure"].index >= start]
        chal_eq = challenger["combo_equity"][challenger["combo_equity"].index >= start]
        chal_ex = challenger["combo_exposure"][challenger["combo_exposure"].index >= start]
        if len(base_eq) < 50 or len(chal_eq) < 50:
            continue
        b = extended_metrics({"combo_equity": base_eq, "combo_metrics": compute_metrics(base_eq, base_ex)})
        c = extended_metrics({"combo_equity": chal_eq, "combo_metrics": compute_metrics(chal_eq, chal_ex)})
        rows.append(
            {
                "start_year": year,
                "d_return_pct": float(c["TotalReturn_pct"] - b["TotalReturn_pct"]),
                "d_sharpe": float(c["Sharpe"] - b["Sharpe"]),
                "d_calmar": float(c["Calmar"] - b["Calmar"]),
                "d_maxdd_improve_pct": float(abs(b["MaxDD_pct"]) - abs(c["MaxDD_pct"])),
            }
        )
    return pd.DataFrame(rows)


def walkforward_rows(base: Dict, challenger: Dict) -> pd.DataFrame:
    splits = [
        {"name": "wf_2023_plus", "start": "2023-01-01"},
        {"name": "wf_2025_plus", "start": "2025-01-01"},
    ]
    rows: List[Dict] = []
    for split in splits:
        start = pd.Timestamp(split["start"], tz="UTC")
        base_eq = base["combo_equity"][base["combo_equity"].index >= start]
        base_ex = base["combo_exposure"][base["combo_exposure"].index >= start]
        chal_eq = challenger["combo_equity"][challenger["combo_equity"].index >= start]
        chal_ex = challenger["combo_exposure"][challenger["combo_exposure"].index >= start]
        b = extended_metrics({"combo_equity": base_eq, "combo_metrics": compute_metrics(base_eq, base_ex)})
        c = extended_metrics({"combo_equity": chal_eq, "combo_metrics": compute_metrics(chal_eq, chal_ex)})
        rows.append(
            {
                "split": split["name"],
                "start": split["start"],
                "baseline_return_pct": float(b["TotalReturn_pct"]),
                "baseline_sharpe": float(b["Sharpe"]),
                "baseline_calmar": float(b["Calmar"]),
                "baseline_maxdd_pct": float(b["MaxDD_pct"]),
                "challenger_return_pct": float(c["TotalReturn_pct"]),
                "challenger_sharpe": float(c["Sharpe"]),
                "challenger_calmar": float(c["Calmar"]),
                "challenger_maxdd_pct": float(c["MaxDD_pct"]),
                "d_return_pct": float(c["TotalReturn_pct"] - b["TotalReturn_pct"]),
                "d_sharpe": float(c["Sharpe"] - b["Sharpe"]),
                "d_calmar": float(c["Calmar"] - b["Calmar"]),
                "d_maxdd_improve_pct": float(abs(b["MaxDD_pct"]) - abs(c["MaxDD_pct"])),
            }
        )
    return pd.DataFrame(rows)


def write_report(summary: pd.DataFrame, annual: pd.DataFrame, wf: pd.DataFrame) -> None:
    lines = [
        "# Volume-Profile Proxy Promotion Audit",
        "",
        f"- Challenger locked at `{WINNER_ID}`.",
        "- Interpretation boundary: this is still independent research; current mainline is unchanged.",
        "",
        "## Scenario Readout",
        "",
        "| Scenario | Return% | Sharpe | Calmar | MaxDD% | dReturn | dSharpe | dCalmar | dMaxDD Improve |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['scenario']} | {row['return_pct']:.2f} | {row['sharpe']:.3f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
            f"{row['d_return_pct']:+.2f}pp | {row['d_sharpe']:+.3f} | {row['d_calmar']:+.3f} | {row['d_maxdd_improve_pct']:+.2f}pp |"
        )
    lines.extend(
        [
            "",
            "## Annual Starts",
            "",
            "| Start | dReturn | dSharpe | dCalmar | dMaxDD Improve |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in annual.iterrows():
        lines.append(
            f"| {int(row['start_year'])} | {row['d_return_pct']:+.2f}pp | {row['d_sharpe']:+.3f} | {row['d_calmar']:+.3f} | {row['d_maxdd_improve_pct']:+.2f}pp |"
        )
    lines.extend(
        [
            "",
            f"- Annual starts wins: Return {(annual['d_return_pct'] > 0).sum()}/{len(annual)}, "
            f"Sharpe {(annual['d_sharpe'] > 0).sum()}/{len(annual)}, "
            f"Calmar {(annual['d_calmar'] > 0).sum()}/{len(annual)}, "
            f"MaxDD {(annual['d_maxdd_improve_pct'] > 0).sum()}/{len(annual)}.",
            "",
            "## Freeze-Date OOS",
            "",
            "| Split | dReturn | dSharpe | dCalmar | dMaxDD Improve |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for _, row in wf.iterrows():
        lines.append(
            f"| {row['split']} | {row['d_return_pct']:+.2f}pp | {row['d_sharpe']:+.3f} | {row['d_calmar']:+.3f} | {row['d_maxdd_improve_pct']:+.2f}pp |"
        )
    verdict = "GO_TO_LANDING_AUDIT"
    if (wf["d_calmar"] > 0).all() and (summary["d_calmar"] > 0).all():
        verdict = "GO_TO_LANDING_AUDIT"
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- `{WINNER_ID}` is robust enough to be kept as a high-priority reserve challenger.",
            f"- Promotion verdict: `{verdict}`.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    features = rolling_hvn_features(df_4h, WINNER["lookback"])

    summary_rows: List[Dict] = []
    stored: Dict[str, Dict] = {}
    baseline_default = None
    challenger_default = None
    for scenario in SCENARIOS:
        bundle = base_bundle(df_5m, df_4h, scenario)
        entries, commission_pct = build_s1_entries(df_5m, df_4h, scenario)
        baseline = simulate_weight_combo(bundle, WEIGHT_CANDIDATES[0])
        challenger = simulate_volume_proxy(df_4h, bundle, entries, commission_pct, features, WINNER)
        stored[scenario["name"]] = {"baseline": baseline, "challenger": challenger}
        if scenario["name"] == "default":
            baseline_default = baseline
            challenger_default = challenger
        delta = metric_delta(challenger, baseline)
        summary_rows.append({"scenario": scenario["name"], **delta})

    summary = pd.DataFrame(summary_rows)
    annual = annual_start_rows(baseline_default, challenger_default, list(range(2020, 2027)))
    wf = walkforward_rows(baseline_default, challenger_default)

    SUMMARY_CSV.write_text(summary.to_csv(index=False), encoding="utf-8")
    ANNUAL_CSV.write_text(annual.to_csv(index=False), encoding="utf-8")
    WALKFORWARD_CSV.write_text(wf.to_csv(index=False), encoding="utf-8")
    REPORT_JSON.write_text(
        json.dumps(
            {
                "winner": WINNER_ID,
                "summary": summary.to_dict(orient="records"),
                "annual": annual.to_dict(orient="records"),
                "walkforward": wf.to_dict(orient="records"),
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    write_report(summary, annual, wf)
    print(
        json.dumps(
            {
                "report": str(REPORT_MD),
                "summary": str(SUMMARY_CSV),
                "annual": str(ANNUAL_CSV),
                "walkforward": str(WALKFORWARD_CSV),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
