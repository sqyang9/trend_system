#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v85_state_recovery.py
State persistence, restart recovery helpers, and event journaling.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


@dataclass
class StateDefaults:
    schema_version: int = 1


class JSONStateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def default_state() -> Dict[str, Any]:
        return {
            "schema_version": 1,
            "updated_at": JSONStateStore._now(),
            "kill_switch": {
                "enabled": False,
                "reason": "",
                "triggered_at": "",
            },
            "positions": {},  # symbol -> {contracts, side, entry_price, updated_at}
            "open_orders": {},  # order_id -> {symbol, side, amount, price, status, client_order_id, updated_at}
            "events": [],  # append-only rolling event log
        }

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            state = self.default_state()
            self.save(state)
            return state

        raw = self.path.read_text(encoding="utf-8")
        data = json.loads(raw)

        # forward compatibility for missing keys
        base = self.default_state()
        for key, val in base.items():
            if key not in data:
                data[key] = val

        return data

    def save(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = self._now()
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def append_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        state = self.load()
        state["events"].append(
            {
                "ts": self._now(),
                "type": event_type,
                "payload": payload,
            }
        )
        # keep recent 2000 events
        if len(state["events"]) > 2000:
            state["events"] = state["events"][-2000:]
        self.save(state)

    def set_kill_switch(self, enabled: bool, reason: str = "") -> None:
        state = self.load()
        state["kill_switch"] = {
            "enabled": bool(enabled),
            "reason": reason,
            "triggered_at": self._now() if enabled else "",
        }
        self.save(state)

    def upsert_position(self, symbol: str, contracts: float, side: str, entry_price: float) -> None:
        state = self.load()
        if abs(float(contracts)) < 1e-12:
            state["positions"].pop(symbol, None)
        else:
            state["positions"][symbol] = {
                "contracts": float(contracts),
                "side": side,
                "entry_price": float(entry_price),
                "updated_at": self._now(),
            }
        self.save(state)

    def upsert_open_order(self, order: Dict[str, Any]) -> None:
        state = self.load()
        oid = str(order.get("order_id") or order.get("id") or "")
        if not oid:
            return
        row = dict(order)
        row["updated_at"] = self._now()
        state["open_orders"][oid] = row
        self.save(state)

    def remove_open_order(self, order_id: str) -> None:
        state = self.load()
        state["open_orders"].pop(order_id, None)
        self.save(state)

    def startup_recovery_snapshot(self) -> Dict[str, Any]:
        """Return current persisted state for bootstrapping logic."""
        return self.load()
