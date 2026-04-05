#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fixed-frequency live status runner for the adopted BTC mainline.

This script is intentionally operational, not research-oriented.
It reads the latest adopted mainline state, then converts that state
into target exposure, target notional, and a plain rebalance instruction.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


_stderr_fd = os.dup(2)
_devnull_fd = os.open(os.devnull, os.O_WRONLY)
os.dup2(_devnull_fd, 2)
try:
    from v132_live_operating_layer import ADOPTED_POSTURE, HARD_CAP, build_live_package  # noqa: E402
finally:
    os.dup2(_stderr_fd, 2)
    os.close(_stderr_fd)
    os.close(_devnull_fd)


STATUS_MD = ROOT / "MAINLINE_LIVE_STATUS.md"
STATUS_JSON = ROOT / "mainline_live_status.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the adopted mainline live status and rebalance instruction."
    )
    parser.add_argument(
        "--account-equity",
        type=float,
        required=True,
        help="Current account equity in USDT.",
    )
    parser.add_argument(
        "--current-notional",
        type=float,
        required=True,
        help="Current actual BTCUSDT perpetual notional in USDT.",
    )
    parser.add_argument(
        "--symbol",
        default="BTCUSDT perpetual",
        help="Execution symbol label used in the action line.",
    )
    parser.add_argument(
        "--tolerance-usdt",
        type=float,
        default=5.0,
        help="Below this absolute delta, action is HOLD.",
    )
    return parser.parse_args()


def layer_target_notionals(account_equity: float, latest: Dict) -> Dict[str, float]:
    return {
        "core_target_notional": account_equity * float(latest["core_exposure"]),
        "sleeve1_target_notional": account_equity * float(latest["sleeve1_exposure"]),
        "sleeve2_target_notional": account_equity * float(latest["sleeve2_exposure"]),
        "total_target_notional": account_equity * float(latest["total_exposure"]),
    }


def classify_action(delta: float, tolerance: float) -> str:
    if abs(delta) <= tolerance:
        return "HOLD"
    if delta > 0:
        return "BUY"
    return "REDUCE"


def suggestion_text(latest: Dict) -> str:
    if latest["governance_alert_level"] in {"Review", "Escalate", "Incident"}:
        return "降低预期，重点观察 path burden 和后续状态变化"
    if latest["portfolio_state"] == "Core-Only":
        return "持有核心主姿态，继续观察 sleeves 是否重新激活"
    if latest["portfolio_state"] in {"Expansion-Carry", "Diversification-Carry", "Stacked Multi-Sleeve"}:
        return "持有当前组合姿态，不需要额外主观干预"
    return "继续观察"


def render_md(args: argparse.Namespace, pkg: Dict, targets: Dict[str, float], delta: float, action: str) -> str:
    latest = pkg["latest"]
    state_code = str(pkg["state_series"].iloc[-1])
    sign = "+" if delta > 0 else ""
    lines = [
        "# Mainline Live Status",
        "",
        f"- Time: `{latest['timestamp']}`",
        f"- State: `{state_code}`",
        f"- Portfolio state: `{latest['portfolio_state']}`",
        f"- Risk-Off active: `{latest['riskoff_active']}`",
        "",
        "## Target Exposure",
        "",
        f"- Core = `{latest['core_exposure']:.2f}`",
        f"- Sleeve1 = `{latest['sleeve1_exposure']:.2f}`",
        f"- Sleeve2 = `{latest['sleeve2_exposure']:.2f}`",
        f"- Total = `{latest['total_exposure']:.2f}`",
        f"- Headroom to 3.0x cap = `{latest['cap_headroom']:.2f}x`",
        f"- ATR scale = `{latest['atr_scale']:.2f}x`",
        f"- ATR scales = `S1 {latest['atr_scale_s1']:.2f}x / S2 {latest['atr_scale_s2']:.2f}x`",
        f"- ATRVT contract = `{latest['atrvt_label']}`",
        f"- ATRVT detail = `S1 {latest['atrvt_s1_ref_days']}d / {latest['atrvt_s1_ref_stat']} / {latest['atrvt_s1_scale_min']:.2f}-{latest['atrvt_s1_scale_max']:.2f}; S2 {latest['atrvt_s2_ref_days']}d / {latest['atrvt_s2_ref_stat']} / {latest['atrvt_s2_scale_min']:.2f}-{latest['atrvt_s2_scale_max']:.2f}`",
        f"- S1 gate contract = `{latest['s1_gate_label']}`",
        f"- S1 gate latest = `candidate={latest['s1_gate_candidate']} / pass={latest['s1_gate_pass']} / reason={latest['s1_gate_reason']}`",
        f"- HV percentile = `{latest['hv_pct_180d'] * 100.0:.1f}`",
        f"- Core gate = `{latest['core_reentry_gate']}` / instability `{latest['core_instability_state']}` via `{latest['instability_source']}`",
        "",
        "## Target Notional",
        "",
        f"- Account equity = `{args.account_equity:.2f} USDT`",
        f"- Core target notional = `{targets['core_target_notional']:.2f} USDT`",
        f"- Sleeve1 target notional = `{targets['sleeve1_target_notional']:.2f} USDT`",
        f"- Sleeve2 target notional = `{targets['sleeve2_target_notional']:.2f} USDT`",
        f"- Total target notional = `{targets['total_target_notional']:.2f} USDT`",
        "",
        "## Rebalance Instruction",
        "",
        f"- Current actual notional = `{args.current_notional:.2f} USDT`",
        f"- Target notional = `{targets['total_target_notional']:.2f} USDT`",
        f"- Delta = `{sign}{delta:.2f} USDT`",
        f"- Action = `{action}`",
    ]
    if action == "HOLD":
        lines.append("- Suggested order = `No trade`")
    elif action == "BUY":
        lines.append(f"- Suggested order = `BUY {abs(delta):.2f} USDT {args.symbol}`")
    else:
        lines.append(f"- Suggested order = `REDUCE {abs(delta):.2f} USDT {args.symbol}`")
    lines.extend(
        [
            "",
            "## Operating Memo",
            "",
            f"- Suggestion: `{suggestion_text(latest)}`",
            f"- Governance alert: `{latest['governance_alert_level']}`",
            f"- Current drawdown: `{latest['current_drawdown_pct']:.2f}%`",
            f"- Days since equity high: `{latest['days_since_equity_high']:.1f}`",
            f"- Trailing 3m cluster loss: `{latest['trailing_3m_cluster_loss_pct']:.2f}%`",
            f"- Trailing 6m cluster loss: `{latest['trailing_6m_cluster_loss_pct']:.2f}%`",
            "",
            "## Scheduling",
            "",
            "- Recommended run frequency: `every 4h bar close`.",
            "- ATR sleeve scaling, HV-forced high-churn qualification, and weekly override are already captured by the same 4h refresh cycle.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    with contextlib.redirect_stdout(io.StringIO()):
        pkg = build_live_package()
    latest = pkg["latest"]
    targets = layer_target_notionals(args.account_equity, latest)
    delta = float(targets["total_target_notional"] - args.current_notional)
    action = classify_action(delta, args.tolerance_usdt)

    payload = {
        "timestamp": latest["timestamp"],
        "state": str(pkg["state_series"].iloc[-1]),
        "portfolio_state": latest["portfolio_state"],
        "riskoff_active": latest["riskoff_active"],
        "target_exposure": {
            "core": latest["core_exposure"],
            "sleeve1": latest["sleeve1_exposure"],
            "sleeve2": latest["sleeve2_exposure"],
            "total": latest["total_exposure"],
            "cap_headroom": latest["cap_headroom"],
            "hard_cap": HARD_CAP,
            "atr_scale": latest["atr_scale"],
            "atr_scale_s1": latest["atr_scale_s1"],
            "atr_scale_s2": latest["atr_scale_s2"],
            "hv_pct_180d": latest["hv_pct_180d"],
            "atrvt_label": latest["atrvt_label"],
            "atr_ref_days": latest["atr_ref_days"],
            "atr_ref_stat": latest["atr_ref_stat"],
            "atr_scale_min": latest["atr_scale_min"],
            "atr_scale_max": latest["atr_scale_max"],
            "atrvt_s1_label": latest["atrvt_s1_label"],
            "atrvt_s2_label": latest["atrvt_s2_label"],
            "atrvt_s1_ref_days": latest["atrvt_s1_ref_days"],
            "atrvt_s1_ref_stat": latest["atrvt_s1_ref_stat"],
            "atrvt_s1_scale_min": latest["atrvt_s1_scale_min"],
            "atrvt_s1_scale_max": latest["atrvt_s1_scale_max"],
            "atrvt_s2_ref_days": latest["atrvt_s2_ref_days"],
            "atrvt_s2_ref_stat": latest["atrvt_s2_ref_stat"],
            "atrvt_s2_scale_min": latest["atrvt_s2_scale_min"],
            "atrvt_s2_scale_max": latest["atrvt_s2_scale_max"],
            "s1_gate_label": latest["s1_gate_label"],
            "s1_gate_enabled": latest["s1_gate_enabled"],
            "s1_gate_family": latest["s1_gate_family"],
            "s1_gate_candidate": latest["s1_gate_candidate"],
            "s1_gate_pass": latest["s1_gate_pass"],
            "s1_gate_reason": latest["s1_gate_reason"],
            "s1_vp_hvn_escape_atr": latest["s1_vp_hvn_escape_atr"],
            "s1_vp_volume_ratio20": latest["s1_vp_volume_ratio20"],
        },
        "core_gate_context": {
            "reentry_gate": latest["core_reentry_gate"],
            "instability_state": latest["core_instability_state"],
            "instability_source": latest["instability_source"],
            "hv_forced_high_churn": latest["hv_forced_high_churn"],
        },
        "s1_gate_context": {
            "label": latest["s1_gate_label"],
            "enabled": latest["s1_gate_enabled"],
            "family": latest["s1_gate_family"],
            "candidate": latest["s1_gate_candidate"],
            "pass": latest["s1_gate_pass"],
            "reason": latest["s1_gate_reason"],
            "hvn_escape_atr": latest["s1_vp_hvn_escape_atr"],
            "volume_ratio20": latest["s1_vp_volume_ratio20"],
        },
        "account": {
            "equity_usdt": args.account_equity,
            "current_notional_usdt": args.current_notional,
            "symbol": args.symbol,
        },
        "target_notional": {
            "core_usdt": targets["core_target_notional"],
            "sleeve1_usdt": targets["sleeve1_target_notional"],
            "sleeve2_usdt": targets["sleeve2_target_notional"],
            "total_usdt": targets["total_target_notional"],
        },
        "rebalance": {
            "delta_usdt": delta,
            "action": action,
            "tolerance_usdt": args.tolerance_usdt,
            "order_text": (
                "No trade"
                if action == "HOLD"
                else f"{action} {abs(delta):.2f} USDT {args.symbol}"
            ),
        },
        "operating_memo": {
            "suggestion": suggestion_text(latest),
            "governance_alert_level": latest["governance_alert_level"],
            "current_drawdown_pct": latest["current_drawdown_pct"],
            "days_since_equity_high": latest["days_since_equity_high"],
            "trailing_3m_cluster_loss_pct": latest["trailing_3m_cluster_loss_pct"],
            "trailing_6m_cluster_loss_pct": latest["trailing_6m_cluster_loss_pct"],
            "preferred_onboarding": pkg["preferred_onboarding"],
        },
        "adopted_posture": ADOPTED_POSTURE,
    }

    STATUS_MD.write_text(render_md(args, pkg, targets, delta, action), encoding="utf-8")
    STATUS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
