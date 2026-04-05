#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fast strengthening audit plus implemented parity spot-check for S1 volume-profile proxy."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v123_formal_launch_and_layer2_weight_audit import ADOPTED_ATRVT_CONTRACT, SCENARIOS, base_bundle, simulate_weight_combo
from future_direction_research.v186_volume_profile_proxy_promotion_audit import (
    WINNER,
    WINNER_ID,
    annual_start_rows,
    build_s1_entries,
    metric_delta,
    rolling_hvn_features,
    simulate_volume_proxy,
    walkforward_rows,
)


OUT_DIR = Path("future_direction_research")
OUT_DIR.mkdir(exist_ok=True)
REPORT_MD = OUT_DIR / "VOLUME_PROFILE_PROXY_STRENGTHENING_FAST_AUDIT.md"
SUMMARY_CSV = OUT_DIR / "volume_profile_proxy_strengthening_fast_summary.csv"
ANNUAL_CSV = OUT_DIR / "volume_profile_proxy_strengthening_fast_annual.csv"
WALKFORWARD_CSV = OUT_DIR / "volume_profile_proxy_strengthening_fast_walkforward.csv"
REPORT_JSON = OUT_DIR / "volume_profile_proxy_strengthening_fast_audit.json"

FAST_GRID = [
    {"id": WINNER_ID, **WINNER},
    {"id": "vp_lb60_ea35_vr110", "lookback": 60, "escape_atr": 0.35, "vol_ratio": 1.10},
]


def baseline_posture() -> Dict:
    return {
        "id": "baseline_mainline",
        "core_weight": 1.00,
        "sleeve1_weight": 1.00,
        "sleeve2_weight": 1.00,
        "atr_vol_target_s1": True,
        "atr_vol_target_s2": True,
        "atrvt_s1_ref_days": ADOPTED_ATRVT_CONTRACT["atrvt_s1_spec"]["atr_ref_days"],
        "atrvt_s1_ref_stat": ADOPTED_ATRVT_CONTRACT["atrvt_s1_spec"]["atr_ref_stat"],
        "atrvt_s1_scale_min": ADOPTED_ATRVT_CONTRACT["atrvt_s1_spec"]["atr_scale_min"],
        "atrvt_s1_scale_max": ADOPTED_ATRVT_CONTRACT["atrvt_s1_spec"]["atr_scale_max"],
        "atrvt_s2_ref_days": ADOPTED_ATRVT_CONTRACT["atrvt_s2_spec"]["atr_ref_days"],
        "atrvt_s2_ref_stat": ADOPTED_ATRVT_CONTRACT["atrvt_s2_spec"]["atr_ref_stat"],
        "atrvt_s2_scale_min": ADOPTED_ATRVT_CONTRACT["atrvt_s2_spec"]["atr_scale_min"],
        "atrvt_s2_scale_max": ADOPTED_ATRVT_CONTRACT["atrvt_s2_spec"]["atr_scale_max"],
        "s1_gate_enabled": False,
        "s1_gate_family": "none",
    }


def implemented_posture(cfg: Dict) -> Dict:
    posture = baseline_posture()
    posture.update(
        {
            "id": cfg["id"],
            "s1_gate_enabled": True,
            "s1_gate_family": "volume_profile_proxy",
            "s1_vp_lookback": int(cfg["lookback"]),
            "s1_vp_escape_atr": float(cfg["escape_atr"]),
            "s1_vp_volume_ratio": float(cfg["vol_ratio"]),
        }
    )
    return posture


def write_report(summary: pd.DataFrame, annual: pd.DataFrame, wf: pd.DataFrame, parity: Dict, winner_id: str) -> None:
    lines = [
        "# Volume-Profile Proxy Strengthening Fast Audit",
        "",
        "- Scope: fast strengthening around the current winner plus an implemented-parity spot-check.",
        "- Boundary: current official mainline remains unchanged.",
        f"- Strengthened winner: `{winner_id}`.",
        "",
        "## Implemented Parity Spot-Check",
        "",
        f"- Manual research path winner `{WINNER_ID}` default:",
        f"  - `Return {parity['manual_return_pct']:.2f}% / Sharpe {parity['manual_sharpe']:.3f} / Calmar {parity['manual_calmar']:.3f} / MaxDD {parity['manual_maxdd_pct']:.2f}%`",
        f"- Shared-contract implemented replay for the same gate:",
        f"  - `Return {parity['impl_return_pct']:.2f}% / Sharpe {parity['impl_sharpe']:.3f} / Calmar {parity['impl_calmar']:.3f} / MaxDD {parity['impl_maxdd_pct']:.2f}%`",
        f"- Parity delta:",
        f"  - `dReturn {parity['d_return_pct']:+.2f}pp / dSharpe {parity['d_sharpe']:+.3f} / dCalmar {parity['d_calmar']:+.3f} / dMaxDDImprove {parity['d_maxdd_improve_pct']:+.2f}pp`",
        "",
        "## Scenario Readout",
        "",
        "| Scenario | Candidate | Return% | Sharpe | Calmar | MaxDD% | dReturn | dSharpe | dCalmar | dMaxDD Improve |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['scenario']} | {row['candidate']} | {row['return_pct']:.2f} | {row['sharpe']:.3f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
            f"{row['d_return_pct']:+.2f}pp | {row['d_sharpe']:+.3f} | {row['d_calmar']:+.3f} | {row['d_maxdd_improve_pct']:+.2f}pp |"
        )
    if not annual.empty:
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
    if not wf.empty:
        lines.extend(
            [
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
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            "- If the current winner still dominates after the parity spot-check, it remains the reserve front-runner.",
            "- If the looser neighbor wins on default but loses on stress/harsh or OOS, it should not replace the current reserve winner.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)
    scenario_map = {s["name"]: s for s in SCENARIOS}

    baseline = baseline_posture()
    default_bundle = base_bundle(df_5m, df_4h, scenario_map["default"], atrvt_spec=baseline, s1_gate_contract=baseline)
    default_baseline = simulate_weight_combo(default_bundle, baseline)

    summary_rows: List[Dict] = []
    cache: Dict[tuple[str, str], Dict] = {}

    for scenario_name in ["default", "stress", "harsh_friction"]:
        bundle = base_bundle(df_5m, df_4h, scenario_map[scenario_name], atrvt_spec=baseline, s1_gate_contract=baseline)
        baseline_sim = simulate_weight_combo(bundle, baseline)
        entries, commission_pct = build_s1_entries(df_5m, df_4h, scenario_map[scenario_name])
        for cfg in FAST_GRID:
            features = rolling_hvn_features(df_4h, int(cfg["lookback"]))
            challenger = simulate_volume_proxy(df_4h, bundle, entries, commission_pct, features, cfg)
            cache[(scenario_name, cfg["id"])] = challenger
            summary_rows.append({"scenario": scenario_name, "candidate": cfg["id"]} | metric_delta(challenger, baseline_sim))

    summary = pd.DataFrame(summary_rows).sort_values(["scenario", "calmar", "return_pct"], ascending=[True, False, False]).reset_index(drop=True)
    default_only = summary[summary["scenario"] == "default"].sort_values(["calmar", "return_pct"], ascending=[False, False]).reset_index(drop=True)
    winner_id = str(default_only.iloc[0]["candidate"])
    winner_default = cache[("default", winner_id)]

    impl_posture = implemented_posture(next(cfg for cfg in FAST_GRID if cfg["id"] == WINNER_ID))
    impl_bundle = base_bundle(df_5m, df_4h, scenario_map["default"], atrvt_spec=impl_posture, s1_gate_contract=impl_posture)
    impl_sim = simulate_weight_combo(impl_bundle, impl_posture)
    parity = {
        "manual_return_pct": float(cache[("default", WINNER_ID)]["metrics"]["TotalReturn_pct"]),
        "manual_sharpe": float(cache[("default", WINNER_ID)]["metrics"]["Sharpe"]),
        "manual_calmar": float(cache[("default", WINNER_ID)]["metrics"]["Calmar"]),
        "manual_maxdd_pct": float(cache[("default", WINNER_ID)]["metrics"]["MaxDD_pct"]),
        "impl_return_pct": float(impl_sim["metrics"]["TotalReturn_pct"]),
        "impl_sharpe": float(impl_sim["metrics"]["Sharpe"]),
        "impl_calmar": float(impl_sim["metrics"]["Calmar"]),
        "impl_maxdd_pct": float(impl_sim["metrics"]["MaxDD_pct"]),
        "d_return_pct": float(impl_sim["metrics"]["TotalReturn_pct"] - cache[("default", WINNER_ID)]["metrics"]["TotalReturn_pct"]),
        "d_sharpe": float(impl_sim["metrics"]["Sharpe"] - cache[("default", WINNER_ID)]["metrics"]["Sharpe"]),
        "d_calmar": float(impl_sim["metrics"]["Calmar"] - cache[("default", WINNER_ID)]["metrics"]["Calmar"]),
        "d_maxdd_improve_pct": float(abs(cache[("default", WINNER_ID)]["metrics"]["MaxDD_pct"]) - abs(impl_sim["metrics"]["MaxDD_pct"])),
    }

    annual = annual_start_rows(default_baseline, winner_default, [2020, 2021, 2022, 2023, 2024, 2025, 2026])
    wf = walkforward_rows(default_baseline, winner_default)

    summary.to_csv(SUMMARY_CSV, index=False)
    annual.to_csv(ANNUAL_CSV, index=False)
    wf.to_csv(WALKFORWARD_CSV, index=False)
    write_report(summary, annual, wf, parity, winner_id)

    REPORT_JSON.write_text(
        json.dumps(
            {
                "winner_id": winner_id,
                "parity": parity,
                "fast_grid": FAST_GRID,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "winner_id": winner_id,
                "report_md": str(REPORT_MD),
                "summary_csv": str(SUMMARY_CSV),
                "annual_csv": str(ANNUAL_CSV),
                "walkforward_csv": str(WALKFORWARD_CSV),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
