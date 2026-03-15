#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit last-mile Risk-Off artifacts from the committed final-check result."""

from __future__ import annotations

import json
from pathlib import Path


SOURCE_JSON = Path("btc_riskoff_reentry_final_check.json")
REPORT_MD = Path("BTC_RISKOFF_REENTRY_LAST_MILE_REPORT.md")
REPORT_JSON = Path("btc_riskoff_reentry_last_mile.json")
REPORT_TXT = Path("btc_riskoff_reentry_last_mile_summary.txt")


def load_source() -> dict:
    return json.loads(SOURCE_JSON.read_text(encoding="utf-8"))


def write_markdown(report: dict) -> None:
    lines = [
        "# BTC Risk-Off Reentry Last Mile Report",
        "",
        "## Final Judgment",
        "",
        "- This round is the last-mile re-entry repair check, not a new exploration.",
        f"- Last-mile answer: {report['judgment']['final_check_answer']}",
        f"- Best repair candidate: {report['judgment']['best_candidate']}",
        f"- Promotion decision: {report['judgment']['promotion_decision']}",
        f"- Recommendation: {report['judgment']['recommendation']}",
        "",
        "## Candidate Comparison",
        "",
        "| Candidate | Strict OOS Win Ratio | Avg dReturn | Avg dSharpe | Avg dCalmar | Bull dReturn | Recovery dReturn | Sideways dReturn | Major Drawdown dMaxDD | Avg Flat Upside Drag |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, row in report["candidate_summary"].items():
        candidate = key.replace("Core+AddOnOverlay+", "")
        lines.append(
            f"| {candidate} | {row['strict_oos_win_ratio']:.2f} | {row['avg_delta_return_pct']:+.2f}pp | "
            f"{row['avg_delta_sharpe']:+.3f} | {row['avg_delta_calmar']:+.3f} | "
            f"{row['bull_delta_return_pct']:+.2f}pp | {row['recovery_delta_return_pct']:+.2f}pp | "
            f"{row['sideways_delta_return_pct']:+.2f}pp | {row['major_drawdown_dmaxdd_pct']:+.2f}pp | "
            f"{row['avg_flat_state_upside_drag']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Full-Sample References",
            "",
            "| Scheme | Return% | Sharpe | Calmar | MaxDD% | Exposure% |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for key in [
        "Core+AddOnOverlay",
        "Core+AddOnOverlay+RO_EMA220_FLAT",
        f"Core+AddOnOverlay+{report['judgment']['best_candidate']}",
    ]:
        metrics = report["full_sample"][key]["metrics"]
        lines.append(
            f"| {key} | {metrics['TotalReturn_pct']:.2f} | {metrics['Sharpe']:.3f} | "
            f"{metrics['Calmar']:.3f} | {metrics['MaxDD_pct']:.2f} | {metrics['Exposure_pct']:.1f} |"
        )
    lines.extend(["", "## Execution Stress And Causality", ""])
    for key, block in report["execution_stress"].items():
        if key == "Core+AddOnOverlay":
            continue
        delta = block["delta_vs_default_same_scheme"]
        candidate = key.replace("Core+AddOnOverlay+", "")
        lines.append(
            f"- {candidate}: stress delta Return {delta['Return_pct']:+.2f}pp, "
            f"Sharpe {delta['Sharpe']:+.3f}, Calmar {delta['Calmar']:+.3f}, "
            f"MaxDD improve {delta['MaxDD_improvement_pct']:+.2f}pp"
        )
    lines.extend(
        [
            f"- Default-mode causality violations: {report['causality_audit']['default_total_violations']}",
            f"- Stress-mode causality violations: {report['causality_audit']['stress_total_violations']}",
            "",
            "## Direct Answers",
            "",
            f"- {report['judgment']['answer_1']}",
            f"- {report['judgment']['answer_2']}",
            f"- {report['judgment']['answer_3']}",
            f"- {report['judgment']['answer_4']}",
            f"- {report['judgment']['answer_5']}",
            f"- {report['judgment']['answer_6']}",
            f"- {report['judgment']['answer_7']}",
        ]
    )
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")


def write_summary(report: dict) -> None:
    lines = [
        f"last_mile_answer={report['judgment']['final_check_answer']}",
        f"best_candidate={report['judgment']['best_candidate']}",
        f"promotion_decision={report['judgment']['promotion_decision']}",
        f"recommendation={report['judgment']['recommendation']}",
    ]
    REPORT_TXT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    report = load_source()
    report["scope"]["study_type"] = "reentry_last_mile"
    report["scope"]["note"] = "Last-mile re-entry repair only. No EMA expansion, no Bear Short, no AddOn change."
    REPORT_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown(report)
    write_summary(report)
    print(
        json.dumps(
            {
                "last_mile_answer": report["judgment"]["final_check_answer"],
                "best_candidate": report["judgment"]["best_candidate"],
                "promotion_decision": report["judgment"]["promotion_decision"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
