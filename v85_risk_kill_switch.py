#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v85_risk_kill_switch.py
Runtime risk guard and kill-switch policies.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class RiskLimits:
    max_daily_loss_pct: float = 3.0
    max_drawdown_pct: float = 25.0
    max_position_notional: float = 10000.0
    max_consecutive_errors: int = 8


class RuntimeRiskManager:
    def __init__(self, limits: RiskLimits, initial_equity: float):
        self.limits = limits
        self.initial_equity = float(initial_equity)
        self.peak_equity = float(initial_equity)
        self.day_start_equity = float(initial_equity)
        self.current_day = datetime.now(timezone.utc).date()
        self.consecutive_errors = 0
        self.kill_switch_enabled = False
        self.kill_reason = ""

    def _trip(self, reason: str) -> tuple[bool, str]:
        self.kill_switch_enabled = True
        self.kill_reason = reason
        return True, reason

    def clear_kill_switch(self) -> None:
        self.kill_switch_enabled = False
        self.kill_reason = ""

    def on_runtime_error(self) -> tuple[bool, str]:
        self.consecutive_errors += 1
        if self.consecutive_errors >= self.limits.max_consecutive_errors:
            return self._trip(f"max_consecutive_errors_hit:{self.consecutive_errors}")
        return False, ""

    def on_runtime_ok(self) -> None:
        self.consecutive_errors = 0

    def on_position_notional(self, notional: float) -> tuple[bool, str]:
        if abs(notional) > self.limits.max_position_notional:
            return self._trip(
                f"position_notional_exceeded:{notional:.2f}>{self.limits.max_position_notional:.2f}"
            )
        return False, ""

    def on_equity(self, equity: float, ts: datetime | None = None) -> tuple[bool, str]:
        if ts is None:
            ts = datetime.now(timezone.utc)

        d = ts.date()
        if d != self.current_day:
            self.current_day = d
            self.day_start_equity = float(equity)

        self.peak_equity = max(self.peak_equity, float(equity))

        if self.day_start_equity > 0:
            daily_pnl_pct = (float(equity) / self.day_start_equity - 1.0) * 100.0
            if daily_pnl_pct <= -self.limits.max_daily_loss_pct:
                return self._trip(f"daily_loss_exceeded:{daily_pnl_pct:.2f}%")

        if self.peak_equity > 0:
            dd_pct = (float(equity) / self.peak_equity - 1.0) * 100.0
            if dd_pct <= -self.limits.max_drawdown_pct:
                return self._trip(f"drawdown_exceeded:{dd_pct:.2f}%")

        return False, ""
