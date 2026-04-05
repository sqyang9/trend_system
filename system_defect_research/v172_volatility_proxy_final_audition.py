#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final audition-style audit for volatility-proxy system upgrades."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from universal_data_updater_5m import DataLoader5m
from v85_research_suite_v2 import ensure_datetime
from v90_asset_management_system_aligned import compute_metrics
from v91_exposure_engine_e1_constant_mapping import extended_metrics

from system_defect_research.v171_volatility_proxy_system_upgrade import (
    BACKGROUND_CSV,
    GRID,
    W06_END,
    W06_START,
    W11_END,
    W11_START,
    build_background,
    path_bundle,
    scenario_results,
)
from v123_formal_launch_and_layer2_weight_audit import SCENARIOS


OUT_DIR = Path("system_defect_research")
AUDIT_MD = OUT_DIR / "VOLATILITY_PROXY_FINAL_AUDITION.md"
SUMMARY_CSV = OUT_DIR / "volatility_proxy_final_audition_summary.csv"
SUMMARY_JSON = OUT_DIR / "volatility_proxy_final_audition.json"
WINDOWS_CSV = OUT_DIR / "volatility_proxy_final_audition_windows.csv"
CHURN_CSV = OUT_DIR / "volatility_proxy_final_audition_churn.csv"
ANNUAL_CSV = OUT_DIR / "volatility_proxy_final_audition_annual_starts.csv"
PLOTS_HTML = OUT_DIR / "VOLATILITY_PROXY_FINAL_AUDITION.html"

OFFICIAL_MAINLINE_RETURN = 2878.61
OFFICIAL_MAINLINE_CALMAR = 2.854
OFFICIAL_MAINLINE_MAXDD = -25.41

WINDOWS = [
    ("W06", W06_START, W06_END),
    ("W11", W11_START, W11_END),
    ("2024-12_to_2025-06", pd.Timestamp("2024-12-01", tz="UTC"), pd.Timestamp("2025-06-01", tz="UTC")),
    ("2025-06_to_2025-12", pd.Timestamp("2025-06-01", tz="UTC"), pd.Timestamp("2025-12-01", tz="UTC")),
]

ANNUAL_STARTS = [
    pd.Timestamp("2020-01-01", tz="UTC"),
    pd.Timestamp("2021-01-01", tz="UTC"),
    pd.Timestamp("2022-01-01", tz="UTC"),
    pd.Timestamp("2023-01-01", tz="UTC"),
    pd.Timestamp("2024-01-01", tz="UTC"),
    pd.Timestamp("2025-01-01", tz="UTC"),
    pd.Timestamp("2026-01-01", tz="UTC"),
]


@dataclass(frozen=True)
class AuditCandidate:
    key: str
    label: str
    color: str
    thesis: str


CANDIDATES = [
    AuditCandidate("baseline", "Current mainline replay", "#0f172a", "Reference"),
    AuditCandidate("p0_atrvt_all", "P0 only: ATR vol-targeting on S1+S2", "#0ea5e9", "Fix P0"),
    AuditCandidate("p1_hv90_coregate", "P1 only: HV90 forces HC gate", "#9333ea", "Fix P1"),
    AuditCandidate("combo_all_hv85", "Combo: S1+S2 ATR VT + HV85 HC gate", "#16a34a", "Fix P0+P1"),
]


def annual_start_metrics(equity: pd.Series, exposure: pd.Series) -> Dict[str, float]:
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


def summarize_churn(cycles: pd.DataFrame, candidate_key: str) -> dict:
    sub = cycles.copy()
    valid = sub["days_re_to_next_flat"].dropna()
    return {
        "candidate": candidate_key,
        "full_re_count": int(len(sub)),
        "median_days_re_to_next_flat": float(valid.median()) if not valid.empty else float("nan"),
        "quick_reflat_14d_ratio_pct": float(sub["quick_reflat_after_re_14d"].mean() * 100.0) if not sub.empty else float("nan"),
        "quick_reflat_30d_ratio_pct": float(sub["quick_reflat_after_re_30d"].mean() * 100.0) if not sub.empty else float("nan"),
        "high_churn_re_count": int((sub["instability_state"] == "highly_unstable").sum()),
        "high_churn_quick_reflat_14d_ratio_pct": float(
            sub.loc[sub["instability_state"] == "highly_unstable", "quick_reflat_after_re_14d"].mean() * 100.0
        )
        if (sub["instability_state"] == "highly_unstable").any()
        else float("nan"),
        "high_churn_quick_reflat_30d_ratio_pct": float(
            sub.loc[sub["instability_state"] == "highly_unstable", "quick_reflat_after_re_30d"].mean() * 100.0
        )
        if (sub["instability_state"] == "highly_unstable").any()
        else float("nan"),
    }


def build_window_rows(bundle: dict, cycles: pd.DataFrame, candidate_key: str, candidate_label: str) -> List[dict]:
    rows: List[dict] = []
    eq = bundle["combo_equity"]
    exp = bundle["combo_exposure"]
    for label, start, end in WINDOWS:
        mask = (eq.index >= start) & (eq.index <= end)
        sub_eq = eq.loc[mask]
        sub_exp = exp.loc[mask]
        sub_cycles = cycles[(cycles["re_time"] >= start) & (cycles["re_time"] <= end)].copy()
        if len(sub_eq) >= 2:
            maxdd_pct = float((sub_eq / sub_eq.cummax() - 1.0).min() * 100.0)
            ret_pct = float(sub_eq.iloc[-1] / sub_eq.iloc[0] - 1.0) * 100.0
            avg_exp = float(sub_exp.mean())
        else:
            maxdd_pct = 0.0
            ret_pct = 0.0
            avg_exp = 0.0
        rows.append(
            {
                "candidate": candidate_key,
                "label": candidate_label,
                "window": label,
                "return_pct": ret_pct,
                "maxdd_pct": maxdd_pct,
                "avg_total_exposure": avg_exp,
                "dd_over_avg_exposure_pct": float(maxdd_pct / avg_exp) if avg_exp > 1e-9 else 0.0,
                "entries": int(len(sub_cycles)),
                "quick14_pct": float(sub_cycles["quick_reflat_after_re_14d"].mean() * 100.0) if not sub_cycles.empty else 0.0,
                "quick30_pct": float(sub_cycles["quick_reflat_after_re_30d"].mean() * 100.0) if not sub_cycles.empty else 0.0,
            }
        )
    return rows


def build_annual_table(default_map: Dict[str, dict]) -> pd.DataFrame:
    rows = []
    for start in ANNUAL_STARTS:
        for candidate in CANDIDATES:
            system = default_map[candidate.key]["combo"]
            sub_eq = system["combo_equity"][system["combo_equity"].index >= start]
            sub_ex = system["combo_exposure"][system["combo_exposure"].index >= start]
            if sub_eq.empty:
                continue
            metrics = annual_start_metrics(sub_eq, sub_ex)
            rows.append({"start": start.date().isoformat(), "candidate": candidate.key, "label": candidate.label, **metrics})
    return pd.DataFrame(rows)


def write_plot(default_map: Dict[str, dict]) -> None:
    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.46, 0.28, 0.26],
        subplot_titles=("Equity Curves", "Underwater", "Total Exposure"),
    )
    for candidate in CANDIDATES:
        system = default_map[candidate.key]["combo"]
        eq = system["combo_equity"]
        uw = (eq / eq.cummax() - 1.0) * 100.0
        ex = system["combo_exposure"] * 100.0
        fig.add_trace(
            go.Scatter(x=eq.index, y=eq, mode="lines", name=candidate.label, line=dict(width=2.0, color=candidate.color)),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=uw.index, y=uw, mode="lines", name=f"{candidate.label} UW", line=dict(width=1.2, color=candidate.color), showlegend=False),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(x=ex.index, y=ex, mode="lines", name=f"{candidate.label} Exposure", line=dict(width=1.2, color=candidate.color), showlegend=False),
            row=3,
            col=1,
        )
    fig.update_layout(template="plotly_white", height=1120, hovermode="x unified", title="Volatility Proxy Final Audition")
    fig.update_yaxes(title_text="Equity", row=1, col=1)
    fig.update_yaxes(title_text="Underwater %", row=2, col=1)
    fig.update_yaxes(title_text="Exposure %", row=3, col=1)
    PLOTS_HTML.write_text(fig.to_html(full_html=True, include_plotlyjs=True), encoding="utf-8")


def choose_rows(summary_df: pd.DataFrame) -> dict:
    default_df = summary_df[summary_df["scenario"] == "default"]
    return {
        "baseline": default_df[default_df["candidate"] == "baseline"].iloc[0],
        "p0": default_df[default_df["candidate"] == "p0_atrvt_all"].iloc[0],
        "p1": default_df[default_df["candidate"] == "p1_hv90_coregate"].iloc[0],
        "combo": default_df[default_df["candidate"] == "combo_all_hv85"].iloc[0],
    }


def delta(df: pd.DataFrame, a: str, b: str) -> Dict[str, float]:
    ra = df[df["candidate"] == a].iloc[0]
    rb = df[df["candidate"] == b].iloc[0]
    return {
        "return_pct": float(ra["return_pct"] - rb["return_pct"]),
        "calmar": float(ra["calmar"] - rb["calmar"]),
        "maxdd_pct": float(ra["maxdd_pct"] - rb["maxdd_pct"]),
    }


def annual_scorecard(annual_df: pd.DataFrame, cand: str, ref: str) -> Dict[str, int]:
    merged = (
        annual_df[annual_df["candidate"] == cand].set_index("start").add_suffix("_cand").join(
            annual_df[annual_df["candidate"] == ref].set_index("start").add_suffix("_ref"),
            how="inner",
        )
    )
    if merged.empty:
        return {"calmar_better": 0, "maxdd_better": 0, "return_better": 0, "n": 0}
    return {
        "calmar_better": int((merged["calmar_cand"] > merged["calmar_ref"]).sum()),
        "maxdd_better": int((merged["maxdd_pct_cand"] > merged["maxdd_pct_ref"]).sum()),
        "return_better": int((merged["return_pct_cand"] > merged["return_pct_ref"]).sum()),
        "n": int(len(merged)),
    }


def write_report(summary_df: pd.DataFrame, churn_df: pd.DataFrame, windows_df: pd.DataFrame, annual_df: pd.DataFrame) -> None:
    default_df = summary_df[summary_df["scenario"] == "default"]
    stress_df = summary_df[summary_df["scenario"] == "stress"]
    harsh_df = summary_df[summary_df["scenario"] == "harsh_friction"]
    rows = choose_rows(summary_df)
    d_p0 = delta(default_df, "p0_atrvt_all", "baseline")
    d_p1 = delta(default_df, "p1_hv90_coregate", "baseline")
    d_combo = delta(default_df, "combo_all_hv85", "baseline")
    d_combo_stress = delta(stress_df, "combo_all_hv85", "baseline")
    d_combo_harsh = delta(harsh_df, "combo_all_hv85", "baseline")
    ann_vs_base = annual_scorecard(annual_df, "combo_all_hv85", "baseline")
    ann_p0_vs_base = annual_scorecard(annual_df, "p0_atrvt_all", "baseline")

    churn_map = churn_df.set_index("candidate")
    window_map = windows_df.set_index(["candidate", "window"])

    lines: List[str] = [
        "# Volatility Proxy Final Audition",
        "",
        "## Scope",
        "",
        "- Mainline not changed.",
        "- This audit upgrades the prior screen into a promotion-style readout for the volatility-proxy branch.",
        "- Candidate set is intentionally narrow:",
        "  - baseline replay of the current official mainline rules",
        "  - strongest P0-only fix: `ATR vol-targeting on S1+S2`",
        "  - strongest P1-only fix: `HV90 forces high-churn gate`",
        "  - strongest combined fix: `ATR vol-targeting on S1+S2 + HV85 forces high-churn gate`",
        "",
        "## Canonical Baseline",
        "",
        f"- Official mainline headline remains `Return {OFFICIAL_MAINLINE_RETURN:.2f}% / Calmar {OFFICIAL_MAINLINE_CALMAR:.3f} / MaxDD {OFFICIAL_MAINLINE_MAXDD:.2f}%` from `official_mainline/FORMAL_MAINLINE_LAUNCH_AUDIT.md`.",
        f"- Local replay baseline inside this audition engine is `Return {rows['baseline']['return_pct']:.2f}% / Calmar {rows['baseline']['calmar']:.3f} / MaxDD {rows['baseline']['maxdd_pct']:.2f}%`.",
        "- Promotion judgment below uses local deltas inside the same engine for apples-to-apples comparison.",
        "",
        "## Default",
        "",
        "| Candidate | Thesis | Return% | Calmar | MaxDD% | Worst3m | Worst6m | RecoveryDays | AvgTotalExp% |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for candidate in CANDIDATES:
        row = default_df[default_df["candidate"] == candidate.key].iloc[0]
        lines.append(
            f"| {candidate.label} | {candidate.thesis} | {row['return_pct']:.2f} | {row['calmar']:.3f} | {row['maxdd_pct']:.2f} | "
            f"{row['worst_3m_cluster_return_pct']:.2f} | {row['worst_6m_cluster_return_pct']:.2f} | {row['recovery_days_from_maxdd']:.1f} | {row['avg_total_exposure_pct']:.2f} |"
        )

    lines.extend(
        [
            "",
            "## Scenario Delta Vs Baseline Replay",
            "",
            "| Candidate | Default dReturn | Default dCalmar | Default dMaxDD | Stress dCalmar | Harsh dCalmar |",
            "| --- | --- | --- | --- | --- | --- |",
            f"| P0 only | {d_p0['return_pct']:+.2f}pp | {d_p0['calmar']:+.3f} | {d_p0['maxdd_pct']:+.2f}pp | "
            f"{delta(stress_df, 'p0_atrvt_all', 'baseline')['calmar']:+.3f} | {delta(harsh_df, 'p0_atrvt_all', 'baseline')['calmar']:+.3f} |",
            f"| P1 only | {d_p1['return_pct']:+.2f}pp | {d_p1['calmar']:+.3f} | {d_p1['maxdd_pct']:+.2f}pp | "
            f"{delta(stress_df, 'p1_hv90_coregate', 'baseline')['calmar']:+.3f} | {delta(harsh_df, 'p1_hv90_coregate', 'baseline')['calmar']:+.3f} |",
            f"| Combo | {d_combo['return_pct']:+.2f}pp | {d_combo['calmar']:+.3f} | {d_combo['maxdd_pct']:+.2f}pp | "
            f"{d_combo_stress['calmar']:+.3f} | {d_combo_harsh['calmar']:+.3f} |",
            "",
            "## W06 / W11",
            "",
            "| Candidate | W06 DD/Exp | W06 MaxDD% | W11 Entries | W11 Quick14 | W11 Quick30 | W11 AvgExp |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for candidate in CANDIDATES:
        w06 = window_map.loc[(candidate.key, "W06")]
        w11 = window_map.loc[(candidate.key, "W11")]
        lines.append(
            f"| {candidate.label} | {w06['dd_over_avg_exposure_pct']:.1f}% | {w06['maxdd_pct']:.2f} | {int(w11['entries'])} | "
            f"{w11['quick14_pct']:.1f}% | {w11['quick30_pct']:.1f}% | {w11['avg_total_exposure']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Churn Audit",
            "",
            "| Candidate | Full RE | Median Days RE->next FLAT | Quick14 | Quick30 | HC Quick14 | HC Quick30 |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for candidate in CANDIDATES:
        row = churn_map.loc[candidate.key]
        lines.append(
            f"| {candidate.label} | {int(row['full_re_count'])} | {row['median_days_re_to_next_flat']:.1f} | "
            f"{row['quick_reflat_14d_ratio_pct']:.1f}% | {row['quick_reflat_30d_ratio_pct']:.1f}% | "
            f"{row['high_churn_quick_reflat_14d_ratio_pct']:.1f}% | {row['high_churn_quick_reflat_30d_ratio_pct']:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Annual Starts",
            "",
            f"- `P0 only` vs baseline replay: Calmar better `{ann_p0_vs_base['calmar_better']}/{ann_p0_vs_base['n']}`, MaxDD better `{ann_p0_vs_base['maxdd_better']}/{ann_p0_vs_base['n']}`, Return better `{ann_p0_vs_base['return_better']}/{ann_p0_vs_base['n']}`.",
            f"- `Combo` vs baseline replay: Calmar better `{ann_vs_base['calmar_better']}/{ann_vs_base['n']}`, MaxDD better `{ann_vs_base['maxdd_better']}/{ann_vs_base['n']}`, Return better `{ann_vs_base['return_better']}/{ann_vs_base['n']}`.",
            "",
            "## Readout",
            "",
            f"- `P0 only` is the strongest economic fix: default `Return {rows['p0']['return_pct']:.2f}% / Calmar {rows['p0']['calmar']:.3f} / MaxDD {rows['p0']['maxdd_pct']:.2f}%`, and it improves W06 `DD/Exp` from {window_map.loc[('baseline', 'W06')]['dd_over_avg_exposure_pct']:.1f}% to {window_map.loc[('p0_atrvt_all', 'W06')]['dd_over_avg_exposure_pct']:.1f}%.",
            f"- `P1 only` is a real detector upgrade but still too weak standalone: W11 entries drop from {int(window_map.loc[('baseline', 'W11')]['entries'])} to {int(window_map.loc[('p1_hv90_coregate', 'W11')]['entries'])}, yet default return/calmar stay below baseline replay.",
            f"- `Combo` is the best dual-defect candidate: default `Return {rows['combo']['return_pct']:.2f}% / Calmar {rows['combo']['calmar']:.3f} / MaxDD {rows['combo']['maxdd_pct']:.2f}%`, W06 `DD/Exp {window_map.loc[('combo_all_hv85', 'W06')]['dd_over_avg_exposure_pct']:.1f}%`, W11 `entries {int(window_map.loc[('combo_all_hv85', 'W11')]['entries'])}, quick14 {window_map.loc[('combo_all_hv85', 'W11')]['quick14_pct']:.1f}%`.",
            f"- Promotion framing: if the goal is pure portfolio economics, `P0 only` should lead the next round; if the goal is to repair both P0 and P1 in one package, `Combo` is the better promotion candidate.",
            "",
            "## Verdict",
            "",
            "- `P0 only`: `GO_TO_AUDITION`.",
            "- `P1 only`: `NO_GO` as a standalone promotion candidate, but `GO` as background data reserve.",
            "- `Combo`: `GO_TO_AUDITION` as the best integrated system-defect candidate.",
        ]
    )
    AUDIT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    loader = DataLoader5m("./data")
    df_5m, df_4h = loader.load_data()
    df_5m = ensure_datetime(df_5m)
    df_4h = ensure_datetime(df_4h)

    background = build_background(df_4h)
    if not BACKGROUND_CSV.exists():
        background.reset_index().rename(columns={"index": "timestamp"}).to_csv(BACKGROUND_CSV, index=False)

    candidate_lookup = {cand.key: cand for cand in GRID}
    for required in [c.key for c in CANDIDATES]:
        if required not in candidate_lookup:
            raise KeyError(f"Missing candidate in GRID: {required}")

    scenario_maps: Dict[str, Dict[str, dict]] = {}
    summary_rows: List[dict] = []
    churn_rows: List[dict] = []
    window_rows: List[dict] = []
    for scenario in SCENARIOS:
        out = scenario_results(df_5m, df_4h, background, scenario)
        scenario_maps[scenario["name"]] = out
        for candidate in CANDIDATES:
            system = out[candidate.key]["combo"]
            summary_rows.append(
                {
                    "scenario": scenario["name"],
                    "candidate": candidate.key,
                    "label": candidate.label,
                    "thesis": candidate.thesis,
                    "return_pct": float(system["metrics"]["TotalReturn_pct"]),
                    "cagr_pct": float(system["metrics"]["CAGR_pct"]),
                    "sharpe": float(system["metrics"]["Sharpe"]),
                    "calmar": float(system["metrics"]["Calmar"]),
                    "maxdd_pct": float(system["metrics"]["MaxDD_pct"]),
                    "worst_3m_cluster_return_pct": float(system["path"]["worst_3m_cluster_return_pct"]),
                    "worst_6m_cluster_return_pct": float(system["path"]["worst_6m_cluster_return_pct"]),
                    "recovery_days_from_maxdd": float(system["path"]["recovery_days_from_maxdd"]),
                    "avg_total_exposure_pct": float(system["combo_exposure"].mean() * 100.0),
                    "avg_core_exposure_pct": float(system["core_exposure"].mean() * 100.0),
                    "avg_s1_exposure_pct": float(system["s1_exposure"].mean() * 100.0),
                    "avg_s2_exposure_pct": float(system["s2_exposure"].mean() * 100.0),
                }
            )
        if scenario["name"] == "default":
            for candidate in CANDIDATES:
                cycles = out[candidate.key]["cycles"]
                churn_rows.append({"label": candidate.label, **summarize_churn(cycles, candidate.key)})
                window_rows.extend(build_window_rows(out[candidate.key]["combo"], cycles, candidate.key, candidate.label))

    summary_df = pd.DataFrame(summary_rows)
    churn_df = pd.DataFrame(churn_rows)
    windows_df = pd.DataFrame(window_rows)
    annual_df = build_annual_table(scenario_maps["default"])

    SUMMARY_CSV.write_text(summary_df.to_csv(index=False), encoding="utf-8")
    CHURN_CSV.write_text(churn_df.to_csv(index=False), encoding="utf-8")
    WINDOWS_CSV.write_text(windows_df.to_csv(index=False), encoding="utf-8")
    ANNUAL_CSV.write_text(annual_df.to_csv(index=False), encoding="utf-8")
    SUMMARY_JSON.write_text(
        json.dumps(
            {
                "summary": summary_rows,
                "churn": churn_rows,
                "windows": window_rows,
                "annual_starts": annual_df.to_dict(orient="records"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    write_plot(scenario_maps["default"])
    write_report(summary_df, churn_df, windows_df, annual_df)
    print(
        json.dumps(
            {
                "report": str(AUDIT_MD),
                "summary_csv": str(SUMMARY_CSV),
                "churn_csv": str(CHURN_CSV),
                "windows_csv": str(WINDOWS_CSV),
                "annual_csv": str(ANNUAL_CSV),
                "plots_html": str(PLOTS_HTML),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
