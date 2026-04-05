#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""System-level crash-defense screen via sleeve daily-loss breaker variants."""

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
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v95_range_rotation_mean_reversion_audit import make_range_rotation_params
from v96_range_rotation_mean_reversion_s3_audit import scenario_systems
from v121_coreonly_riskoff_sellside_ema_audit import build_indicators, build_instability_flags, build_target
from v123_formal_launch_and_layer2_weight_audit import ADOPTED_SPEC


OUT_DIR = Path("system_defect_research")
OUT_DIR.mkdir(parents=True, exist_ok=True)

REPORT_MD = OUT_DIR / "PORTFOLIO_CIRCUIT_BREAKER_SCREEN.md"
SUMMARY_CSV = OUT_DIR / "portfolio_circuit_breaker_summary.csv"
SUMMARY_JSON = OUT_DIR / "portfolio_circuit_breaker_summary.json"

W06_START = pd.Timestamp("2022-06-16 04:00:00", tz="UTC")
W06_END = pd.Timestamp("2022-12-16 00:00:00", tz="UTC")


@dataclass(frozen=True)
class BreakerSpec:
    key: str
    label: str
    formal_enable: bool
    range_enable: bool
    daily_loss_limit_pct: float
    cooldown_bars: int


GRID: List[BreakerSpec] = [
    BreakerSpec("baseline", "Baseline", False, False, 0.0, 0),
    BreakerSpec("s2_dll1.0_cd6", "S2-only DLL 1.0% / CD6", False, True, 1.0, 6),
    BreakerSpec("all_dll1.0_cd6", "All sleeves DLL 1.0% / CD6", True, True, 1.0, 6),
    BreakerSpec("all_dll1.0_cd9", "All sleeves DLL 1.0% / CD9", True, True, 1.0, 9),
]


def current_core_sim(df_5m: pd.DataFrame, df_4h: pd.DataFrame, riskoff_overrides: Dict) -> dict:
    riskoff_params = riskoff_current_research_optimal(**riskoff_overrides)
    indicators = build_indicators(df_4h, riskoff_params, ADOPTED_SPEC["ema_len"])
    instability = build_instability_flags(
        df_5m,
        df_4h,
        riskoff_params,
        ema_len=ADOPTED_SPEC["ema_len"],
        threshold=ADOPTED_SPEC["threshold"],
        flips30_threshold=ADOPTED_SPEC["flips30_threshold"],
        flips60_threshold=ADOPTED_SPEC["flips60_threshold"],
    )
    target = build_target(indicators, ADOPTED_SPEC, instability["instability_state"])
    return simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)


def combine_portfolio(formal_payload: Dict, core_sim: Dict) -> dict:
    const1x = formal_payload["systems"]["Core+ConstAddOn[1.00x]"]
    candidate_sleeve = formal_payload["candidate_sleeve"]
    idx = const1x["combo_equity"].index

    sleeve1_equity = const1x["sleeve"]["equity"].reindex(idx).ffill().bfill().astype(float)
    sleeve1_weight = const1x["sleeve"]["weight"].reindex(idx).fillna(0.0).astype(float)
    sleeve2_equity = candidate_sleeve["equity"].reindex(idx).ffill().bfill().astype(float)
    sleeve2_weight = candidate_sleeve["weight"].reindex(idx).fillna(0.0).astype(float)
    init_equity = float(sleeve1_equity.iloc[0])

    core_equity = core_sim["equity"]["equity"].reindex(idx).ffill().bfill().astype(float)
    core_exposure = core_sim["equity"]["exposure"].reindex(idx).ffill().bfill().fillna(1.0).astype(float)

    combo_equity = (core_equity + (sleeve1_equity - init_equity) + (sleeve2_equity - init_equity)).astype(float)
    combo_exposure = (core_exposure + sleeve1_weight + sleeve2_weight).astype(float)
    metrics = extended_metrics({"combo_equity": combo_equity, "combo_metrics": compute_metrics(combo_equity, combo_exposure)})
    return {
        "combo_equity": combo_equity,
        "combo_exposure": combo_exposure,
        "core_exposure": core_exposure,
        "s1_exposure": sleeve1_weight,
        "s2_exposure": sleeve2_weight,
        "metrics": metrics,
    }


def build_formal_payload(df_5m: pd.DataFrame, df_4h: pd.DataFrame, scenario: Dict, spec: BreakerSpec) -> Dict:
    formal_kwargs = dict(scenario["formal_overrides"])
    range_kwargs = dict(scenario["formal_overrides"])
    if spec.formal_enable:
        formal_kwargs.update(
            {
                "enable_daily_loss_limit": True,
                "daily_loss_limit_pct": spec.daily_loss_limit_pct,
                "cooldown_bars": spec.cooldown_bars,
            }
        )
    if spec.range_enable:
        range_kwargs.update(
            {
                "enable_daily_loss_limit": True,
                "daily_loss_limit_pct": spec.daily_loss_limit_pct,
                "cooldown_bars": spec.cooldown_bars,
            }
        )
    formal_params = formal_current_research_optimal(**formal_kwargs)
    range_params = make_range_rotation_params(**range_kwargs)
    return scenario_systems(formal_params, range_params, df_5m, df_4h)


def w06_metrics(bundle: dict) -> dict:
    mask = (bundle["combo_equity"].index >= W06_START) & (bundle["combo_equity"].index <= W06_END)
    equity = bundle["combo_equity"].loc[mask].astype(float)
    exposure = bundle["combo_exposure"].loc[mask].astype(float)
    s2_exposure = bundle["s2_exposure"].loc[mask].astype(float)
    if len(equity) < 2:
        return {
            "w06_return_pct": 0.0,
            "w06_maxdd_pct": 0.0,
            "w06_avg_total_exposure": 0.0,
            "w06_avg_s2_exposure": 0.0,
            "w06_dd_over_avg_exposure_pct": 0.0,
        }
    maxdd_pct = float((equity / equity.cummax() - 1.0).min() * 100.0)
    avg_exp = float(exposure.mean())
    return {
        "w06_return_pct": float(equity.iloc[-1] / equity.iloc[0] - 1.0) * 100.0,
        "w06_maxdd_pct": maxdd_pct,
        "w06_avg_total_exposure": avg_exp,
        "w06_avg_s2_exposure": float(s2_exposure.mean()),
        "w06_dd_over_avg_exposure_pct": float(maxdd_pct / avg_exp) if avg_exp > 1e-9 else 0.0,
    }


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    scenario = {
        "name": "default",
        "formal_overrides": {},
        "riskoff_overrides": {
            "entry_execution_mode": "next_bar_open",
            "intrabar_execution_model": "legacy_bar_extrema",
            "intrabar_path_mode": "midpoint",
        },
    }
    core_sim = current_core_sim(df_5m, df_4h, scenario["riskoff_overrides"])

    rows = []
    for spec in GRID:
        formal_payload = build_formal_payload(df_5m, df_4h, scenario, spec)
        combo = combine_portfolio(formal_payload, core_sim)
        row = {
            "candidate": spec.key,
            "label": spec.label,
            "daily_loss_limit_pct": spec.daily_loss_limit_pct,
            "cooldown_bars": spec.cooldown_bars,
            "formal_breaker": spec.formal_enable,
            "range_breaker": spec.range_enable,
            "return_pct": float(combo["metrics"]["TotalReturn_pct"]),
            "calmar": float(combo["metrics"]["Calmar"]),
            "maxdd_pct": float(combo["metrics"]["MaxDD_pct"]),
        }
        row.update(w06_metrics(combo))
        rows.append(row)

    summary_df = pd.DataFrame(rows)
    SUMMARY_CSV.write_text(summary_df.to_csv(index=False), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    baseline = summary_df[summary_df["candidate"] == "baseline"].iloc[0]
    best = summary_df.sort_values(
        ["w06_dd_over_avg_exposure_pct", "w06_maxdd_pct", "calmar", "return_pct"],
        ascending=[False, False, False, False],
    ).iloc[0]

    lines = [
        "# Portfolio Circuit Breaker Screen",
        "",
        "- Scope: system-level crash-defense screen via existing sleeve `daily_loss_limit + cooldown` engine hooks.",
        "- This is still independent research. Mainline not changed.",
        "- Goal: see whether W06-style stop penetration is better handled by sleeve breaker logic than by small ATR-stop tweaks.",
        "",
        "## Default Summary",
        "",
        "| Candidate | Return% | Calmar | MaxDD% | W06 Return% | W06 MaxDD% | W06 AvgExp | W06 AvgS2Exp | W06 DD/Exp |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for _, row in summary_df.sort_values(["calmar", "return_pct"], ascending=[False, False]).iterrows():
        lines.append(
            f"| {row['label']} | {row['return_pct']:.2f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
            f"{row['w06_return_pct']:.2f} | {row['w06_maxdd_pct']:.2f} | {row['w06_avg_total_exposure']:.2f} | "
            f"{row['w06_avg_s2_exposure']:.2f} | {row['w06_dd_over_avg_exposure_pct']:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Readout",
            "",
            f"- Baseline W06: MaxDD `{baseline['w06_maxdd_pct']:.2f}%`, AvgExp `{baseline['w06_avg_total_exposure']:.2f}`, DD/Exp `{baseline['w06_dd_over_avg_exposure_pct']:.1f}%`.",
            f"- Best W06 candidate in this screen: `{best['label']}` with MaxDD `{best['w06_maxdd_pct']:.2f}%`, DD/Exp `{best['w06_dd_over_avg_exposure_pct']:.1f}%`.",
            "- This first-pass screen is intentionally default-only and W06-centric; if one candidate shows real edge, then it is worth expanding to stress / harsh.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"report": str(REPORT_MD), "summary_csv": str(SUMMARY_CSV)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
