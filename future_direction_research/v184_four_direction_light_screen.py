#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight independent screen for four forward-looking ideas vs current official mainline."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Dict, List, Tuple

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
from v90_asset_management_system_aligned import (
    compute_metrics,
    current_research_optimal as riskoff_current_research_optimal,
    simulate_core,
)
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v121_coreonly_riskoff_sellside_ema_audit import (
    build_indicators,
    build_instability_flags,
    build_target_trace,
)
from v123_formal_launch_and_layer2_weight_audit import (
    ADOPTED_SPEC,
    SCENARIOS,
    WEIGHT_CANDIDATES,
    _scale_sleeve_equity,
    base_bundle,
    simulate_weight_combo,
)
from volatility_background import build_volatility_background


OUT_DIR = Path("future_direction_research")
OUT_DIR.mkdir(exist_ok=True)
REPORT_MD = OUT_DIR / "FOUR_DIRECTION_LIGHT_SCREEN.md"
SUMMARY_CSV = OUT_DIR / "four_direction_light_screen_summary.csv"
REPORT_JSON = OUT_DIR / "four_direction_light_screen.json"

BASELINE_ID = WEIGHT_CANDIDATES[0]["id"]
KAMA_LABEL = "core_kama250"
VOLPROF_LABEL = "s1_volume_profile_proxy"
ATRBUDGET_LABEL = "s1_entry_fixed_atr_budget"
TIMEDECAY_LABEL = "s1_time_decay_6bar"


def _scenario_map() -> Dict[str, Dict]:
    return {row["name"]: row for row in SCENARIOS}


def _kama(series: pd.Series, er_len: int = 250, fast: int = 2, slow: int = 30) -> pd.Series:
    close = series.astype(float)
    change = close.diff(er_len).abs()
    volatility = close.diff().abs().rolling(er_len).sum()
    er = (change / volatility.replace(0.0, np.nan)).fillna(0.0).clip(lower=0.0, upper=1.0)
    fast_sc = 2.0 / (fast + 1.0)
    slow_sc = 2.0 / (slow + 1.0)
    sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

    kama = pd.Series(np.nan, index=close.index, dtype=float)
    seed_idx = min(er_len, len(close) - 1)
    if seed_idx < 0:
        return close.copy()
    kama.iloc[: seed_idx + 1] = close.iloc[: seed_idx + 1]
    for i in range(seed_idx + 1, len(close)):
        prev = kama.iloc[i - 1]
        if not np.isfinite(prev):
            prev = close.iloc[i - 1]
        kama.iloc[i] = prev + sc.iloc[i] * (close.iloc[i] - prev)
    return kama.ffill().bfill().astype(float)


def _current_scaled_sleeves(bundle: Dict) -> Dict[str, pd.Series]:
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


def _base_core_equity(bundle: Dict) -> pd.Series:
    return (INIT_EQUITY + bundle["base_core_pnl"].cumsum()).astype(float)


def _combine_manual(
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


def _signal_bar_map(series: pd.Series, signal_time: pd.Series) -> pd.Series:
    return series.reindex(signal_time.dt.floor("4h")).to_numpy()


def _build_s1_entries(df_5m: pd.DataFrame, df_4h: pd.DataFrame, scenario: Dict) -> Tuple[pd.DataFrame, Dict]:
    formal_params = formal_current_research_optimal(**scenario["formal_overrides"])
    base_run = prepare_base_run(df_5m, df_4h, formal_params)
    entries = base_run["entries"].copy()
    signals = base_run["signals"].copy()
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    signal_map = d4[["close", "high", "low", "volume"]].rename(
        columns={
            "close": "signal_close_4h",
            "high": "signal_high_4h",
            "low": "signal_low_4h",
            "volume": "signal_volume_4h",
        }
    )
    entries["signal_bar"] = entries["signal_time"].dt.floor("4h")
    entries = entries.merge(signal_map, left_on="signal_bar", right_index=True, how="left")
    return entries.reset_index(drop=True), {"commission_pct": float(formal_params.commission_pct)}


def _rolling_hvn_features(d4: pd.DataFrame, bars: pd.Index, lookback: int = 60, bins: int = 24) -> pd.DataFrame:
    ts_to_pos = {ts: i for i, ts in enumerate(d4.index)}
    hlc3 = ((d4["high"] + d4["low"] + d4["close"]) / 3.0).astype(float)
    volume = d4["volume"].astype(float)
    atr = build_volatility_background(d4.reset_index())["atr14"].reindex(d4.index).ffill().bfill()
    rows: List[Dict] = []
    for ts in bars:
        pos = ts_to_pos.get(ts)
        if pos is None or pos < lookback:
            rows.append({"signal_bar": ts, "hvn_price": np.nan, "hvn_escape_atr": np.nan, "vol_ratio20": np.nan})
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
        current_vol = float(volume.iloc[pos])
        vol20 = float(volume.iloc[max(0, pos - 20):pos].mean())
        rows.append(
            {
                "signal_bar": ts,
                "hvn_price": hvn_price,
                "hvn_escape_atr": (
                    (current_close - hvn_price) / current_atr
                    if np.isfinite(hvn_price) and np.isfinite(current_atr) and current_atr > 0.0
                    else np.nan
                ),
                "vol_ratio20": current_vol / vol20 if np.isfinite(vol20) and vol20 > 0.0 else np.nan,
            }
        )
    return pd.DataFrame(rows)


def _plan_s1_volume_profile(entries: pd.DataFrame, df_4h: pd.DataFrame) -> pd.DataFrame:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    hvn = _rolling_hvn_features(d4, pd.Index(entries["signal_bar"].dropna().unique()))
    out = entries.merge(hvn, on="signal_bar", how="left")
    plan = constant_weight_plan(out, 1.0)
    valid = (out["hvn_escape_atr"] >= 0.50) & (out["vol_ratio20"] >= 1.20)
    plan.loc[~valid.fillna(False), "addon_weight"] = 0.0
    plan["vp_valid"] = valid.fillna(False)
    return plan


def _plan_s1_entry_fixed_atr_budget(entries: pd.DataFrame, bundle: Dict, df_4h: pd.DataFrame) -> pd.DataFrame:
    spec = bundle["atrvt_s1_spec"]
    s1_background = build_volatility_background(
        df_4h,
        atr_ref_days=spec["atr_ref_days"],
        atr_ref_stat=spec["atr_ref_stat"],
        atr_scale_min=spec["atr_scale_min"],
        atr_scale_max=spec["atr_scale_max"],
    )
    plan = constant_weight_plan(entries, 1.0)
    plan["addon_weight"] = (
        s1_background["atr_scale"]
        .reindex(plan["entry_time"].dt.floor("4h"))
        .ffill()
        .fillna(1.0)
        .to_numpy()
    )
    return plan


def _plan_s1_time_decay(entries: pd.DataFrame, df_4h: pd.DataFrame, bars: int = 6, atr_activate: float = 2.5) -> pd.DataFrame:
    d4 = ensure_datetime(df_4h).set_index("timestamp").sort_index()
    pos_map = {ts: i for i, ts in enumerate(d4.index)}
    plan = constant_weight_plan(entries, 1.0)
    forced = []
    for idx, row in plan.iterrows():
        entry_bar = row["entry_time"].floor("4h")
        exit_bar = row["exit_time"].floor("4h")
        entry_pos = pos_map.get(entry_bar)
        if entry_pos is None:
            forced.append(False)
            continue
        natural_exit_pos = pos_map.get(exit_bar, entry_pos)
        if natural_exit_pos <= entry_pos:
            forced.append(False)
            continue
        bar_end = min(entry_pos + bars - 1, len(d4.index) - 1)
        if natural_exit_pos <= bar_end:
            forced.append(False)
            continue
        entry_atr = float(row["entry_atr"]) if "entry_atr" in row and pd.notna(row["entry_atr"]) else np.nan
        if not np.isfinite(entry_atr) or entry_atr <= 0.0:
            forced.append(False)
            continue
        target_price = float(row["entry_price"]) + atr_activate * entry_atr
        max_high = float(d4.iloc[entry_pos : bar_end + 1]["high"].max())
        if max_high < target_price:
            forced_exit_ts = d4.index[bar_end]
            forced_exit_px = float(d4.iloc[bar_end]["close"])
            plan.at[idx, "exit_time"] = forced_exit_ts
            plan.at[idx, "exit_price"] = forced_exit_px
            plan.at[idx, "exit_reason"] = "time_decay_6bar"
            forced.append(True)
        else:
            forced.append(False)
    plan["time_decay_forced"] = forced
    return plan


def _simulate_s1_plan(
    df_4h: pd.DataFrame,
    plan: pd.DataFrame,
    commission_pct: float,
    dynamic_scale: pd.Series | None = None,
) -> Tuple[pd.Series, pd.Series]:
    sleeve = simulate_sleeve(df_4h, plan, commission_pct)
    equity = sleeve["equity"].astype(float)
    weight = sleeve["weight"].astype(float)
    if dynamic_scale is None:
        return equity, weight
    return _scale_sleeve_equity(equity, weight, dynamic_scale)


def _kama_core_result(df_5m: pd.DataFrame, df_4h: pd.DataFrame, scenario: Dict, bundle: Dict) -> Dict:
    background = build_volatility_background(df_4h)
    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    indicators = build_indicators(df_4h, riskoff_params, ADOPTED_SPEC["ema_len"], background=background)
    indicators = indicators.copy()
    indicators["ema"] = _kama(indicators["close"], er_len=250, fast=2, slow=30)
    indicators["ema_slope"] = indicators["ema"].diff()
    instability = build_instability_flags(
        df_5m,
        df_4h,
        riskoff_params,
        ema_len=ADOPTED_SPEC["ema_len"],
        threshold=ADOPTED_SPEC["threshold"],
        flips30_threshold=ADOPTED_SPEC["flips30_threshold"],
        flips60_threshold=ADOPTED_SPEC["flips60_threshold"],
        hv_force_threshold=ADOPTED_SPEC.get("hv_force_threshold"),
        background=background,
    )
    target = build_target_trace(indicators, ADOPTED_SPEC, instability["instability_state"])["weight"].astype(float)
    core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
    sleeves = _current_scaled_sleeves(bundle)
    return _combine_manual(
        core_sim["equity"]["equity"].reindex(bundle["index"]).ffill().bfill(),
        core_sim["equity"]["exposure"].reindex(bundle["index"]).ffill().bfill(),
        sleeves["s1_equity"],
        sleeves["s1_weight"],
        sleeves["s2_equity"],
        sleeves["s2_weight"],
    )


def _s1_volume_profile_result(df_4h: pd.DataFrame, bundle: Dict, entries: pd.DataFrame, commission_pct: float) -> Dict:
    plan = _plan_s1_volume_profile(entries, df_4h)
    s1_equity, s1_weight = _simulate_s1_plan(
        df_4h,
        plan,
        commission_pct,
        dynamic_scale=bundle["atr_scale_s1"],
    )
    sleeves = _current_scaled_sleeves(bundle)
    return _combine_manual(
        _base_core_equity(bundle),
        bundle["base_core_exposure"],
        s1_equity,
        s1_weight,
        sleeves["s2_equity"],
        sleeves["s2_weight"],
    )


def _s1_entry_fixed_atr_budget_result(df_4h: pd.DataFrame, bundle: Dict, entries: pd.DataFrame, commission_pct: float) -> Dict:
    plan = _plan_s1_entry_fixed_atr_budget(entries, bundle, df_4h)
    s1_equity, s1_weight = _simulate_s1_plan(df_4h, plan, commission_pct, dynamic_scale=None)
    sleeves = _current_scaled_sleeves(bundle)
    return _combine_manual(
        _base_core_equity(bundle),
        bundle["base_core_exposure"],
        s1_equity,
        s1_weight,
        sleeves["s2_equity"],
        sleeves["s2_weight"],
    )


def _s1_time_decay_result(df_4h: pd.DataFrame, bundle: Dict, entries: pd.DataFrame, commission_pct: float) -> Dict:
    plan = _plan_s1_time_decay(entries, df_4h, bars=6, atr_activate=2.5)
    s1_equity, s1_weight = _simulate_s1_plan(
        df_4h,
        plan,
        commission_pct,
        dynamic_scale=bundle["atr_scale_s1"],
    )
    sleeves = _current_scaled_sleeves(bundle)
    return _combine_manual(
        _base_core_equity(bundle),
        bundle["base_core_exposure"],
        s1_equity,
        s1_weight,
        sleeves["s2_equity"],
        sleeves["s2_weight"],
    )


def _row(name: str, scenario: str, result: Dict, baseline: Dict) -> Dict:
    m = result["metrics"]
    b = baseline["metrics"]
    return {
        "candidate": name,
        "scenario": scenario,
        "return_pct": float(m["TotalReturn_pct"]),
        "sharpe": float(m["Sharpe"]),
        "calmar": float(m["Calmar"]),
        "maxdd_pct": float(m["MaxDD_pct"]),
        "exposure_pct": float(m["Exposure_pct"]),
        "d_return_pct": float(m["TotalReturn_pct"] - b["TotalReturn_pct"]),
        "d_sharpe": float(m["Sharpe"] - b["Sharpe"]),
        "d_calmar": float(m["Calmar"] - b["Calmar"]),
        "d_maxdd_improve_pct": float(abs(b["MaxDD_pct"]) - abs(m["MaxDD_pct"])),
    }


def _decision_text(default_rows: pd.DataFrame) -> List[str]:
    lines: List[str] = []
    rank = default_rows.sort_values(["calmar", "return_pct"], ascending=False)
    for _, row in rank.iterrows():
        name = row["candidate"]
        d_ret = float(row["d_return_pct"])
        d_calmar = float(row["d_calmar"])
        d_dd = float(row["d_maxdd_improve_pct"])
        if name == "baseline_mainline":
            continue
        if d_calmar > 0 and d_ret > 0 and d_dd > 0:
            verdict = "frontier-positive"
        elif d_calmar > 0 or d_dd > 0:
            verdict = "reserve-only"
        else:
            verdict = "no-go"
        lines.append(
            f"- `{name}`: {verdict}; default `dReturn {d_ret:+.2f}pp / dSharpe {row['d_sharpe']:+.3f} / dCalmar {d_calmar:+.3f} / dMaxDD improve {d_dd:+.2f}pp`."
        )
    return lines


def write_report(rows: pd.DataFrame) -> None:
    default_rows = rows[rows["scenario"] == "default"].copy()
    scenario_order = ["default", "stress", "harsh_friction"]
    candidate_order = [
        "baseline_mainline",
        KAMA_LABEL,
        VOLPROF_LABEL,
        ATRBUDGET_LABEL,
        TIMEDECAY_LABEL,
    ]
    labels = {
        "baseline_mainline": "Current Official Mainline",
        KAMA_LABEL: "Core KAMA250 Divider",
        VOLPROF_LABEL: "S1 Volume-Profile Proxy Gate",
        ATRBUDGET_LABEL: "S1 Entry-Fixed ATR Budget",
        TIMEDECAY_LABEL: "S1 Time-Decay Exit (6 bars)",
    }
    lines = [
        "# Four-Direction Light Screen",
        "",
        "- Scope: lightweight independent screen only; current mainline stays unchanged.",
        "- Baseline mainline: asymmetric ATRVT (`S1 90d`, `S2 60d`) + current hybrid core qualification.",
        "- Direction (3) note: the current mainline already contains sleeve-level ATRVT. This probe tests a narrower `entry-fixed ATR budget` replacement on `S1`, not a brand-new volatility-targeting layer.",
        "",
    ]
    for scenario in scenario_order:
        lines.extend(
            [
                f"## {scenario}",
                "",
                "| Candidate | Return% | Sharpe | Calmar | MaxDD% | dReturn | dSharpe | dCalmar | dMaxDD Improve |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        sub = rows[rows["scenario"] == scenario].set_index("candidate")
        for name in candidate_order:
            row = sub.loc[name]
            lines.append(
                f"| {labels[name]} | {row['return_pct']:.2f} | {row['sharpe']:.3f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
                f"{row['d_return_pct']:+.2f}pp | {row['d_sharpe']:+.3f} | {row['d_calmar']:+.3f} | {row['d_maxdd_improve_pct']:+.2f}pp |"
            )
        lines.append("")
    lines.extend(
        [
            "## Readout",
            "",
            * _decision_text(default_rows),
            "",
            "## Candidate Definitions",
            "",
            "- `Core KAMA250 Divider`: swap the core trend divider from `EMA250` to `KAMA250`; keep the same high-churn logic and sleeves.",
            "- `S1 Volume-Profile Proxy Gate`: require `4h volume > 1.2x rolling20 mean` and breakout close to sit at least `0.5 ATR` above a `60-bar` rolling HVN proxy before allowing the S1 trade.",
            "- `S1 Entry-Fixed ATR Budget`: replace dynamic S1 ATRVT with an entry-fixed ATR budget weight using the current adopted `S1 90d` ATRVT scale sampled at entry.",
            "- `S1 Time-Decay Exit (6 bars)`: if a breakout trade fails to reach `+2.5 ATR` expansion inside `6` bars, force-close at the `6th` bar close.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    rows: List[Dict] = []
    report: Dict[str, Dict] = {}
    for scenario in SCENARIOS:
        bundle = base_bundle(df_5m, df_4h, scenario)
        entries, meta = _build_s1_entries(df_5m, df_4h, scenario)
        baseline = simulate_weight_combo(bundle, WEIGHT_CANDIDATES[0])
        kama_res = _kama_core_result(df_5m, df_4h, scenario, bundle)
        vp_res = _s1_volume_profile_result(df_4h, bundle, entries, meta["commission_pct"])
        atr_budget_res = _s1_entry_fixed_atr_budget_result(df_4h, bundle, entries, meta["commission_pct"])
        time_decay_res = _s1_time_decay_result(df_4h, bundle, entries, meta["commission_pct"])

        scenario_pack = {
            "baseline_mainline": baseline,
            KAMA_LABEL: kama_res,
            VOLPROF_LABEL: vp_res,
            ATRBUDGET_LABEL: atr_budget_res,
            TIMEDECAY_LABEL: time_decay_res,
        }
        report[scenario["name"]] = {}
        for name, result in scenario_pack.items():
            report[scenario["name"]][name] = {"metrics": result["metrics"]}
            rows.append(_row(name, scenario["name"], result, baseline))

    summary = pd.DataFrame(rows)
    SUMMARY_CSV.write_text(summary.to_csv(index=False), encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    write_report(summary)
    print(json.dumps({"report": str(REPORT_MD), "summary": str(SUMMARY_CSV), "json": str(REPORT_JSON)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
