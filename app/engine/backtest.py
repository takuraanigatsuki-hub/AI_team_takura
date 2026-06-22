"""Простой векторизованный бэктестер: проходит свечи и применяет стратегии."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from ..core.config import Settings
from ..models.schemas import StrategyVote
from ..risk.manager import RiskManager
from ..strategies import Strategy, StrategyContext
from .aggregator import aggregate_votes


@dataclass
class BacktestTrade:
    side: str
    timestamp: int
    price: float
    quantity: float
    reason: str


@dataclass
class BacktestResult:
    starting_balance: float
    final_equity: float
    pnl: float
    pnl_pct: float
    trades: list[BacktestTrade] = field(default_factory=list)
    equity_curve: list[tuple[int, float]] = field(default_factory=list)

    @property
    def num_trades(self) -> int:
        return len(self.trades)


def run_backtest(
    candles: pd.DataFrame,
    strategies: list[Strategy],
    settings: Settings,
    symbol: str = "BACKTEST/USDT",
    starting_balance: float = 10_000.0,
    warmup: int | None = None,
) -> BacktestResult:
    """Бэктест по одному инструменту. `candles` должен иметь колонки
    open/high/low/close/volume и индекс = timestamp в миллисекундах."""
    if candles.empty:
        return BacktestResult(starting_balance, starting_balance, 0.0, 0.0)

    risk = RiskManager(settings)
    warmup = warmup or max((s.warmup_candles() for s in strategies), default=50)

    cash = float(starting_balance)
    qty = 0.0
    avg_cost = 0.0
    trades: list[BacktestTrade] = []
    equity_curve: list[tuple[int, float]] = []
    daily_start_equity = cash

    for i in range(warmup, len(candles)):
        window = candles.iloc[: i + 1]
        price = float(window["close"].iloc[-1])
        ts = int(window.index[-1])

        ctx = StrategyContext(
            symbol=symbol, timeframe=settings.timeframe,
            candles=window, position_quantity=qty,
        )
        votes: list[StrategyVote] = []
        for strategy in strategies:
            try:
                votes.append(strategy.evaluate(ctx))
            except Exception as exc:  # noqa: BLE001
                votes.append(StrategyVote(name=strategy.name, action="hold",
                                          confidence=0.0, reason=f"err: {exc}"))
        signal = aggregate_votes(symbol, price, votes, settings.signal_consensus)

        equity = cash + qty * price

        # стопы/тейки
        if qty > 0 and avg_cost > 0:
            if risk.should_close_for_stop_loss(avg_cost, price):
                cash += qty * price * (1 - 0.001)
                trades.append(BacktestTrade("sell", ts, price, qty, "stop-loss"))
                qty = 0.0
                avg_cost = 0.0
                equity_curve.append((ts, cash))
                continue
            if risk.should_close_for_take_profit(avg_cost, price):
                cash += qty * price * (1 - 0.001)
                trades.append(BacktestTrade("sell", ts, price, qty, "take-profit"))
                qty = 0.0
                avg_cost = 0.0
                equity_curve.append((ts, cash))
                continue

        if signal.action == "buy" and qty == 0:
            decision = risk.position_size_for_buy(
                equity=equity, cash_available=cash, price=price,
                open_positions=0, daily_pnl=equity - daily_start_equity,
                daily_start_equity=daily_start_equity, existing_qty=0,
            )
            if decision.allow:
                cost = decision.quantity * price
                fee = cost * 0.001
                cash -= cost + fee
                avg_cost = price
                qty = decision.quantity
                trades.append(BacktestTrade("buy", ts, price, qty, signal.reason))
        elif signal.action == "sell" and qty > 0:
            cash += qty * price * (1 - 0.001)
            trades.append(BacktestTrade("sell", ts, price, qty, signal.reason))
            qty = 0.0
            avg_cost = 0.0

        equity_curve.append((ts, cash + qty * price))

    final_price = float(candles["close"].iloc[-1])
    final_equity = cash + qty * final_price
    pnl = final_equity - starting_balance
    pnl_pct = pnl / starting_balance * 100 if starting_balance else 0.0
    return BacktestResult(
        starting_balance=starting_balance,
        final_equity=final_equity,
        pnl=pnl,
        pnl_pct=pnl_pct,
        trades=trades,
        equity_curve=equity_curve,
    )
