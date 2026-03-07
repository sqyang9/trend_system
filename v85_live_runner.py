#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v85_live_runner.py
P1 live runner:
- startup recovery
- exchange/state reconciliation
- runtime risk kill-switch
- optional strategy-target execution
- optional test order pipeline
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from v85_intrabar_backtest import V85Params
from v85_live_execution import (
    CCXTOKXExecutionAdapter,
    OrderRequest,
    PaperExecutionAdapter,
)
from v85_live_strategy import StrategyTarget, compute_strategy_target
from v85_order_reconcile import apply_reconcile_actions, reconcile_state
from v85_risk_kill_switch import RiskLimits, RuntimeRiskManager
from v85_state_recovery import JSONStateStore


def build_adapter(args):
    if args.paper:
        return PaperExecutionAdapter(init_cash_usdt=args.paper_cash)

    api_key = os.getenv("OKX_API_KEY", "")
    secret = os.getenv("OKX_API_SECRET", "")
    password = os.getenv("OKX_API_PASSWORD", "")
    if not (api_key and secret and password):
        raise RuntimeError("Missing OKX credentials in env: OKX_API_KEY / OKX_API_SECRET / OKX_API_PASSWORD")

    return CCXTOKXExecutionAdapter(
        api_key=api_key,
        secret=secret,
        password=password,
        testnet=args.testnet,
        dry_run=args.dry_run,
    )


def build_strategy_params(args) -> V85Params:
    return V85Params(
        position_pct=args.position_pct,
        commission_pct=args.commission_pct,
        initial_stop_atr=args.initial_stop_atr,
        trail_start_atr=args.trail_start_atr,
        trail_offset_atr=args.trail_offset_atr,
        tp1_atr=args.tp1_atr,
        tp2_atr=args.tp2_atr,
        enable_partial_tp=(not args.disable_partial_tp),
        min_long_score=args.min_long_score,
        min_short_score=args.min_short_score,
        adx_trend_level=args.adx_trend_level,
        enable_short=args.allow_short,
    )


def sync_positions_to_state(store: JSONStateStore, positions):
    current = store.load()
    local_symbols = list(current.get("positions", {}).keys())
    for sym in local_symbols:
        store.upsert_position(sym, 0.0, "flat", 0.0)

    for p in positions:
        store.upsert_position(p.symbol, p.contracts, p.side, p.entry_price)


def signed_contracts(snapshot) -> float:
    qty = float(snapshot.contracts)
    side = str(snapshot.side).lower()
    if qty < 0:
        return qty
    if side == "short":
        return -qty
    return qty


def net_contracts_for_symbol(positions, symbol: str) -> float:
    total = 0.0
    for p in positions:
        if p.symbol == symbol:
            total += signed_contracts(p)
    return total


def order_price_from_reference(side: str, order_type: str, ref_price: float, offset_bps: float) -> float | None:
    if ref_price <= 0:
        return None
    if order_type == "market":
        return ref_price

    offset = offset_bps / 10000.0
    if side.lower() == "buy":
        return ref_price * (1.0 - offset)
    return ref_price * (1.0 + offset)


def place_and_record(adapter, store: JSONStateStore, req: OrderRequest, event_type: str) -> None:
    result = adapter.place_order(req)
    store.append_event(
        event_type,
        {
            "order_id": result.order_id,
            "client_order_id": result.client_order_id,
            "symbol": result.symbol,
            "side": result.side,
            "order_type": result.order_type,
            "amount": result.amount,
            "price": result.price,
            "status": result.status,
            "filled": result.filled,
            "tag": req.tag,
            "reduce_only": req.reduce_only,
        },
    )
    print(f"[ORDER] {event_type} {result.order_id} status={result.status} filled={result.filled}")


def align_to_strategy_target(adapter, store: JSONStateStore, args, target: StrategyTarget, current_net: float) -> None:
    target_net = float(target.target_contracts)
    tol = float(args.qty_tolerance)
    ref_price = float(target.last_price)

    store.append_event("strategy_target", target.to_dict())
    print(
        "[STRATEGY] "
        f"asof_5m={target.asof_5m} side={target.target_side} target={target_net:.6f} "
        f"price={ref_price:.2f} long_score={target.long_score} short_score={target.short_score} "
        f"completed_4h={target.completed_4h_bar}"
    )

    if abs(target_net - current_net) <= tol:
        print("[STRATEGY] position already aligned")
        return

    crossed_zero = (current_net > 0 > target_net) or (current_net < 0 < target_net)
    if crossed_zero and abs(current_net) > tol:
        close_side = "sell" if current_net > 0 else "buy"
        close_price = order_price_from_reference(close_side, args.strategy_order_type, ref_price, args.limit_offset_bps)
        place_and_record(
            adapter,
            store,
            OrderRequest(
                symbol=args.symbol,
                side=close_side,
                order_type=args.strategy_order_type,
                amount=abs(current_net),
                price=close_price,
                reduce_only=True,
                tag="v85-strategy-flatten",
            ),
            "strategy_flatten",
        )
        current_net = 0.0

    delta = target_net - current_net
    if abs(delta) <= tol:
        return

    side = "buy" if delta > 0 else "sell"
    reduce_only = abs(target_net) < abs(current_net) and ((target_net >= 0) == (current_net >= 0))
    price = order_price_from_reference(side, args.strategy_order_type, ref_price, args.limit_offset_bps)
    place_and_record(
        adapter,
        store,
        OrderRequest(
            symbol=args.symbol,
            side=side,
            order_type=args.strategy_order_type,
            amount=abs(delta),
            price=price,
            reduce_only=reduce_only,
            tag="v85-strategy-align",
        ),
        "strategy_align",
    )


def run_once(args) -> int:
    state_store = JSONStateStore(args.state)
    state = state_store.startup_recovery_snapshot()
    state_store.append_event("startup", {"state_path": str(args.state)})

    adapter = build_adapter(args)
    if not adapter.ping():
        state_store.set_kill_switch(True, "exchange_ping_failed")
        state_store.append_event("fatal", {"reason": "exchange_ping_failed"})
        print("[FATAL] exchange ping failed")
        return 2

    balance = adapter.fetch_balance()
    positions = adapter.fetch_positions([args.symbol])
    open_orders = adapter.fetch_open_orders(args.symbol)

    report = reconcile_state(state, positions, open_orders)
    if report.has_actions:
        apply_reconcile_actions(state_store, report)
        print(f"[RECONCILE] applied {len(report.actions)} actions")
    else:
        print("[RECONCILE] no drift found")

    sync_positions_to_state(state_store, positions)

    limits = RiskLimits(
        max_daily_loss_pct=args.max_daily_loss_pct,
        max_drawdown_pct=args.max_drawdown_pct,
        max_position_notional=args.max_position_notional,
        max_consecutive_errors=args.max_consecutive_errors,
    )
    equity = balance.total_usdt if balance.total_usdt > 0 else args.paper_cash
    risk = RuntimeRiskManager(limits, initial_equity=equity)

    tripped, reason = risk.on_equity(equity, datetime.now(timezone.utc))
    if tripped:
        state_store.set_kill_switch(True, reason)
        state_store.append_event("risk_trip", {"reason": reason})
        print(f"[KILL] {reason}")
        return 3

    for p in positions:
        notional = abs(signed_contracts(p) * p.entry_price)
        tripped, reason = risk.on_position_notional(notional)
        if tripped:
            state_store.set_kill_switch(True, reason)
            state_store.append_event("risk_trip", {"reason": reason, "symbol": p.symbol})
            print(f"[KILL] {reason}")
            return 3

    current_state = state_store.load()
    if current_state.get("kill_switch", {}).get("enabled", False):
        print(f"[HALT] kill switch enabled: {current_state['kill_switch'].get('reason', '')}")
        return 4

    if args.run_strategy:
        params = build_strategy_params(args)
        target = compute_strategy_target(
            args.data_dir,
            equity,
            params=params,
            symbol=args.symbol,
            refresh_data=(args.refresh_data or args.run_strategy),
            use_intrabar_stop=(not args.no_intrabar),
            allow_short=args.allow_short,
        )

        if args.signal_only:
            state_store.append_event("strategy_signal_only", target.to_dict())
            print("[STRATEGY] signal-only mode")
        else:
            current_net = net_contracts_for_symbol(positions, args.symbol)
            align_to_strategy_target(adapter, state_store, args, target, current_net)
            positions = adapter.fetch_positions([args.symbol])
            sync_positions_to_state(state_store, positions)

    if args.send_test_order:
        req = OrderRequest(
            symbol=args.symbol,
            side=args.test_order_side,
            order_type=args.test_order_type,
            amount=args.test_order_amount,
            price=args.test_order_price,
            reduce_only=args.test_order_reduce_only,
            tag="v85-live-smoke",
        )
        place_and_record(adapter, state_store, req, "order_submitted")

    print("[OK] live runner pass")
    return 0


def run_loop(args) -> int:
    while True:
        try:
            code = run_once(args)
        except Exception as exc:
            print(f"[ERROR] {type(exc).__name__}: {exc}")
            if args.loop_seconds <= 0:
                return 1
            code = 1

        if args.loop_seconds <= 0:
            return code

        if code != 0 and (not args.keep_going_on_error):
            return code

        time.sleep(args.loop_seconds)


def main():
    ap = argparse.ArgumentParser(description="V85 live execution kernel runner")
    ap.add_argument("--symbol", default="BTC/USDT:USDT")
    ap.add_argument("--state", type=Path, default=Path("./data/live_state.json"))
    ap.add_argument("--data_dir", type=Path, default=Path("./data"))

    ap.add_argument("--paper", action="store_true", help="use paper adapter")
    ap.add_argument("--paper_cash", type=float, default=10000.0)
    ap.add_argument("--testnet", action="store_true")
    ap.add_argument("--dry_run", action="store_true")

    ap.add_argument("--run_strategy", action="store_true")
    ap.add_argument("--signal_only", action="store_true")
    ap.add_argument("--refresh_data", action="store_true")
    ap.add_argument("--no_intrabar", action="store_true")
    ap.add_argument("--allow_short", action="store_true")
    ap.add_argument("--strategy_order_type", choices=["market", "limit"], default="market")
    ap.add_argument("--limit_offset_bps", type=float, default=5.0)
    ap.add_argument("--qty_tolerance", type=float, default=1e-6)
    ap.add_argument("--loop_seconds", type=int, default=0)
    ap.add_argument("--keep_going_on_error", action="store_true")

    ap.add_argument("--position_pct", type=float, default=30.0)
    ap.add_argument("--commission_pct", type=float, default=0.06)
    ap.add_argument("--initial_stop_atr", type=float, default=2.4)
    ap.add_argument("--trail_start_atr", type=float, default=3.0)
    ap.add_argument("--trail_offset_atr", type=float, default=2.8)
    ap.add_argument("--tp1_atr", type=float, default=2.1)
    ap.add_argument("--tp2_atr", type=float, default=3.5)
    ap.add_argument("--disable_partial_tp", action="store_true")
    ap.add_argument("--min_long_score", type=int, default=2)
    ap.add_argument("--min_short_score", type=int, default=4)
    ap.add_argument("--adx_trend_level", type=float, default=22.0)

    ap.add_argument("--send_test_order", action="store_true")
    ap.add_argument("--test_order_side", choices=["buy", "sell"], default="buy")
    ap.add_argument("--test_order_type", choices=["market", "limit"], default="limit")
    ap.add_argument("--test_order_amount", type=float, default=0.001)
    ap.add_argument("--test_order_price", type=float, default=0.0)
    ap.add_argument("--test_order_reduce_only", action="store_true")

    ap.add_argument("--max_daily_loss_pct", type=float, default=3.0)
    ap.add_argument("--max_drawdown_pct", type=float, default=25.0)
    ap.add_argument("--max_position_notional", type=float, default=100000.0)
    ap.add_argument("--max_consecutive_errors", type=int, default=8)

    args = ap.parse_args()
    code = run_loop(args)
    raise SystemExit(code)


if __name__ == "__main__":
    main()
