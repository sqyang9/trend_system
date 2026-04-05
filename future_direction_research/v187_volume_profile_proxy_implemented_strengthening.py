#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Implemented-form strengthening and audit for the S1 volume-profile proxy gate."""

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
from v90_asset_management_system_aligned import compute_metrics
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v123_formal_launch_and_layer2_weight_audit import ADOPTED_ATRVT_CONTRACT, SCENARIOS, base_bundle, simulate_weight_combo


OUT_DIR = Path("future_direction_research")
OUT_DIR.mkdir(exist_ok=True)
REPORT_MD = OUT_DIR / "VOLUME_PROFILE_PROXY_IMPLEMENTED_STRENGTHENING.md"
SUMMARY_CSV = OUT_DIR / "volume_profile_proxy_implemented_strengthening_summary.csv"
ANNUAL_CSV = OUT_DIR / "volume_profile_proxy_implemented_strengthening_annual.csv"
WALKFORWARD_CSV = OUT_DIR / "volume_profile_proxy_implemented_strengthening_walkforward.csv"
REPORT_JSON = OUT_DIR / "volume_profile_proxy_implemented_strengthening.json"


PARAM_GRID = [
    {"lookback": 60, "escape_atr": 0.50, "vol_ratio": 1.20},
    {"lookback": 60, "escape_atr": 0.35, "vol_ratio": 1.10},
]


def candidate_id(cfg: Dict) -> str:
    return f"vp_lb{cfg['lookback']}_ea{int(round(cfg['escape_atr'] * 100)):02d}_vr{int(round(cfg['vol_ratio'] * 100)):03d}"


def posture_with_gate(cfg: Dict | None = None) -> Dict:
    posture = {
        "id": "core1.00_s11.00_s21.00_atrvt",
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
    if cfg is None:
        posture["id"] = "baseline_mainline"
        return posture
    posture.update(
        {
            "id": candidate_id(cfg),
            "s1_gate_enabled": True,
            "s1_gate_family": "volume_profile_proxy",
            "s1_vp_lookback": int(cfg["lookback"]),
            "s1_vp_escape_atr": float(cfg["escape_atr"]),
            "s1_vp_volume_ratio": float(cfg["vol_ratio"]),
        }
    )
    return posture


def metric_delta(challenger: Dict, baseline: Dict) -> Dict:
    c = challenger["metrics"]
    b = baseline["metrics"]
    trace = challenger["s1_gate_trace"]
    candidate_count = int(trace["s1_candidate"].fillna(False).sum())
    pass_count = int((trace["s1_candidate"].fillna(False) & trace["s1_gate_pass"].fillna(False)).sum())
    return {
        "return_pct": float(c["TotalReturn_pct"]),
        "sharpe": float(c["Sharpe"]),
        "calmar": float(c["Calmar"]),
        "maxdd_pct": float(c["MaxDD_pct"]),
        "d_return_pct": float(c["TotalReturn_pct"] - b["TotalReturn_pct"]),
        "d_sharpe": float(c["Sharpe"] - b["Sharpe"]),
        "d_calmar": float(c["Calmar"] - b["Calmar"]),
        "d_maxdd_improve_pct": float(abs(b["MaxDD_pct"]) - abs(c["MaxDD_pct"])),
        "s1_candidate_count": candidate_count,
        "s1_pass_count": pass_count,
        "s1_pass_rate_pct": float(100.0 * pass_count / candidate_count) if candidate_count > 0 else 0.0,
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
                "d_return_pct": float(c["TotalReturn_pct"] - b["TotalReturn_pct"]),
                "d_sharpe": float(c["Sharpe"] - b["Sharpe"]),
                "d_calmar": float(c["Calmar"] - b["Calmar"]),
                "d_maxdd_improve_pct": float(abs(b["MaxDD_pct"]) - abs(c["MaxDD_pct"])),
            }
        )
    return pd.DataFrame(rows)


def write_report(summary: pd.DataFrame, annual: pd.DataFrame, wf: pd.DataFrame, winner_id: str) -> None:
    lines = [
        "# Volume-Profile Proxy Implemented Strengthening",
        "",
        "- Scope: re-run the S1 volume-profile reserve line through the implemented shared `S1 gate` contract.",
        "- Boundary: current official mainline remains unchanged.",
        f"- Strengthened winner: `{winner_id}`.",
        "",
        "## Scenario Readout",
        "",
        "| Scenario | Candidate | Return% | Sharpe | Calmar | MaxDD% | dReturn | dSharpe | dCalmar | dMaxDD Improve | Cand | Pass | PassRate |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['scenario']} | {row['candidate']} | {row['return_pct']:.2f} | {row['sharpe']:.3f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
            f"{row['d_return_pct']:+.2f}pp | {row['d_sharpe']:+.3f} | {row['d_calmar']:+.3f} | {row['d_maxdd_improve_pct']:+.2f}pp | "
            f"{int(row['s1_candidate_count'])} | {int(row['s1_pass_count'])} | {row['s1_pass_rate_pct']:.1f}% |"
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
            "- This report is used to decide whether the current reserve winner still holds after the shared implementation pass.",
            "- A candidate is strengthen-worthy only if it stays positive on default, stress, harsh, and keeps freeze-date OOS positive.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    scenario_map = {s["name"]: s for s in SCENARIOS}
    baseline_posture = posture_with_gate(None)

    default_baseline_bundle = base_bundle(df_5m, df_4h, scenario_map["default"], atrvt_spec=baseline_posture, s1_gate_contract=baseline_posture)
    default_baseline = simulate_weight_combo(default_baseline_bundle, baseline_posture)

    screen_rows: List[Dict] = []
    top_candidates: List[str] = []
    cache: Dict[tuple[str, str], Dict] = {}

    for cfg in PARAM_GRID:
        posture = posture_with_gate(cfg)
        bundle = base_bundle(df_5m, df_4h, scenario_map["default"], atrvt_spec=posture, s1_gate_contract=posture)
        sim = simulate_weight_combo(bundle, posture)
        cache[("default", posture["id"])] = sim
        row = {"scenario": "default", "candidate": posture["id"]} | metric_delta(sim, default_baseline)
        screen_rows.append(row)

    default_df = pd.DataFrame(screen_rows).sort_values(["calmar", "return_pct"], ascending=[False, False]).reset_index(drop=True)
    top_candidates = default_df.head(len(PARAM_GRID))["candidate"].tolist()
    winner_id = top_candidates[0]

    audited_rows = screen_rows.copy()
    scenario_names = ["stress", "harsh_friction"]
    for scenario_name in scenario_names:
        baseline_bundle = base_bundle(df_5m, df_4h, scenario_map[scenario_name], atrvt_spec=baseline_posture, s1_gate_contract=baseline_posture)
        baseline_sim = simulate_weight_combo(baseline_bundle, baseline_posture)
        for cfg in PARAM_GRID:
            cid = candidate_id(cfg)
            if cid not in top_candidates:
                continue
            posture = posture_with_gate(cfg)
            bundle = base_bundle(df_5m, df_4h, scenario_map[scenario_name], atrvt_spec=posture, s1_gate_contract=posture)
            sim = simulate_weight_combo(bundle, posture)
            cache[(scenario_name, cid)] = sim
            audited_rows.append({"scenario": scenario_name, "candidate": cid} | metric_delta(sim, baseline_sim))

    winner_cfg = next(cfg for cfg in PARAM_GRID if candidate_id(cfg) == winner_id)
    winner_posture = posture_with_gate(winner_cfg)
    annual = annual_start_rows(default_baseline, cache[("default", winner_id)], [2020, 2021, 2022, 2023, 2024, 2025, 2026])
    wf = walkforward_rows(default_baseline, cache[("default", winner_id)])

    summary = pd.DataFrame(audited_rows).sort_values(["scenario", "calmar", "return_pct"], ascending=[True, False, False]).reset_index(drop=True)
    summary.to_csv(SUMMARY_CSV, index=False)
    annual.to_csv(ANNUAL_CSV, index=False)
    wf.to_csv(WALKFORWARD_CSV, index=False)
    write_report(summary, annual, wf, winner_id)

    REPORT_JSON.write_text(
        json.dumps(
            {
                "winner_id": winner_id,
                "winner_posture": winner_posture,
                "top_candidates_default": top_candidates,
                "summary_rows": len(summary),
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
