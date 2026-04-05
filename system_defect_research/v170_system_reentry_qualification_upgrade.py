#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""System-level re-entry qualification upgrade screen for choppy-downtrend defense."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig_system_defect_research")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_addon_grading_study import current_research_optimal as formal_current_research_optimal
from v90_asset_management_system_aligned import compute_metrics, current_research_optimal as riskoff_current_research_optimal, simulate_core
from v90_riskoff_promotion_v2 import build_indicator_cache
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v92_const1x_deployment_audit import loss_cluster_diagnostics, path_diagnostics
from v95_range_rotation_mean_reversion_audit import make_range_rotation_params
from v96_range_rotation_mean_reversion_s3_audit import scenario_systems
from v121_coreonly_riskoff_sellside_ema_audit import build_indicators as build_core_indicators
from v121_coreonly_riskoff_sellside_ema_audit import build_target as build_baseline_target
from v123_formal_launch_and_layer2_weight_audit import SCENARIOS


OUT_DIR = Path("system_defect_research")
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_MD = OUT_DIR / "SYSTEM_REENTRY_QUALIFICATION_UPGRADE.md"
SUMMARY_CSV = OUT_DIR / "system_reentry_qualification_upgrade_summary.csv"
CHURN_CSV = OUT_DIR / "system_reentry_qualification_upgrade_churn.csv"
SUMMARY_JSON = OUT_DIR / "system_reentry_qualification_upgrade_summary.json"

ADOPTED_BASELINE_SPEC = {
    "name": "WRSI14_30_EMA250",
    "reentry_family": "weekly_rsi_hold",
    "rsi_period": 14,
    "threshold": 30.0,
    "ema_len": 250,
}

W11_START = pd.Timestamp("2024-12-16 04:00:00", tz="UTC")
W11_END = pd.Timestamp("2025-06-16 00:00:00", tz="UTC")


@dataclass(frozen=True)
class QualSpec:
    key: str
    label: str
    unstable_flips30: int | None
    unstable_flips60: int | None
    highly_flips30: int
    highly_flips60: int
    breakout_window: int


GRID: List[QualSpec] = [
    QualSpec("baseline", "Current mainline", None, None, 2, 3, 4),
    QualSpec("u12_hc23_b4", "Unstable 1/2 strict; HC 2/3 breakout4", 1, 2, 2, 3, 4),
    QualSpec("u13_hc23_b4", "Unstable 1/3 strict; HC 2/3 breakout4", 1, 3, 2, 3, 4),
    QualSpec("u12_hc23_b3", "Unstable 1/2 strict; HC 2/3 breakout3", 1, 2, 2, 3, 3),
    QualSpec("u12_hc24_b4", "Unstable 1/2 strict; HC 2/4 breakout4", 1, 2, 2, 4, 4),
]


def compute_rsi(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def build_indicators(df_4h: pd.DataFrame, riskoff_params) -> pd.DataFrame:
    cache = build_indicator_cache(df_4h, riskoff_params, [50, 250], ensure_datetime(df_4h)["timestamp"])
    out = cache[250].copy()
    out["ema50"] = cache[50]["ema"]
    out["ema50_slope"] = cache[50]["ema_slope"]
    weekly_close = out["close"].resample("W-SUN").last()
    out["weekly_rsi_14"] = compute_rsi(weekly_close, 14).reindex(out.index, method="ffill")
    return out


def strict_ema50_ok(row: pd.Series) -> bool:
    return bool(pd.notna(row["ema50"]) and pd.notna(row["ema50_slope"]) and row["ema50"] > row["ema"] and row["ema50_slope"] > 0)


def baseline_core_transitions(df_5m: pd.DataFrame, df_4h: pd.DataFrame, riskoff_params) -> pd.Series:
    indicators = build_core_indicators(df_4h, riskoff_params, ADOPTED_BASELINE_SPEC["ema_len"])
    target = build_baseline_target(indicators, ADOPTED_BASELINE_SPEC)
    core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
    exposure = core_sim["equity"]["exposure"].reindex(indicators.index).ffill().bfill().astype(float)
    transitions = pd.Series(0, index=exposure.index, dtype=int)
    transitions.loc[exposure.diff().abs().fillna(0.0) > 1e-9] = 1
    return transitions


def instability_multitier(transitions: pd.Series, spec: QualSpec) -> pd.DataFrame:
    roll30 = transitions.rolling(30 * 6, min_periods=1).sum()
    roll60 = transitions.rolling(60 * 6, min_periods=1).sum()
    out = pd.DataFrame(index=transitions.index)
    out["core_flips_30d"] = roll30
    out["core_flips_60d"] = roll60
    out["instability_state"] = "stable"
    if spec.unstable_flips30 is not None and spec.unstable_flips60 is not None:
        unstable = (roll30 >= spec.unstable_flips30) & (roll60 >= spec.unstable_flips60)
        out.loc[unstable, "instability_state"] = "unstable"
    highly = (roll30 >= spec.highly_flips30) & (roll60 >= spec.highly_flips60)
    out.loc[highly, "instability_state"] = "highly_unstable"
    return out


def build_target_and_events(indicators: pd.DataFrame, instability: pd.DataFrame, spec: QualSpec) -> tuple[pd.Series, pd.DataFrame]:
    bearish = (indicators["close"] < indicators["ema"]) & (indicators["ema_slope"] < 0)
    close_confirm = indicators["close"] > indicators["ema"]
    weekly_trigger = (indicators["weekly_rsi_14"] <= 30.0).fillna(False)
    env_state = instability["instability_state"].reindex(indicators.index).ffill().fillna("stable")

    state = "normal"
    bear_count = 0
    close_count = 0
    qual_bars = 0
    armed_trigger_high = np.nan
    weights: list[float] = []
    events: list[dict] = []

    for ts, row in indicators.iterrows():
        is_bear = bool(bearish.loc[ts]) if pd.notna(bearish.loc[ts]) else False
        is_close = bool(close_confirm.loc[ts]) if pd.notna(close_confirm.loc[ts]) else False
        trig = bool(weekly_trigger.loc[ts])
        env = str(env_state.loc[ts])
        strict_ok = strict_ema50_ok(row)

        bear_count = bear_count + 1 if is_bear else 0
        close_count = close_count + 1 if is_close else 0

        prev_state = state
        event = ""
        reentry_path = ""

        if state == "normal":
            if bear_count >= 2:
                state = "flat"
                event = "FLAT"
            elif bear_count == 1:
                state = "soft_off"
        elif state == "soft_off":
            if bear_count >= 2:
                state = "flat"
                event = "FLAT"
            elif bear_count == 0:
                state = "normal"
        elif state == "flat":
            if trig:
                state = "override_hold"
                event = "RE"
                reentry_path = "weekly_rsi30_hold"
                bear_count = 0
                close_count = 0
            elif close_count >= 3:
                if env == "stable":
                    state = "normal"
                    event = "RE"
                    reentry_path = "stable_close3"
                    bear_count = 0
                    close_count = 0
                elif env == "unstable":
                    if strict_ok:
                        state = "normal"
                        event = "RE"
                        reentry_path = "unstable_strict_ema50"
                        bear_count = 0
                        close_count = 0
                elif env == "highly_unstable":
                    if strict_ok:
                        state = "armed"
                        event = "QUALIFY"
                        reentry_path = f"high_churn_breakout{spec.breakout_window}"
                        qual_bars = 0
                        armed_trigger_high = float(row["high"])
                        bear_count = 0
                        close_count = 0
        elif state == "armed":
            qual_bars += 1
            if trig:
                state = "override_hold"
                event = "RE"
                reentry_path = "weekly_rsi30_hold"
                qual_bars = 0
                armed_trigger_high = np.nan
                bear_count = 0
                close_count = 0
            elif bear_count >= 2 or qual_bars >= spec.breakout_window:
                state = "flat"
                event = "QUALIFY_FAIL"
                qual_bars = 0
                armed_trigger_high = np.nan
                bear_count = 0
                close_count = 0
            elif pd.notna(armed_trigger_high) and row["close"] > armed_trigger_high:
                state = "normal"
                event = "RE"
                reentry_path = f"high_churn_strict_breakout{spec.breakout_window}"
                qual_bars = 0
                armed_trigger_high = np.nan
                bear_count = 0
                close_count = 0
        elif state == "override_hold":
            if close_count >= 3:
                state = "normal"

        weight = 1.0 if state in {"normal", "override_hold"} else 0.5 if state == "soft_off" else 0.0
        weights.append(weight)
        if event:
            events.append(
                {
                    "timestamp": ts,
                    "candidate": spec.key,
                    "event": event,
                    "from_state": prev_state,
                    "to_state": state,
                    "reentry_path": reentry_path,
                    "instability_state": env,
                }
            )
    target = pd.Series(weights, index=indicators.index, dtype=float)
    events_df = pd.DataFrame(events)
    if not events_df.empty:
        events_df["timestamp"] = pd.to_datetime(events_df["timestamp"], utc=True)
    return target, events_df


def build_cycles(events: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "candidate",
        "flat_time",
        "re_time",
        "reentry_path",
        "instability_state",
        "days_re_to_next_flat",
        "quick_reflat_after_re_14d",
        "quick_reflat_after_re_30d",
    ]
    if events.empty:
        return pd.DataFrame(columns=cols)
    flats = events[events["event"] == "FLAT"].sort_values("timestamp").reset_index(drop=True)
    res = events[events["event"] == "RE"].sort_values("timestamp").reset_index(drop=True)
    rows = []
    for _, flat in flats.iterrows():
        later_re = res[res["timestamp"] > flat["timestamp"]]
        if later_re.empty:
            continue
        re = later_re.iloc[0]
        later_flat = flats[flats["timestamp"] > re["timestamp"]]
        next_flat = later_flat.iloc[0] if not later_flat.empty else None
        rows.append(
            {
                "candidate": flat["candidate"],
                "flat_time": flat["timestamp"],
                "re_time": re["timestamp"],
                "reentry_path": re["reentry_path"],
                "instability_state": re["instability_state"],
                "days_re_to_next_flat": float((next_flat["timestamp"] - re["timestamp"]).total_seconds() / 86400.0) if next_flat is not None else np.nan,
                "quick_reflat_after_re_14d": bool(next_flat is not None and (next_flat["timestamp"] - re["timestamp"]).total_seconds() / 86400.0 <= 14.0),
                "quick_reflat_after_re_30d": bool(next_flat is not None and (next_flat["timestamp"] - re["timestamp"]).total_seconds() / 86400.0 <= 30.0),
            }
        )
    return pd.DataFrame(rows, columns=cols)


def build_formal_bundle(df_5m: pd.DataFrame, df_4h: pd.DataFrame, formal_overrides: Dict) -> dict:
    formal_params = formal_current_research_optimal(**formal_overrides)
    range_params = make_range_rotation_params(**formal_overrides)
    payload = scenario_systems(formal_params, range_params, df_5m, df_4h)
    systems = payload["systems"]
    const1x = systems["Core+ConstAddOn[1.00x]"]
    idx = const1x["combo_equity"].index
    candidate_sleeve = payload["candidate_sleeve"]
    return {
        "index": idx,
        "s1_equity": const1x["sleeve"]["equity"].reindex(idx).ffill().bfill().astype(float),
        "s1_weight": const1x["sleeve"]["weight"].reindex(idx).fillna(0.0).astype(float),
        "s2_equity": candidate_sleeve["equity"].reindex(idx).ffill().bfill().astype(float),
        "s2_weight": candidate_sleeve["weight"].reindex(idx).fillna(0.0).astype(float),
    }


def path_bundle(equity: pd.Series) -> dict:
    pdx = path_diagnostics(equity)
    clusters = loss_cluster_diagnostics(equity)
    maxdd_episode = pdx["worst_underwater_episodes"][0] if pdx["worst_underwater_episodes"] else None
    return {
        "worst_3m_cluster_return_pct": float(clusters["worst_3m_cluster_return_pct"]),
        "worst_6m_cluster_return_pct": float(clusters["worst_6m_cluster_return_pct"]),
        "recovery_days_from_maxdd": float(maxdd_episode["recovery_days_from_trough"]) if maxdd_episode is not None else 0.0,
    }


def evaluate_combo(bundle: dict, core_sim: dict) -> dict:
    idx = bundle["index"]
    s1_equity = bundle["s1_equity"]
    s2_equity = bundle["s2_equity"]
    init_equity = float(s1_equity.iloc[0])
    core_equity = core_sim["equity"]["equity"].reindex(idx).ffill().bfill().astype(float)
    core_exposure = core_sim["equity"]["exposure"].reindex(idx).ffill().bfill().astype(float)
    combo_equity = (core_equity + (s1_equity - init_equity) + (s2_equity - init_equity)).astype(float)
    combo_exposure = (core_exposure + bundle["s1_weight"] + bundle["s2_weight"]).astype(float)
    metrics = extended_metrics({"combo_equity": combo_equity, "combo_metrics": compute_metrics(combo_equity, combo_exposure)})
    return {
        "combo_equity": combo_equity,
        "combo_exposure": combo_exposure,
        "metrics": metrics,
        "path": path_bundle(combo_equity),
        "avg_core_exposure_pct": float(core_exposure.mean() * 100.0),
        "core_exposure": core_exposure,
    }


def w11_metrics(core_exposure: pd.Series, combo_equity: pd.Series, combo_exposure: pd.Series, cycles: pd.DataFrame) -> dict:
    mask = (combo_equity.index >= W11_START) & (combo_equity.index <= W11_END)
    eq = combo_equity.loc[mask].astype(float)
    ex = combo_exposure.loc[mask].astype(float)
    core = core_exposure.loc[mask].astype(float)
    win_cycles = cycles[(cycles["flat_time"] >= W11_START) & (cycles["flat_time"] <= W11_END)]
    valid = win_cycles["days_re_to_next_flat"].dropna()
    return {
        "w11_return_pct": float(eq.iloc[-1] / eq.iloc[0] - 1.0) * 100.0 if len(eq) >= 2 else 0.0,
        "w11_maxdd_pct": float((eq / eq.cummax() - 1.0).min() * 100.0) if len(eq) >= 2 else 0.0,
        "w11_avg_total_exposure": float(ex.mean()) if len(ex) else 0.0,
        "w11_avg_core_exposure": float(core.mean()) if len(core) else 0.0,
        "w11_entry_count": int(len(win_cycles)),
        "w11_quick_reflat_14d_pct": float(win_cycles["quick_reflat_after_re_14d"].mean() * 100.0) if not win_cycles.empty else 0.0,
        "w11_quick_reflat_30d_pct": float(win_cycles["quick_reflat_after_re_30d"].mean() * 100.0) if not win_cycles.empty else 0.0,
        "w11_median_reflat_days": float(valid.median()) if not valid.empty else np.nan,
    }


def summarize_churn(cycles: pd.DataFrame, spec: QualSpec) -> dict:
    sub = cycles[cycles["candidate"] == spec.key].copy()
    hc = sub[sub["instability_state"] == "highly_unstable"].copy()
    return {
        "candidate": spec.key,
        "label": spec.label,
        "full_re_count": int(len(sub)),
        "quick_reflat_14d_ratio_pct": float(sub["quick_reflat_after_re_14d"].mean() * 100.0) if not sub.empty else np.nan,
        "quick_reflat_30d_ratio_pct": float(sub["quick_reflat_after_re_30d"].mean() * 100.0) if not sub.empty else np.nan,
        "highly_unstable_re_count": int(len(hc)),
        "highly_unstable_quick_reflat_14d_ratio_pct": float(hc["quick_reflat_after_re_14d"].mean() * 100.0) if not hc.empty else np.nan,
        "highly_unstable_quick_reflat_30d_ratio_pct": float(hc["quick_reflat_after_re_30d"].mean() * 100.0) if not hc.empty else np.nan,
    }


def evaluate_scenario(df_5m: pd.DataFrame, df_4h: pd.DataFrame, scenario: Dict) -> dict:
    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    indicators = build_indicators(df_4h, riskoff_params)
    transitions = baseline_core_transitions(df_5m, df_4h, riskoff_params)
    bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])

    systems = {}
    churn_rows: list[dict] = []
    for spec in GRID:
        if spec.key == "baseline":
            baseline_instability = pd.DataFrame(index=transitions.index)
            baseline_instability["instability_state"] = np.where(
                (transitions.rolling(30 * 6, min_periods=1).sum() >= 2) & (transitions.rolling(60 * 6, min_periods=1).sum() >= 3),
                "highly_unstable",
                "stable",
            )
            instability = baseline_instability
        else:
            instability = instability_multitier(transitions, spec)
        target, events = build_target_and_events(indicators, instability, spec)
        core_sim = simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)
        combo = evaluate_combo(bundle, core_sim)
        cycles = build_cycles(events)
        systems[spec.key] = {
            **combo,
            "events": events,
            "cycles": cycles,
            "instability": instability,
        }
        if scenario["name"] == "default":
            churn = summarize_churn(cycles, spec)
            churn.update(w11_metrics(combo["core_exposure"], combo["combo_equity"], combo["combo_exposure"], cycles))
            churn_rows.append(churn)
    return {"systems": systems, "churn_rows": churn_rows}


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    summary_rows: list[dict] = []
    churn_rows: list[dict] = []
    report = {}
    for scenario in SCENARIOS:
        result = evaluate_scenario(df_5m, df_4h, scenario)
        report[scenario["name"]] = result
        for spec in GRID:
            system = result["systems"][spec.key]
            summary_rows.append(
                {
                    "scenario": scenario["name"],
                    "candidate": spec.key,
                    "label": spec.label,
                    "return_pct": float(system["metrics"]["TotalReturn_pct"]),
                    "calmar": float(system["metrics"]["Calmar"]),
                    "maxdd_pct": float(system["metrics"]["MaxDD_pct"]),
                    "worst3m_pct": float(system["path"]["worst_3m_cluster_return_pct"]),
                    "worst6m_pct": float(system["path"]["worst_6m_cluster_return_pct"]),
                    "recovery_days": float(system["path"]["recovery_days_from_maxdd"]),
                    "avg_core_exposure_pct": float(system["avg_core_exposure_pct"]),
                }
            )
        churn_rows.extend(result["churn_rows"])

    summary_df = pd.DataFrame(summary_rows)
    churn_df = pd.DataFrame(churn_rows)
    SUMMARY_CSV.write_text(summary_df.to_csv(index=False), encoding="utf-8")
    CHURN_CSV.write_text(churn_df.to_csv(index=False), encoding="utf-8")
    SUMMARY_JSON.write_text(
        json.dumps({"summary": summary_rows, "churn": churn_rows}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    default_df = summary_df[summary_df["scenario"] == "default"].copy()
    baseline = default_df[default_df["candidate"] == "baseline"].iloc[0]
    merged = default_df.merge(churn_df[["candidate", "w11_entry_count", "w11_quick_reflat_14d_pct", "w11_quick_reflat_30d_pct", "highly_unstable_quick_reflat_14d_ratio_pct"]], on="candidate")
    best = merged.sort_values(
        ["w11_quick_reflat_14d_pct", "highly_unstable_quick_reflat_14d_ratio_pct", "calmar", "return_pct"],
        ascending=[True, True, False, False],
    ).iloc[0]

    lines = [
        "# System Re-Entry Qualification Upgrade",
        "",
        "- Scope: system-level upgrade candidates for choppy-downtrend false re-entry defense.",
        "- Stable environment remains `close3`.",
        "- Upgrade focus: add an earlier `unstable` tier before current `highly_unstable` tier, and lightly test breakout-window length.",
        "",
        "## Default Summary",
        "",
        "| Candidate | Return% | Calmar | MaxDD% | W11 Entries | W11 quick14 | W11 quick30 | HC quick14 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    table = merged.sort_values(["calmar", "return_pct"], ascending=[False, False])
    for _, row in table.iterrows():
        lines.append(
            f"| {row['label']} | {row['return_pct']:.2f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
            f"{int(row['w11_entry_count'])} | {row['w11_quick_reflat_14d_pct']:.1f}% | {row['w11_quick_reflat_30d_pct']:.1f}% | "
            f"{row['highly_unstable_quick_reflat_14d_ratio_pct']:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Stress / Harsh",
            "",
            "| Candidate | Stress Calmar | Stress MaxDD% | Harsh Calmar | Harsh MaxDD% |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    stress_df = summary_df[summary_df["scenario"] == "stress"].set_index("candidate")
    harsh_df = summary_df[summary_df["scenario"] == "harsh_friction"].set_index("candidate")
    for spec in GRID:
        s = stress_df.loc[spec.key]
        h = harsh_df.loc[spec.key]
        lines.append(
            f"| {spec.label} | {s['calmar']:.3f} | {s['maxdd_pct']:.2f} | {h['calmar']:.3f} | {h['maxdd_pct']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Readout",
            "",
            f"- Current mainline default: Return `{baseline['return_pct']:.2f}%`, Calmar `{baseline['calmar']:.3f}`, MaxDD `{baseline['maxdd_pct']:.2f}%`.",
            f"- Best W11-oriented candidate in this screen: `{best['label']}` with W11 entries `{int(best['w11_entry_count'])}`, quick14 `{best['w11_quick_reflat_14d_pct']:.1f}%`, HC quick14 `{best['highly_unstable_quick_reflat_14d_ratio_pct']:.1f}%`.",
            "- This screen asks whether the current one-tier high-churn gate should become a two-tier qualification system.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_MD), "summary_csv": str(SUMMARY_CSV)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
