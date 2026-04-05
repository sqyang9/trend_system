#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Layered freeze-point lineage audit for the combo promotion chain."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig_system_defect_research")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import pandas as pd
import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_asset_management_system_aligned import compute_metrics, current_research_optimal as riskoff_current_research_optimal, simulate_core
from v91_exposure_engine_e1_constant_mapping import extended_metrics

from system_defect_research.v171_volatility_proxy_system_upgrade import build_background, build_formal_bundle, path_bundle, scale_sleeve
from v121_coreonly_riskoff_sellside_ema_audit import build_indicators, build_instability_flags, build_target
from v123_formal_launch_and_layer2_weight_audit import ADOPTED_SPEC, SCENARIOS


OUT_DIR = Path("system_defect_research")
REPORT_MD = OUT_DIR / "LINEAGE_FREEZE_AUDIT.md"
SUMMARY_CSV = OUT_DIR / "lineage_freeze_split_summary.csv"
DETAIL_CSV = OUT_DIR / "lineage_freeze_candidate_detail.csv"
WINDOW_DELTA_CSV = OUT_DIR / "lineage_freeze_window_delta.csv"
REPORT_JSON = OUT_DIR / "lineage_freeze_audit.json"
PLOTS_HTML = OUT_DIR / "LINEAGE_FREEZE_AUDIT.html"

WINDOWS = [
    ("W01", pd.Timestamp("2019-12-16 04:00:00", tz="UTC"), pd.Timestamp("2020-06-16 00:00:00", tz="UTC")),
    ("W02", pd.Timestamp("2020-06-16 04:00:00", tz="UTC"), pd.Timestamp("2020-12-16 00:00:00", tz="UTC")),
    ("W03", pd.Timestamp("2020-12-16 04:00:00", tz="UTC"), pd.Timestamp("2021-06-16 00:00:00", tz="UTC")),
    ("W04", pd.Timestamp("2021-06-16 04:00:00", tz="UTC"), pd.Timestamp("2021-12-16 00:00:00", tz="UTC")),
    ("W05", pd.Timestamp("2021-12-16 04:00:00", tz="UTC"), pd.Timestamp("2022-06-16 00:00:00", tz="UTC")),
    ("W06", pd.Timestamp("2022-06-16 04:00:00", tz="UTC"), pd.Timestamp("2022-12-16 00:00:00", tz="UTC")),
    ("W07", pd.Timestamp("2022-12-16 04:00:00", tz="UTC"), pd.Timestamp("2023-06-16 00:00:00", tz="UTC")),
    ("W08", pd.Timestamp("2023-06-16 04:00:00", tz="UTC"), pd.Timestamp("2023-12-16 00:00:00", tz="UTC")),
    ("W09", pd.Timestamp("2023-12-16 04:00:00", tz="UTC"), pd.Timestamp("2024-06-16 00:00:00", tz="UTC")),
    ("W10", pd.Timestamp("2024-06-16 04:00:00", tz="UTC"), pd.Timestamp("2024-12-16 00:00:00", tz="UTC")),
    ("W11", pd.Timestamp("2024-12-16 04:00:00", tz="UTC"), pd.Timestamp("2025-06-16 00:00:00", tz="UTC")),
    ("W12", pd.Timestamp("2025-06-16 04:00:00", tz="UTC"), pd.Timestamp("2025-12-16 00:00:00", tz="UTC")),
    ("W13", pd.Timestamp("2025-12-16 04:00:00", tz="UTC"), pd.Timestamp("2026-03-30 20:00:00", tz="UTC")),
]

SPLITS = [
    ("fit_W01_W06_validate_W07_W13", "W01", "W06", "W07", "W13"),
    ("fit_W01_W09_validate_W10_W13", "W01", "W09", "W10", "W13"),
]


@dataclass(frozen=True)
class Stage:
    key: str
    label: str
    stage_order: int


STAGES = [
    Stage("close3_only", "Stage 1: EMA250 + close3", 1),
    Stage("hybrid_breakout4", "Stage 2: + HC strict breakout4", 2),
    Stage("hybrid_hv85", "Stage 3: + HV85 force HC", 3),
    Stage("hybrid_atrvt", "Stage 4: + ATRVT on sleeves", 4),
    Stage("combo", "Stage 5: + HV85 and ATRVT", 5),
]


def metrics_for_slice(equity: pd.Series, exposure: pd.Series) -> Dict[str, float]:
    if equity.empty or len(equity) < 2:
        return {
            "return_pct": 0.0,
            "calmar": 0.0,
            "maxdd_pct": 0.0,
            "worst3m_pct": 0.0,
            "worst6m_pct": 0.0,
            "recovery_days": 0.0,
            "avg_total_exposure_pct": 0.0,
        }
    metrics = extended_metrics({"combo_equity": equity, "combo_metrics": compute_metrics(equity, exposure)})
    path = path_bundle(equity)
    return {
        "return_pct": float(metrics["TotalReturn_pct"]),
        "calmar": float(metrics["Calmar"]),
        "maxdd_pct": float(metrics["MaxDD_pct"]),
        "worst3m_pct": float(path["worst_3m_cluster_return_pct"]),
        "worst6m_pct": float(path["worst_6m_cluster_return_pct"]),
        "recovery_days": float(path["recovery_days_from_maxdd"]),
        "avg_total_exposure_pct": float(exposure.mean() * 100.0),
    }


def slice_series(series: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    return series[(series.index >= start) & (series.index <= end)].astype(float)


def eval_combo(core_sim: dict, s1_eq: pd.Series, s1_w: pd.Series, s2_eq: pd.Series, s2_w: pd.Series, idx: pd.DatetimeIndex) -> tuple[pd.Series, pd.Series]:
    init_equity = float(s1_eq.iloc[0])
    core_equity = core_sim["equity"]["equity"].reindex(idx).ffill().bfill().astype(float)
    core_exposure = core_sim["equity"]["exposure"].reindex(idx).ffill().bfill().astype(float)
    s1_equity = s1_eq.reindex(idx).ffill().bfill().astype(float)
    s2_equity = s2_eq.reindex(idx).ffill().bfill().astype(float)
    s1_weight = s1_w.reindex(idx).ffill().fillna(0.0).astype(float)
    s2_weight = s2_w.reindex(idx).ffill().fillna(0.0).astype(float)
    combo_equity = (core_equity + (s1_equity - init_equity) + (s2_equity - init_equity)).astype(float)
    combo_exposure = (core_exposure + s1_weight + s2_weight).astype(float)
    return combo_equity, combo_exposure


def build_stage_series(df_5m: pd.DataFrame, df_4h: pd.DataFrame) -> Dict[str, tuple[pd.Series, pd.Series]]:
    scenario = next(s for s in SCENARIOS if s["name"] == "default")
    riskoff_params = riskoff_current_research_optimal(**scenario["riskoff_overrides"])
    background = build_background(df_4h)
    indicators = build_indicators(df_4h, riskoff_params, ADOPTED_SPEC["ema_len"], background=background)

    stable_env = pd.Series("stable", index=indicators.index)
    flip_env = build_instability_flags(
        df_5m,
        df_4h,
        riskoff_params,
        ema_len=ADOPTED_SPEC["ema_len"],
        threshold=ADOPTED_SPEC["threshold"],
        flips30_threshold=ADOPTED_SPEC["flips30_threshold"],
        flips60_threshold=ADOPTED_SPEC["flips60_threshold"],
        hv_force_threshold=None,
        background=background,
    )["instability_state"]
    hv_env = build_instability_flags(
        df_5m,
        df_4h,
        riskoff_params,
        ema_len=ADOPTED_SPEC["ema_len"],
        threshold=ADOPTED_SPEC["threshold"],
        flips30_threshold=ADOPTED_SPEC["flips30_threshold"],
        flips60_threshold=ADOPTED_SPEC["flips60_threshold"],
        hv_force_threshold=0.85,
        background=background,
    )["instability_state"]

    spec = dict(ADOPTED_SPEC)
    idx = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])["index"]
    formal_bundle = build_formal_bundle(df_5m, df_4h, scenario["formal_overrides"])
    atr_scale = background["atr_scale"].reindex(formal_bundle["index"]).ffill().fillna(1.0)
    s1_scaled_eq, s1_scaled_w = scale_sleeve(formal_bundle["s1_equity"], formal_bundle["s1_weight"], atr_scale)
    s2_scaled_eq, s2_scaled_w = scale_sleeve(formal_bundle["s2_equity"], formal_bundle["s2_weight"], atr_scale)

    def core_from_env(env: pd.Series) -> dict:
        target = build_target(indicators, spec, env)
        return simulate_core(df_5m, df_4h, target, riskoff_params, riskoff_params.entry_execution_mode)

    close3_core = core_from_env(stable_env)
    hybrid_core = core_from_env(flip_env)
    hv_core = core_from_env(hv_env)

    out: Dict[str, tuple[pd.Series, pd.Series]] = {}
    out["close3_only"] = eval_combo(close3_core, formal_bundle["s1_equity"], formal_bundle["s1_weight"], formal_bundle["s2_equity"], formal_bundle["s2_weight"], idx)
    out["hybrid_breakout4"] = eval_combo(hybrid_core, formal_bundle["s1_equity"], formal_bundle["s1_weight"], formal_bundle["s2_equity"], formal_bundle["s2_weight"], idx)
    out["hybrid_hv85"] = eval_combo(hv_core, formal_bundle["s1_equity"], formal_bundle["s1_weight"], formal_bundle["s2_equity"], formal_bundle["s2_weight"], idx)
    out["hybrid_atrvt"] = eval_combo(hybrid_core, s1_scaled_eq, s1_scaled_w, s2_scaled_eq, s2_scaled_w, idx)
    out["combo"] = eval_combo(hv_core, s1_scaled_eq, s1_scaled_w, s2_scaled_eq, s2_scaled_w, idx)
    return out


def pick_by_train(rows: List[dict]) -> dict:
    return sorted(rows, key=lambda r: (r["train_calmar"], r["train_maxdd_pct"], r["train_return_pct"]), reverse=True)[0]


def win_bounds(start_label: str, end_label: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    mapping = {name: (start, end) for name, start, end in WINDOWS}
    return mapping[start_label][0], mapping[end_label][1]


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    stage_map = build_stage_series(df_5m, df_4h)

    detail_rows: List[dict] = []
    summary_rows: List[dict] = []
    window_delta_rows: List[dict] = []

    for split_name, train_start, train_end, val_start, val_end in SPLITS:
        ts, te = win_bounds(train_start, train_end)
        vs, ve = win_bounds(val_start, val_end)

        split_rows: List[dict] = []
        for stage in STAGES:
            eq, ex = stage_map[stage.key]
            train_m = metrics_for_slice(slice_series(eq, ts, te), slice_series(ex, ts, te))
            val_m = metrics_for_slice(slice_series(eq, vs, ve), slice_series(ex, vs, ve))
            row = {
                "split": split_name,
                "candidate": stage.key,
                "label": stage.label,
                "stage_order": stage.stage_order,
                "train_windows": f"{train_start}-{train_end}",
                "validation_windows": f"{val_start}-{val_end}",
                "train_return_pct": train_m["return_pct"],
                "train_calmar": train_m["calmar"],
                "train_maxdd_pct": train_m["maxdd_pct"],
                "validation_return_pct": val_m["return_pct"],
                "validation_calmar": val_m["calmar"],
                "validation_maxdd_pct": val_m["maxdd_pct"],
                "validation_avg_total_exposure_pct": val_m["avg_total_exposure_pct"],
            }
            split_rows.append(row)
            detail_rows.append(row)

        picked = pick_by_train(split_rows)
        close3 = next(r for r in split_rows if r["candidate"] == "close3_only")
        hybrid = next(r for r in split_rows if r["candidate"] == "hybrid_breakout4")
        hv85 = next(r for r in split_rows if r["candidate"] == "hybrid_hv85")
        atrvt = next(r for r in split_rows if r["candidate"] == "hybrid_atrvt")
        combo = next(r for r in split_rows if r["candidate"] == "combo")
        summary_rows.append(
            {
                "split": split_name,
                "selected_candidate": picked["candidate"],
                "selected_label": picked["label"],
                "selected_validation_return_pct": picked["validation_return_pct"],
                "selected_validation_calmar": picked["validation_calmar"],
                "selected_validation_maxdd_pct": picked["validation_maxdd_pct"],
                "combo_validation_return_pct": combo["validation_return_pct"],
                "combo_validation_calmar": combo["validation_calmar"],
                "combo_validation_maxdd_pct": combo["validation_maxdd_pct"],
                "hybrid_validation_return_pct": hybrid["validation_return_pct"],
                "hybrid_validation_calmar": hybrid["validation_calmar"],
                "hybrid_validation_maxdd_pct": hybrid["validation_maxdd_pct"],
                "close3_validation_return_pct": close3["validation_return_pct"],
                "close3_validation_calmar": close3["validation_calmar"],
                "close3_validation_maxdd_pct": close3["validation_maxdd_pct"],
                "combo_d_calmar_vs_hybrid": combo["validation_calmar"] - hybrid["validation_calmar"],
                "combo_d_return_vs_hybrid_pp": combo["validation_return_pct"] - hybrid["validation_return_pct"],
                "hv85_d_calmar_vs_hybrid": hv85["validation_calmar"] - hybrid["validation_calmar"],
                "atrvt_d_calmar_vs_hybrid": atrvt["validation_calmar"] - hybrid["validation_calmar"],
            }
        )
        for prev_key, next_key, change_label in [
            ("close3_only", "hybrid_breakout4", "close3_to_hybrid"),
            ("hybrid_breakout4", "hybrid_hv85", "hybrid_to_hv85"),
            ("hybrid_breakout4", "hybrid_atrvt", "hybrid_to_atrvt"),
            ("hybrid_breakout4", "combo", "hybrid_to_combo"),
        ]:
            prev_row = next(r for r in split_rows if r["candidate"] == prev_key)
            next_row = next(r for r in split_rows if r["candidate"] == next_key)
            window_delta_rows.append(
                {
                    "split": split_name,
                    "change": change_label,
                    "validation_return_delta_pp": next_row["validation_return_pct"] - prev_row["validation_return_pct"],
                    "validation_calmar_delta": next_row["validation_calmar"] - prev_row["validation_calmar"],
                    "validation_maxdd_delta_pp": next_row["validation_maxdd_pct"] - prev_row["validation_maxdd_pct"],
                }
            )

    summary_df = pd.DataFrame(summary_rows)
    detail_df = pd.DataFrame(detail_rows)
    delta_df = pd.DataFrame(window_delta_rows)
    SUMMARY_CSV.write_text(summary_df.to_csv(index=False), encoding="utf-8")
    DETAIL_CSV.write_text(detail_df.to_csv(index=False), encoding="utf-8")
    WINDOW_DELTA_CSV.write_text(delta_df.to_csv(index=False), encoding="utf-8")

    fig = go.Figure()
    colors = {
        "close3_only": "#64748b",
        "hybrid_breakout4": "#0f172a",
        "hybrid_hv85": "#7c3aed",
        "hybrid_atrvt": "#0ea5e9",
        "combo": "#16a34a",
    }
    vs, ve = win_bounds("W10", "W13")
    for stage in STAGES:
        eq, _ = stage_map[stage.key]
        sub = slice_series(eq, vs, ve)
        rebased = 100.0 * sub / float(sub.iloc[0])
        fig.add_trace(go.Scatter(x=rebased.index, y=rebased.values, mode="lines", name=stage.label, line=dict(width=2.0, color=colors[stage.key])))
    fig.update_layout(template="plotly_white", hovermode="x unified", height=620, title="Lineage Freeze Audit: W10-W13 OOS")
    fig.update_yaxes(title_text="Rebased Equity")
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")

    split_a = summary_df[summary_df["split"] == "fit_W01_W06_validate_W07_W13"].iloc[0]
    split_b = summary_df[summary_df["split"] == "fit_W01_W09_validate_W10_W13"].iloc[0]
    lines = [
        "# Lineage Freeze Audit",
        "",
        "## Scope",
        "",
        "- Mainline not changed.",
        "- This audit decomposes the full promotion lineage into layered frozen checkpoints:",
        "  - `EMA250 + close3`",
        "  - `+ HC strict breakout4`",
        "  - `+ HV85 force`",
        "  - `+ ATRVT`",
        "  - final `combo = HV85 + ATRVT`",
        "- Goal: judge whether the later added layers still look sensible once validation is pushed into later windows.",
        "",
        "## Static Freeze Splits",
        "",
        "| Split | Selected By Train | Close3 Calmar | Hybrid Calmar | Combo Calmar | Combo dCalmar vs Hybrid |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| {split_a['split']} | {split_a['selected_label']} | {split_a['close3_validation_calmar']:.3f} | {split_a['hybrid_validation_calmar']:.3f} | {split_a['combo_validation_calmar']:.3f} | {split_a['combo_d_calmar_vs_hybrid']:+.3f} |",
        f"| {split_b['split']} | {split_b['selected_label']} | {split_b['close3_validation_calmar']:.3f} | {split_b['hybrid_validation_calmar']:.3f} | {split_b['combo_validation_calmar']:.3f} | {split_b['combo_d_calmar_vs_hybrid']:+.3f} |",
        "",
        "## Validation Deltas Vs Immediate Prior Stage",
        "",
        "| Split | Change | dReturn | dCalmar | dMaxDD |",
        "| --- | --- | --- | --- | --- |",
    ]
    for _, row in delta_df.iterrows():
        lines.append(
            f"| {row['split']} | {row['change']} | {row['validation_return_delta_pp']:+.2f}pp | "
            f"{row['validation_calmar_delta']:+.3f} | {row['validation_maxdd_delta_pp']:+.2f}pp |"
        )
    lines.extend(
        [
            "",
            "## Readout",
            "",
            f"- `W01-W06 -> W07-W13`: training still prefers `{split_a['selected_candidate']}`, while combo validates at `Calmar {split_a['combo_validation_calmar']:.3f}` versus hybrid `Calmar {split_a['hybrid_validation_calmar']:.3f}`.",
            f"- `W01-W09 -> W10-W13`: combo validates at `Calmar {split_b['combo_validation_calmar']:.3f}` versus hybrid `Calmar {split_b['hybrid_validation_calmar']:.3f}`.",
            "- This directly tests whether the late layers (`HV85`, `ATRVT`) add or subtract once the earlier lineage is frozen.",
            "",
            "## Verdict",
            "",
            "- If combo stays close to or above hybrid on the later windows, the late-stage promotion looks credible rather than purely in-sample.",
            "- If combo loses materially to hybrid or close3 after freezing, then the late-stage overlay additions should be treated as more fragile than the earlier lineage.",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    payload = {
        "summary_csv": str(SUMMARY_CSV),
        "detail_csv": str(DETAIL_CSV),
        "window_delta_csv": str(WINDOW_DELTA_CSV),
        "report_md": str(REPORT_MD),
        "plot_html": str(PLOTS_HTML),
    }
    REPORT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
