"""Инструменты, которые автономный агент может вызвать.

Парсер берёт JSON-ответ LLM, валидирует и через risk-manager превращает
в реальные действия движка. Любое нарушение → отклонение действия с причиной.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from ..core.config import Settings
from ..core.database import session_scope
from ..core.logging import logger
from ..engine.trader import TradeEngine
from ..exchange.base import ExchangeError
from ..models.db import Position
from ..models.schemas import Signal
from ..risk.manager import RiskManager


ALLOWED_TOOLS = {"place_order", "close_position", "hold"}


@dataclass
class ToolCall:
    tool: str
    args: dict[str, Any]


@dataclass
class ExecutionResult:
    tool: str
    args: dict[str, Any]
    accepted: bool
    detail: str
    order_id: str = ""


def parse_plan(raw: str) -> tuple[str, list[ToolCall], str]:
    """Извлечь (thesis, actions, error) из LLM-ответа.

    Возвращает пустые actions + error, если JSON невалиден.
    """
    text = (raw or "").strip()
    if not text:
        return "", [], "empty response"
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return "", [], "no JSON object found"
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            return "", [], f"json decode: {exc}"

    if not isinstance(data, dict):
        return "", [], "top-level JSON is not object"

    thesis = str(data.get("thesis", "")).strip()
    raw_actions = data.get("actions") or []
    if not isinstance(raw_actions, list):
        return thesis, [], "'actions' is not a list"

    calls: list[ToolCall] = []
    for raw_action in raw_actions:
        if not isinstance(raw_action, dict):
            continue
        tool = str(raw_action.get("tool", "")).strip().lower()
        args = raw_action.get("args") or {}
        if tool not in ALLOWED_TOOLS:
            continue
        if not isinstance(args, dict):
            continue
        calls.append(ToolCall(tool=tool, args=args))
    return thesis, calls, ""


class ToolExecutor:
    """Выполняет валидированные действия агента через TradeEngine + риск-менеджер."""

    def __init__(self, engine: TradeEngine, settings: Settings) -> None:
        self.engine = engine
        self.settings = settings
        self.risk = RiskManager(settings)

    async def execute(
        self,
        calls: list[ToolCall],
        snapshot: dict[str, Any],
        max_actions: int,
    ) -> list[ExecutionResult]:
        results: list[ExecutionResult] = []
        cash = float(snapshot.get("cash", 0.0))
        equity = float(snapshot.get("equity", 0.0))
        daily_pnl = float(snapshot.get("daily_pnl", 0.0))
        daily_start_equity = float(snapshot.get("daily_start_equity", equity))
        prices: dict[str, float] = snapshot.get("prices", {}) or {}
        positions_qty: dict[str, float] = snapshot.get("positions_qty", {}) or {}
        open_positions = sum(1 for q in positions_qty.values() if q > 0)
        allowed_symbols = set(self.settings.symbols)

        for call in calls[:max_actions]:
            if call.tool == "hold":
                reason = str(call.args.get("reason", "")).strip() or "hold"
                results.append(ExecutionResult(call.tool, call.args, True, reason))
                continue

            symbol = str(call.args.get("symbol", "")).upper().strip()
            if "/" not in symbol:
                results.append(ExecutionResult(call.tool, call.args, False,
                                               f"bad symbol '{symbol}'"))
                continue
            if symbol not in allowed_symbols:
                results.append(ExecutionResult(call.tool, call.args, False,
                                               f"symbol {symbol} не в списке разрешённых"))
                continue

            price = prices.get(symbol)
            if price is None:
                try:
                    price = await self.engine.exchange.fetch_ticker(symbol)
                    prices[symbol] = price
                except ExchangeError as exc:
                    results.append(ExecutionResult(call.tool, call.args, False,
                                                   f"нет цены: {exc}"))
                    continue

            if call.tool == "place_order":
                side = str(call.args.get("side", "")).lower().strip()
                if side not in ("buy", "sell"):
                    results.append(ExecutionResult(call.tool, call.args, False,
                                                   f"bad side '{side}'"))
                    continue
                try:
                    quote_amount = float(call.args.get("quote_amount", 0))
                except (TypeError, ValueError):
                    results.append(ExecutionResult(call.tool, call.args, False,
                                                   "quote_amount должен быть числом"))
                    continue
                reason = str(call.args.get("reason", "")).strip()[:200] or "LLM agent"

                existing_qty = positions_qty.get(symbol, 0.0)

                if side == "buy":
                    requested_qty = quote_amount / price if price > 0 else 0.0
                    decision = self.risk.position_size_for_buy(
                        equity=equity,
                        cash_available=cash,
                        price=price,
                        open_positions=open_positions,
                        daily_pnl=daily_pnl,
                        daily_start_equity=daily_start_equity,
                        existing_qty=existing_qty,
                    )
                    if not decision.allow:
                        results.append(ExecutionResult(call.tool, call.args, False,
                                                       f"риск-менеджер: {decision.reason}"))
                        continue
                    # уважаем меньшее из «риск-менеджер разрешил» и «агент попросил»
                    qty = min(decision.quantity, requested_qty) if requested_qty > 0 else decision.quantity
                    if qty * price < self.settings.min_order_notional:
                        results.append(ExecutionResult(call.tool, call.args, False,
                                                       f"итоговый размер {qty*price:.2f} < min"))
                        continue
                    try:
                        order = await self.engine.exchange.create_market_order(symbol, "buy", qty)
                    except ExchangeError as exc:
                        results.append(ExecutionResult(call.tool, call.args, False,
                                                       f"биржа: {exc}"))
                        continue
                    signal = Signal(symbol=symbol, action="buy", confidence=0.7,
                                    price=order.price, votes=[],
                                    reason=f"[agent] {reason}")
                    self.engine._persist_order(order, signal, side="buy")
                    self.engine._upsert_position_after_buy(symbol, order.quantity, order.price)
                    cash -= order.quantity * order.price + order.fee
                    positions_qty[symbol] = positions_qty.get(symbol, 0.0) + order.quantity
                    open_positions = sum(1 for q in positions_qty.values() if q > 0)
                    results.append(ExecutionResult(
                        call.tool, call.args, True,
                        f"BUY {symbol} qty={order.quantity:.6f} @ {order.price:.4f}",
                        order_id=order.order_id,
                    ))

                else:  # sell
                    if existing_qty <= 0:
                        results.append(ExecutionResult(call.tool, call.args, False,
                                                       "нет позиции для продажи"))
                        continue
                    requested_qty = min(quote_amount / price, existing_qty) if quote_amount > 0 else existing_qty
                    if requested_qty * price < self.settings.min_order_notional:
                        results.append(ExecutionResult(call.tool, call.args, False,
                                                       "итоговый размер sell < min"))
                        continue
                    try:
                        order = await self.engine.exchange.create_market_order(
                            symbol, "sell", requested_qty
                        )
                    except ExchangeError as exc:
                        results.append(ExecutionResult(call.tool, call.args, False,
                                                       f"биржа: {exc}"))
                        continue
                    signal = Signal(symbol=symbol, action="sell", confidence=0.7,
                                    price=order.price, votes=[],
                                    reason=f"[agent] {reason}")
                    self.engine._persist_order(order, signal, side="sell")
                    self.engine._close_position(symbol, order.price, order.quantity)
                    cash += order.quantity * order.price - order.fee
                    positions_qty[symbol] = max(0.0, existing_qty - order.quantity)
                    open_positions = sum(1 for q in positions_qty.values() if q > 0)
                    results.append(ExecutionResult(
                        call.tool, call.args, True,
                        f"SELL {symbol} qty={order.quantity:.6f} @ {order.price:.4f}",
                        order_id=order.order_id,
                    ))

            elif call.tool == "close_position":
                reason = str(call.args.get("reason", "")).strip()[:200] or "agent close"
                existing_qty = positions_qty.get(symbol, 0.0)
                if existing_qty <= 0:
                    results.append(ExecutionResult(call.tool, call.args, False,
                                                   "нет позиции для закрытия"))
                    continue
                try:
                    order = await self.engine.exchange.create_market_order(
                        symbol, "sell", existing_qty
                    )
                except ExchangeError as exc:
                    results.append(ExecutionResult(call.tool, call.args, False,
                                                   f"биржа: {exc}"))
                    continue
                signal = Signal(symbol=symbol, action="sell", confidence=1.0,
                                price=order.price, votes=[],
                                reason=f"[agent close] {reason}")
                self.engine._persist_order(order, signal, side="sell")
                self.engine._close_position(symbol, order.price, order.quantity)
                cash += order.quantity * order.price - order.fee
                positions_qty[symbol] = 0.0
                open_positions = sum(1 for q in positions_qty.values() if q > 0)
                results.append(ExecutionResult(
                    call.tool, call.args, True,
                    f"CLOSE {symbol} qty={order.quantity:.6f} @ {order.price:.4f}",
                    order_id=order.order_id,
                ))

        # отброшенные действия из-за лимита max_actions
        for call in calls[max_actions:]:
            results.append(ExecutionResult(call.tool, call.args, False,
                                           f"превышен лимит {max_actions} действий за цикл"))
        return results


def positions_snapshot() -> dict[str, float]:
    """Считать актуальные открытые позиции с их количеством из БД."""
    out: dict[str, float] = {}
    with session_scope() as session:
        rows = session.execute(
            select(Position).where(Position.quantity > 0)
        ).scalars().all()
        for row in rows:
            out[row.symbol] = float(row.quantity)
    return out
