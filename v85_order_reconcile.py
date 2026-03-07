#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v85_order_reconcile.py
Reconciliation between local persisted state and exchange snapshots.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from v85_live_execution import PositionSnapshot


@dataclass
class ReconcileAction:
    action: str
    detail: Dict[str, Any]


@dataclass
class ReconcileReport:
    actions: List[ReconcileAction]

    @property
    def has_actions(self) -> bool:
        return len(self.actions) > 0


def _exchange_position_map(positions: List[PositionSnapshot]) -> Dict[str, PositionSnapshot]:
    return {p.symbol: p for p in positions}


def reconcile_state(
    local_state: Dict[str, Any],
    exchange_positions: List[PositionSnapshot],
    exchange_open_orders: List[Dict[str, Any]],
    *,
    qty_tolerance: float = 1e-8,
) -> ReconcileReport:
    actions: List[ReconcileAction] = []

    local_pos = local_state.get("positions", {})
    local_orders = local_state.get("open_orders", {})

    ex_pos_map = _exchange_position_map(exchange_positions)
    ex_order_map = {str(o.get("id", "")): o for o in exchange_open_orders if o.get("id")}

    # 1) position reconciliation
    all_symbols = set(local_pos.keys()) | set(ex_pos_map.keys())
    for symbol in sorted(all_symbols):
        lp = local_pos.get(symbol)
        ep = ex_pos_map.get(symbol)

        lqty = float(lp.get("contracts", 0.0)) if lp else 0.0
        eqty = float(ep.contracts) if ep else 0.0

        if abs(lqty - eqty) > qty_tolerance:
            actions.append(
                ReconcileAction(
                    action="sync_position",
                    detail={
                        "symbol": symbol,
                        "local_contracts": lqty,
                        "exchange_contracts": eqty,
                        "exchange_side": ep.side if ep else "flat",
                        "exchange_entry_price": ep.entry_price if ep else 0.0,
                    },
                )
            )

    # 2) open order reconciliation (id-based)
    local_order_ids = set(local_orders.keys())
    ex_order_ids = set(ex_order_map.keys())

    for oid in sorted(local_order_ids - ex_order_ids):
        actions.append(
            ReconcileAction(
                action="close_local_order",
                detail={"order_id": oid},
            )
        )

    for oid in sorted(ex_order_ids - local_order_ids):
        actions.append(
            ReconcileAction(
                action="add_local_order",
                detail={"order_id": oid, "exchange_order": ex_order_map[oid]},
            )
        )

    return ReconcileReport(actions=actions)


def apply_reconcile_actions(state_store, report: ReconcileReport) -> None:
    for a in report.actions:
        if a.action == "sync_position":
            d = a.detail
            if abs(float(d["exchange_contracts"])) < 1e-12:
                state_store.upsert_position(d["symbol"], 0.0, "flat", 0.0)
            else:
                state_store.upsert_position(
                    d["symbol"],
                    float(d["exchange_contracts"]),
                    str(d["exchange_side"]),
                    float(d["exchange_entry_price"]),
                )
            state_store.append_event("reconcile_sync_position", d)

        elif a.action == "close_local_order":
            oid = str(a.detail["order_id"])
            state_store.remove_open_order(oid)
            state_store.append_event("reconcile_close_local_order", {"order_id": oid})

        elif a.action == "add_local_order":
            row = dict(a.detail["exchange_order"])
            row["order_id"] = str(row.get("id", ""))
            state_store.upsert_open_order(row)
            state_store.append_event("reconcile_add_local_order", {"order_id": row["order_id"]})
