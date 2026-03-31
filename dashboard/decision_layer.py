#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Decision/rebalance layer for the dashboard package."""

from __future__ import annotations

from typing import Dict


def classify_action(delta: float, tolerance: float) -> str:
    if abs(delta) <= tolerance:
        return "HOLD"
    if delta > 0:
        return "BUY"
    return "REDUCE"


def suggestion_text(snapshot: Dict) -> str:
    if snapshot["data_freshness"]["is_stale"]:
        return "Data looks stale. Refresh data first and do not trade from this snapshot."
    if snapshot["governance_alert_level"] in {"Review", "Escalate", "Incident"}:
        return "Lower expectations and keep path burden under review."
    if snapshot["portfolio_state"] == "Core-Only":
        return "Hold the core-dominant posture and wait for sleeves to reactivate."
    if snapshot["portfolio_state"] in {"Expansion-Carry", "Diversification-Carry", "Stacked Multi-Sleeve"}:
        return "Hold the active portfolio posture."
    return "Continue observation."


def build_decision(snapshot: Dict, config: Dict) -> Dict:
    account_equity = float(config["account_equity_usdt"])
    current_notional = float(config["current_notional_usdt"])
    tolerance = float(config.get("tolerance_usdt", 5.0))
    symbol = str(config.get("symbol", "BTCUSDT perpetual"))

    targets = {
        "core_target_notional": account_equity * float(snapshot["core_exposure"]),
        "sleeve1_target_notional": account_equity * float(snapshot["sleeve1_exposure"]),
        "sleeve2_target_notional": account_equity * float(snapshot["sleeve2_exposure"]),
        "total_target_notional": account_equity * float(snapshot["total_exposure"]),
    }
    delta = float(targets["total_target_notional"] - current_notional)
    action = classify_action(delta, tolerance)
    order_text = "No trade" if action == "HOLD" else f"{action} {abs(delta):.2f} USDT {symbol}"

    return {
        "account_equity_usdt": account_equity,
        "current_notional_usdt": current_notional,
        "symbol": symbol,
        "tolerance_usdt": tolerance,
        "targets": targets,
        "delta_usdt": delta,
        "action": action,
        "order_text": order_text,
        "suggestion": suggestion_text(snapshot),
    }
