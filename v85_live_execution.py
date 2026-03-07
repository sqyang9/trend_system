#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v85_live_execution.py
Live/paper execution adapters for OKX-style trading workflows.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional


@dataclass
class OrderRequest:
    symbol: str
    side: str  # buy / sell
    order_type: str  # market / limit
    amount: float
    price: Optional[float] = None
    reduce_only: bool = False
    client_order_id: Optional[str] = None
    tag: str = ""


@dataclass
class OrderResult:
    order_id: str
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    amount: float
    price: Optional[float]
    filled: float
    status: str
    timestamp: str
    raw: Dict


@dataclass
class PositionSnapshot:
    symbol: str
    side: str
    contracts: float
    entry_price: float
    unrealized_pnl: float
    raw: Dict


@dataclass
class BalanceSnapshot:
    total_usdt: float
    free_usdt: float
    used_usdt: float
    raw: Dict


class ExecutionAdapter(ABC):
    @abstractmethod
    def ping(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def place_order(self, req: OrderRequest) -> OrderResult:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        raise NotImplementedError

    @abstractmethod
    def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[PositionSnapshot]:
        raise NotImplementedError

    @abstractmethod
    def fetch_balance(self) -> BalanceSnapshot:
        raise NotImplementedError


class CCXTOKXExecutionAdapter(ExecutionAdapter):
    """Production adapter backed by ccxt OKX client."""

    def __init__(
        self,
        api_key: str,
        secret: str,
        password: str,
        *,
        testnet: bool = False,
        default_type: str = "swap",
        dry_run: bool = True,
        timeout_ms: int = 15000,
    ):
        import ccxt  # lazy import

        self.dry_run = dry_run
        self._ccxt = ccxt
        self.exchange = ccxt.okx(
            {
                "apiKey": api_key,
                "secret": secret,
                "password": password,
                "enableRateLimit": True,
                "timeout": timeout_ms,
                "options": {
                    "defaultType": default_type,
                },
            }
        )
        self.exchange.set_sandbox_mode(testnet)

    def ping(self) -> bool:
        try:
            _ = self.exchange.fetch_time()
            return True
        except Exception:
            return False

    def place_order(self, req: OrderRequest) -> OrderResult:
        now = datetime.now(timezone.utc).isoformat()
        cid = req.client_order_id or f"v85-{int(datetime.now(timezone.utc).timestamp() * 1000)}"

        if self.dry_run:
            return OrderResult(
                order_id=f"dry-{cid}",
                client_order_id=cid,
                symbol=req.symbol,
                side=req.side,
                order_type=req.order_type,
                amount=req.amount,
                price=req.price,
                filled=req.amount,
                status="closed",
                timestamp=now,
                raw={"dry_run": True, "tag": req.tag},
            )

        params = {}
        if req.reduce_only:
            params["reduceOnly"] = True
        if cid:
            params["clientOrderId"] = cid
        if req.tag:
            params["tag"] = req.tag

        order_price = None if req.order_type == "market" else req.price
        o = self.exchange.create_order(
            symbol=req.symbol,
            type=req.order_type,
            side=req.side,
            amount=req.amount,
            price=order_price,
            params=params,
        )

        return OrderResult(
            order_id=str(o.get("id", "")),
            client_order_id=str(o.get("clientOrderId", cid)),
            symbol=str(o.get("symbol", req.symbol)),
            side=str(o.get("side", req.side)),
            order_type=str(o.get("type", req.order_type)),
            amount=float(o.get("amount", req.amount) or req.amount),
            price=float(o["price"]) if o.get("price") is not None else req.price,
            filled=float(o.get("filled", 0.0) or 0.0),
            status=str(o.get("status", "unknown")),
            timestamp=now,
            raw=o,
        )

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        if self.dry_run:
            return True
        try:
            self.exchange.cancel_order(order_id, symbol)
            return True
        except Exception:
            return False

    def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        if self.dry_run:
            return []
        return self.exchange.fetch_open_orders(symbol)

    def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[PositionSnapshot]:
        if self.dry_run:
            return []

        rows = self.exchange.fetch_positions(symbols)
        out: List[PositionSnapshot] = []
        for r in rows:
            contracts = float(r.get("contracts") or 0.0)
            if abs(contracts) < 1e-12:
                continue
            side = str(r.get("side") or ("long" if contracts > 0 else "short"))
            out.append(
                PositionSnapshot(
                    symbol=str(r.get("symbol", "")),
                    side=side,
                    contracts=contracts,
                    entry_price=float(r.get("entryPrice") or 0.0),
                    unrealized_pnl=float(r.get("unrealizedPnl") or 0.0),
                    raw=r,
                )
            )
        return out

    def fetch_balance(self) -> BalanceSnapshot:
        if self.dry_run:
            return BalanceSnapshot(total_usdt=0.0, free_usdt=0.0, used_usdt=0.0, raw={"dry_run": True})

        b = self.exchange.fetch_balance()
        total = float(((b.get("total") or {}).get("USDT")) or 0.0)
        free = float(((b.get("free") or {}).get("USDT")) or 0.0)
        used = float(((b.get("used") or {}).get("USDT")) or 0.0)
        return BalanceSnapshot(total_usdt=total, free_usdt=free, used_usdt=used, raw=b)


class PaperExecutionAdapter(ExecutionAdapter):
    """Deterministic paper adapter for local rehearsals and CI-like checks."""

    def __init__(self, init_cash_usdt: float = 10000.0):
        self.cash = float(init_cash_usdt)
        self.open_orders: Dict[str, Dict] = {}
        self.positions: Dict[str, Dict] = {}
        self._counter = 0

    def ping(self) -> bool:
        return True

    def place_order(self, req: OrderRequest) -> OrderResult:
        self._counter += 1
        oid = f"paper-{self._counter}"
        cid = req.client_order_id or oid
        side = req.side.lower()

        pos = self.positions.get(req.symbol, {"contracts": 0.0, "entry_price": 0.0})
        qty = float(pos["contracts"])
        prev_entry = float(pos["entry_price"])
        px = float(req.price) if req.price is not None else prev_entry
        delta = float(req.amount)

        if side == "buy":
            intended_qty = qty + delta
        else:
            intended_qty = qty - delta

        if req.reduce_only:
            if qty > 0 and side == "sell":
                new_qty = max(0.0, qty - delta)
            elif qty < 0 and side == "buy":
                new_qty = min(0.0, qty + delta)
            else:
                new_qty = qty
        else:
            new_qty = intended_qty

        filled = abs(new_qty - qty)

        if abs(new_qty) < 1e-12:
            self.positions.pop(req.symbol, None)
        else:
            if abs(qty) > 1e-12 and (qty > 0) == (new_qty > 0) and abs(new_qty) > abs(qty) and px > 0:
                add_qty = abs(new_qty) - abs(qty)
                entry_price = ((abs(qty) * prev_entry) + (add_qty * px)) / abs(new_qty)
            elif abs(qty) > 1e-12 and (qty > 0) == (new_qty > 0) and abs(new_qty) <= abs(qty):
                entry_price = prev_entry
            else:
                entry_price = px if px > 0 else prev_entry

            self.positions[req.symbol] = {
                "contracts": new_qty,
                "entry_price": entry_price,
            }

        now = datetime.now(timezone.utc).isoformat()
        status = "closed" if filled > 0 else "rejected"
        return OrderResult(
            order_id=oid,
            client_order_id=cid,
            symbol=req.symbol,
            side=req.side,
            order_type=req.order_type,
            amount=req.amount,
            price=px if px > 0 else req.price,
            filled=filled,
            status=status,
            timestamp=now,
            raw={"paper": True, "tag": req.tag, "reduce_only": req.reduce_only},
        )

    def cancel_order(self, order_id: str, symbol: str) -> bool:
        _ = symbol
        return self.open_orders.pop(order_id, None) is not None

    def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        rows = list(self.open_orders.values())
        if symbol is None:
            return rows
        return [r for r in rows if r.get("symbol") == symbol]

    def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[PositionSnapshot]:
        keys = list(self.positions.keys()) if symbols is None else [s for s in symbols if s in self.positions]
        out: List[PositionSnapshot] = []
        for s in keys:
            qty = float(self.positions[s]["contracts"])
            out.append(
                PositionSnapshot(
                    symbol=s,
                    side="long" if qty > 0 else "short",
                    contracts=qty,
                    entry_price=float(self.positions[s]["entry_price"]),
                    unrealized_pnl=0.0,
                    raw={"paper": True},
                )
            )
        return out

    def fetch_balance(self) -> BalanceSnapshot:
        return BalanceSnapshot(total_usdt=self.cash, free_usdt=self.cash, used_usdt=0.0, raw={"paper": True})

