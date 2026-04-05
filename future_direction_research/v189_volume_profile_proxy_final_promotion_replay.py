#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final promotion replay for the implemented S1 volume-profile proxy challenger."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Dict, List

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from canonical_market_data import load_canonical_market_data
from v85_research_suite_v2 import ensure_datetime
from v90_asset_management_system_aligned import compute_metrics
from v91_exposure_engine_e1_constant_mapping import extended_metrics
from v123_formal_launch_and_layer2_weight_audit import ADOPTED_ATRVT_CONTRACT, SCENARIOS, base_bundle, simulate_weight_combo


OUT_DIR = Path("future_direction_research")
OUT_DIR.mkdir(exist_ok=True)
REPORT_MD = OUT_DIR / "VOLUME_PROFILE_PROXY_FINAL_PROMOTION_REPLAY.md"
SUMMARY_CSV = OUT_DIR / "volume_profile_proxy_final_promotion_summary.csv"
ANNUAL_CSV = OUT_DIR / "volume_profile_proxy_final_promotion_annual.csv"
WALKFORWARD_CSV = OUT_DIR / "volume_profile_proxy_final_promotion_walkforward.csv"
REPORT_JSON = OUT_DIR / "volume_profile_proxy_final_promotion_replay.json"

WINNER_ID = "vp_lb60_ea50_vr120"
WINNER_CFG = {"lookback": 60, "escape_atr": 0.50, "vol_ratio": 1.20}


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


def challenger_posture() -> Dict:
    posture = baseline_posture()
    posture.update(
        {
            "id": WINNER_ID,
            "s1_gate_enabled": True,
            "s1_gate_family": "volume_profile_proxy",
            "s1_vp_lookback": int(WINNER_CFG["lookback"]),
            "s1_vp_escape_atr": float(WINNER_CFG["escape_atr"]),
            "s1_vp_volume_ratio": float(WINNER_CFG["vol_ratio"]),
        }
    )
    return posture


def metric_delta(challenger: Dict, baseline: Dict) -> Dict:
    c = challenger["metrics"]
    b = baseline["metrics"]
    trace = challenger["s1_gate_trace"]
    cand = trace["s1_candidate"].fillna(False)
    passed = trace["s1_gate_pass"].fillna(False)
    candidate_count = int(cand.sum())
    pass_count = int((cand & passed).sum())
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


def write_report(summary: pd.DataFrame, annual: pd.DataFrame, wf: pd.DataFrame) -> None:
    lines = [
        "# Volume-Profile Proxy Final Promotion Replay",
        "",
        f"- Challenger: `{WINNER_ID}`.",
        "- This replay uses the implemented shared `S1 gate` contract, not the old manual research path.",
        "- Current locked mainline remains unchanged unless this replay clears promotion standard.",
        "",
        "## Scenario Readout",
        "",
        "| Scenario | Return% | Sharpe | Calmar | MaxDD% | dReturn | dSharpe | dCalmar | dMaxDD Improve | Cand | Pass | PassRate |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in summary.iterrows():
        lines.append(
            f"| {row['scenario']} | {row['return_pct']:.2f} | {row['sharpe']:.3f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
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
        lines.append(
            f"- Annual wins: Return {(annual['d_return_pct'] > 0).sum()}/{len(annual)}, "
            f"Sharpe {(annual['d_sharpe'] > 0).sum()}/{len(annual)}, "
            f"Calmar {(annual['d_calmar'] > 0).sum()}/{len(annual)}, "
            f"MaxDD {(annual['d_maxdd_improve_pct'] > 0).sum()}/{len(annual)}."
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
            "- Promotion standard for replacement:",
            "  - positive on default / stress / harsh",
            "  - annual starts mostly positive",
            "  - freeze-date OOS positive",
            "  - implemented replay aligned with earlier research",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    df_5m, df_4h = load_canonical_market_data()

    scenario_map = {s["name"]: s for s in SCENARIOS}
    base_spec = baseline_posture()
    chal_spec = challenger_posture()

    rows: List[Dict] = []
    results: Dict[str, Dict] = {}
    for scenario_name in ["default", "stress", "harsh_friction"]:
        baseline_bundle = base_bundle(df_5m, df_4h, scenario_map[scenario_name], atrvt_spec=base_spec, s1_gate_contract=base_spec)
        challenger_bundle = base_bundle(df_5m, df_4h, scenario_map[scenario_name], atrvt_spec=chal_spec, s1_gate_contract=chal_spec)
        baseline_sim = simulate_weight_combo(baseline_bundle, base_spec)
        challenger_sim = simulate_weight_combo(challenger_bundle, chal_spec)
        results[scenario_name] = {"baseline": baseline_sim, "challenger": challenger_sim}
        rows.append({"scenario": scenario_name} | metric_delta(challenger_sim, baseline_sim))

    summary = pd.DataFrame(rows)
    annual = annual_start_rows(results["default"]["baseline"], results["default"]["challenger"], [2020, 2021, 2022, 2023, 2024, 2025, 2026])
    wf = walkforward_rows(results["default"]["baseline"], results["default"]["challenger"])

    summary.to_csv(SUMMARY_CSV, index=False)
    annual.to_csv(ANNUAL_CSV, index=False)
    wf.to_csv(WALKFORWARD_CSV, index=False)
    write_report(summary, annual, wf)
    REPORT_JSON.write_text(
        json.dumps(
            {
                "challenger_id": WINNER_ID,
                "summary_rows": len(summary),
                "annual_rows": len(annual),
                "walkforward_rows": len(wf),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
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
