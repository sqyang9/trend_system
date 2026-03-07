#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v85_live_smoke_test.py
Local rehearsal for the P0 live kernel components.
"""

from __future__ import annotations

from pathlib import Path

from v85_live_execution import OrderRequest, PaperExecutionAdapter
from v85_order_reconcile import apply_reconcile_actions, reconcile_state
from v85_risk_kill_switch import RiskLimits, RuntimeRiskManager
from v85_state_recovery import JSONStateStore


def main() -> int:
    state_path = Path("./data/live_state_smoke.json")
    if state_path.exists():
        state_path.unlink()

    store = JSONStateStore(state_path)
    adapter = PaperExecutionAdapter(init_cash_usdt=10000.0)

    assert adapter.ping(), "adapter ping failed"

    # 1) place and fill a long order
    order = adapter.place_order(
        OrderRequest(
            symbol="BTC/USDT:USDT",
            side="buy",
            order_type="limit",
            amount=0.01,
            price=100000.0,
            tag="smoke-long",
        )
    )
    store.append_event("order", {"id": order.order_id, "status": order.status})

    # 2) reconcile local empty state with exchange snapshots
    state = store.load()
    report = reconcile_state(
        state,
        adapter.fetch_positions(["BTC/USDT:USDT"]),
        adapter.fetch_open_orders("BTC/USDT:USDT"),
    )
    apply_reconcile_actions(store, report)

    # 3) risk checks should not trip under normal settings
    risk = RuntimeRiskManager(RiskLimits(), initial_equity=10000.0)
    tripped, reason = risk.on_equity(10050.0)
    assert not tripped, f"unexpected risk trip: {reason}"

    # 4) forced risk trip for kill-switch path
    tripped, reason = risk.on_position_notional(200000.0)
    assert tripped, "expected notional risk trip"
    store.set_kill_switch(True, reason)

    loaded = store.load()
    assert loaded["kill_switch"]["enabled"] is True, "kill switch not persisted"
    assert "BTC/USDT:USDT" in loaded["positions"], "position recovery missing"

    print("SMOKE_TEST_PASS")
    print(f"state_path={state_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
