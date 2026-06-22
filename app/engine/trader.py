from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select

from ..core.config import Settings, get_settings
from ..core.database import session_scope
from ..core.logging import logger, setup_logging
from ..exchange.base import BaseExchange, ExchangeError
from ..exchange.factory import build_exchange
from ..exchange.paper import PaperExchange, _split_symbol
from ..models.db import DecisionLog, EquityPoint, Order, Position
from ..models.schemas import (
    BotStatus,
    Signal,
    StrategyVote,
)
from ..risk.manager import RiskManager
from ..strategies import Strategy, StrategyContext, build_strategies
from .aggregator import aggregate_votes


@dataclass
class _RuntimeStats:
    started_at: datetime | None = None
    last_tick_at: datetime | None = None
    last_error: str | None = None
    last_equity: float = 0.0
    last_cash: float = 0.0
    last_positions_value: float = 0.0
    daily_start_equity: float = 0.0
    daily_start_at: datetime | None = None
    paused: bool = False
    kill_switch: bool = False
    cached_balances: dict[str, float] = field(default_factory=dict)
    adaptive_weights: dict[str, float] = field(default_factory=dict)
    last_regime: dict | None = None
    last_strategy_refresh_at: datetime | None = None


class TradeEngine:
    """Async движок: периодически опрашивает биржу, запускает стратегии,
    проверяет риск-менеджмент и (опционально) выставляет ордера."""

    def __init__(
        self,
        settings: Settings | None = None,
        exchange: BaseExchange | None = None,
        strategies: list[Strategy] | None = None,
    ) -> None:
        setup_logging()
        self.settings = settings or get_settings()
        self.exchange = exchange or build_exchange(self.settings)
        self.strategies = strategies or build_strategies(self.settings.strategies)
        self.risk = RiskManager(self.settings)
        self.stats = _RuntimeStats()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._lock = asyncio.Lock()

    # --------------------------------------------------------------- lifecycle
    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self.stats.started_at = datetime.now(timezone.utc)
        self.stats.daily_start_at = self.stats.started_at
        # подтянем равенство стартового капитала, если есть
        equity, cash, pos_value = await self._equity_snapshot()
        self.stats.daily_start_equity = equity
        self.stats.last_equity = equity
        self.stats.last_cash = cash
        self.stats.last_positions_value = pos_value
        self._task = asyncio.create_task(self._run_loop(), name="trade-engine-loop")
        logger.info(
            "Trade engine started: mode={} exchange={} symbols={} strategies={}",
            self.settings.mode, self.settings.exchange_id,
            self.settings.symbols, [s.name for s in self.strategies],
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=15.0)
            except asyncio.TimeoutError:
                self._task.cancel()
            self._task = None
        try:
            await self.exchange.close()
        except Exception:
            pass
        logger.info("Trade engine stopped")

    def pause(self, value: bool = True) -> None:
        self.stats.paused = bool(value)
        logger.info("Trade engine paused={}", self.stats.paused)

    def kill(self) -> None:
        self.stats.kill_switch = True
        logger.warning("KILL SWITCH activated — no new trades will be opened")

    def reset_kill(self) -> None:
        self.stats.kill_switch = False
        logger.info("Kill switch cleared")

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    # --------------------------------------------------------------- main loop
    async def _run_loop(self) -> None:
        interval = max(2, int(self.settings.loop_interval_seconds))
        while not self._stop.is_set():
            try:
                await self.tick()
            except Exception as exc:  # noqa: BLE001
                self.stats.last_error = str(exc)
                logger.exception("tick failed: {}", exc)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass

    async def tick(self) -> None:
        async with self._lock:
            self.stats.last_tick_at = datetime.now(timezone.utc)
            self._maybe_rollover_day()

            # 1) собираем тикеры и обновляем кэш балансов
            balances = await self.exchange.fetch_balance()
            cash, positions_value, prices = await self._compute_state(balances)
            equity = cash + positions_value
            self.stats.last_equity = equity
            self.stats.last_cash = cash
            self.stats.last_positions_value = positions_value

            with session_scope() as session:
                session.add(EquityPoint(
                    cash=cash, positions_value=positions_value,
                    equity=equity, mode=self.settings.mode,
                ))

            # 2) проверяем стопы/тейки на открытых позициях
            await self._enforce_stops_and_takes(prices)

            # 3) для каждого символа гоняем стратегии
            if self.stats.paused or self.stats.kill_switch:
                logger.debug("engine paused/kill — пропускаем стратегии")
                return

            daily_pnl = equity - self.stats.daily_start_equity
            if self.risk.daily_loss_blocked(daily_pnl, self.stats.daily_start_equity):
                logger.warning("дневной лимит убытков достигнут — новые сделки заблокированы")
                return

            for symbol in self.settings.symbols:
                try:
                    await self._evaluate_symbol(symbol, prices.get(symbol, 0.0),
                                                cash, equity, daily_pnl)
                except ExchangeError as exc:
                    self.stats.last_error = str(exc)
                    logger.error("exchange error для {}: {}", symbol, exc)
                except Exception as exc:  # noqa: BLE001
                    self.stats.last_error = str(exc)
                    logger.exception("ошибка обработки {}: {}", symbol, exc)

    # --------------------------------------------------------------- per-symbol
    async def _evaluate_symbol(
        self,
        symbol: str,
        cached_price: float,
        cash: float,
        equity: float,
        daily_pnl: float,
    ) -> None:
        candles = await self._fetch_candles(symbol)
        if candles.empty:
            return
        price = float(cached_price or candles["close"].iloc[-1])

        position_qty = self._get_open_position_qty(symbol)
        ctx = StrategyContext(
            symbol=symbol, timeframe=self.settings.timeframe,
            candles=candles, position_quantity=position_qty,
        )

        votes: list[StrategyVote] = []
        for strategy in self.strategies:
            try:
                votes.append(strategy.evaluate(ctx))
            except Exception as exc:  # noqa: BLE001
                logger.exception("стратегия {} упала: {}", strategy.name, exc)
                votes.append(StrategyVote(
                    name=strategy.name, action="hold", confidence=0.0,
                    reason=f"ошибка: {exc}",
                ))

        weights = self._effective_weights(candles)
        signal = aggregate_votes(
            symbol, price, votes, self.settings.signal_consensus, weights=weights,
        )
        self._log_decision(signal)

        if signal.action == "buy":
            await self._place_buy(signal, cash, equity, daily_pnl, position_qty)
        elif signal.action == "sell" and position_qty > 0:
            await self._place_sell(signal, position_qty)

    async def _place_buy(
        self,
        signal: Signal,
        cash: float,
        equity: float,
        daily_pnl: float,
        existing_qty: float,
    ) -> None:
        open_positions = self._count_open_positions()
        decision = self.risk.position_size_for_buy(
            equity=equity, cash_available=cash, price=signal.price,
            open_positions=open_positions, daily_pnl=daily_pnl,
            daily_start_equity=self.stats.daily_start_equity,
            existing_qty=existing_qty,
        )
        if not decision.allow:
            logger.info("BUY {} отклонён риск-менеджером: {}", signal.symbol, decision.reason)
            return
        try:
            result = await self.exchange.create_market_order(
                signal.symbol, "buy", decision.quantity
            )
        except ExchangeError as exc:
            logger.error("BUY {} не исполнен: {}", signal.symbol, exc)
            return
        logger.info(
            "BUY {} qty={:.6f} @ {:.4f} (риск {} | {})",
            signal.symbol, result.quantity, result.price,
            decision.reason, signal.reason,
        )
        self._persist_order(result, signal, side="buy")
        self._upsert_position_after_buy(signal.symbol, result.quantity, result.price)

    async def _place_sell(self, signal: Signal, position_qty: float) -> None:
        qty = position_qty
        try:
            result = await self.exchange.create_market_order(signal.symbol, "sell", qty)
        except ExchangeError as exc:
            logger.error("SELL {} не исполнен: {}", signal.symbol, exc)
            return
        logger.info(
            "SELL {} qty={:.6f} @ {:.4f} ({})",
            signal.symbol, result.quantity, result.price, signal.reason,
        )
        self._persist_order(result, signal, side="sell")
        self._close_position(signal.symbol, result.price, result.quantity)

    # --------------------------------------------------------------- stops/tps
    async def _enforce_stops_and_takes(self, prices: dict[str, float]) -> None:
        with session_scope() as session:
            positions = session.execute(
                select(Position).where(Position.quantity > 0)
            ).scalars().all()
            to_close: list[tuple[str, float, str]] = []
            for pos in positions:
                price = prices.get(pos.symbol)
                if price is None:
                    try:
                        price = await self.exchange.fetch_ticker(pos.symbol)
                    except ExchangeError:
                        continue
                    prices[pos.symbol] = price
                if self.risk.should_close_for_stop_loss(pos.avg_entry_price, price):
                    to_close.append((pos.symbol, pos.quantity, "stop-loss"))
                elif self.risk.should_close_for_take_profit(pos.avg_entry_price, price):
                    to_close.append((pos.symbol, pos.quantity, "take-profit"))
        for symbol, qty, reason in to_close:
            try:
                result = await self.exchange.create_market_order(symbol, "sell", qty)
            except ExchangeError as exc:
                logger.error("принудительное закрытие {} провалилось: {}", symbol, exc)
                continue
            logger.info("закрыли {} ({}) qty={:.6f} @ {:.4f}",
                        symbol, reason, result.quantity, result.price)
            sig = Signal(
                symbol=symbol, action="sell", confidence=1.0,
                price=result.price, votes=[], reason=reason,
            )
            self._persist_order(result, sig, side="sell")
            self._close_position(symbol, result.price, result.quantity)

    # --------------------------------------------------------------- helpers
    async def _fetch_candles(self, symbol: str) -> pd.DataFrame:
        rows = await self.exchange.fetch_ohlcv(
            symbol, timeframe=self.settings.timeframe, limit=200
        )
        if not rows:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
        df.set_index("ts", inplace=True)
        return df

    async def _compute_state(
        self, balances: dict[str, dict[str, float]]
    ) -> tuple[float, float, dict[str, float]]:
        quote = self.settings.quote_currency.upper()
        cash = float((balances.get(quote) or {}).get("total", 0.0))
        prices: dict[str, float] = {}
        positions_value = 0.0
        for symbol in self.settings.symbols:
            try:
                price = await self.exchange.fetch_ticker(symbol)
            except ExchangeError as exc:
                logger.warning("не смог получить тикер {}: {}", symbol, exc)
                continue
            prices[symbol] = price
            base, sym_quote = _split_symbol(symbol)
            if sym_quote != quote:
                continue
            base_balance = float((balances.get(base) or {}).get("total", 0.0))
            positions_value += base_balance * price
        # для paper биржи без подключения live-балансов учтём виртуальные балансы
        if isinstance(self.exchange, PaperExchange) and not balances:
            snap = self.exchange.snapshot_balances()
            cash = float(snap.get(quote, 0.0))
            for symbol, price in prices.items():
                base, _ = _split_symbol(symbol)
                positions_value += snap.get(base, 0.0) * price
        return cash, positions_value, prices

    async def _equity_snapshot(self) -> tuple[float, float, float]:
        balances = await self.exchange.fetch_balance()
        cash, pv, _ = await self._compute_state(balances)
        return cash + pv, cash, pv

    def _maybe_rollover_day(self) -> None:
        now = datetime.now(timezone.utc)
        start = self.stats.daily_start_at
        if start is None or (now - start) >= timedelta(days=1):
            self.stats.daily_start_at = now.replace(hour=0, minute=0, second=0, microsecond=0)
            self.stats.daily_start_equity = self.stats.last_equity or self.stats.daily_start_equity
            logger.info("daily roll-over: daily_start_equity={:.2f}",
                        self.stats.daily_start_equity)

    def _log_decision(self, signal: Signal) -> None:
        with session_scope() as session:
            session.add(DecisionLog(
                symbol=signal.symbol,
                action=signal.action,
                confidence=signal.confidence,
                price=signal.price,
                strategies=json.dumps([v.model_dump() for v in signal.votes],
                                      ensure_ascii=False),
                reason=signal.reason,
                mode=self.settings.mode,
            ))

    def _persist_order(self, result, signal: Signal, side: str) -> None:
        with session_scope() as session:
            session.add(Order(
                exchange_order_id=result.order_id,
                symbol=result.symbol,
                side=side,
                type="market",
                quantity=result.quantity,
                price=result.price,
                fee=result.fee,
                quote_amount=result.quantity * result.price,
                mode=self.settings.mode,
                status="filled",
                reason=signal.reason,
            ))
        self._notify_order_async(side=side, symbol=result.symbol,
                                 quantity=result.quantity, price=result.price,
                                 reason=signal.reason)

    def _notify_order_async(self, **kwargs) -> None:
        # отправляем уведомление в Telegram в фоне, не блокируя тик
        if not self.settings.telegram_notify_orders:
            return
        try:
            from ..telegram.notifier import get_notifier

            notifier = get_notifier()
            if not notifier.enabled:
                return
            loop = asyncio.get_event_loop()
            loop.create_task(
                notifier.notify_order(mode=self.settings.mode, **kwargs)
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("telegram notify_order skipped: {}", exc)

    def _get_open_position_qty(self, symbol: str) -> float:
        with session_scope() as session:
            pos = session.execute(
                select(Position).where(Position.symbol == symbol)
            ).scalar_one_or_none()
            return float(pos.quantity) if pos else 0.0

    def _count_open_positions(self) -> int:
        with session_scope() as session:
            rows = session.execute(
                select(Position).where(Position.quantity > 0)
            ).scalars().all()
            return len(rows)

    def _upsert_position_after_buy(self, symbol: str, qty: float, price: float) -> None:
        s = self.settings
        with session_scope() as session:
            pos = session.execute(
                select(Position).where(Position.symbol == symbol)
            ).scalar_one_or_none()
            if pos is None:
                pos = Position(
                    symbol=symbol, quantity=0.0, avg_entry_price=0.0,
                    realized_pnl=0.0, stop_loss=0.0, take_profit=0.0,
                )
                session.add(pos)
            new_qty = (pos.quantity or 0.0) + qty
            if new_qty <= 0:
                pos.quantity = 0.0
                pos.avg_entry_price = 0.0
            else:
                pos.avg_entry_price = (
                    (pos.avg_entry_price or 0.0) * (pos.quantity or 0.0)
                    + price * qty
                ) / new_qty
                pos.quantity = new_qty
            if s.stop_loss_pct > 0 and pos.avg_entry_price:
                pos.stop_loss = pos.avg_entry_price * (1 - s.stop_loss_pct)
            if s.take_profit_pct > 0 and pos.avg_entry_price:
                pos.take_profit = pos.avg_entry_price * (1 + s.take_profit_pct)

    def _close_position(self, symbol: str, price: float, qty: float) -> None:
        with session_scope() as session:
            pos = session.execute(
                select(Position).where(Position.symbol == symbol)
            ).scalar_one_or_none()
            if pos is None:
                return
            sell_qty = min(qty, pos.quantity)
            realized = (price - pos.avg_entry_price) * sell_qty
            pos.realized_pnl += realized
            pos.quantity -= sell_qty
            if pos.quantity <= 1e-12:
                pos.quantity = 0.0

    # --------------------------------------------------------------- adaptive
    def _effective_weights(self, candles: pd.DataFrame) -> dict[str, float] | None:
        """Итоговые веса = blend(adaptive, bandit) × regime preferences."""
        if not self.settings.adaptive_enabled:
            return None
        weights = dict(self.stats.adaptive_weights or {})
        # blend с bandit-sampling если включено
        if self.settings.bandit_enabled:
            from ..adaptive.bandit import blend_weights, load_bandit_states, sample_weights

            names = [s.name for s in self.strategies]
            with session_scope() as session:
                states = load_bandit_states(session, names=names)
            bandit_w = sample_weights(states)
            weights = blend_weights(
                weights or {n: 1.0 for n in names},
                bandit_w,
                blend=self.settings.bandit_blend,
            )

        if not weights and not self.settings.adaptive_use_regime:
            return None
        if self.settings.adaptive_use_regime and not candles.empty:
            from ..adaptive.regime import apply_regime_preferences, detect_regime

            regime = detect_regime(candles["close"], window=60)
            self.stats.last_regime = regime.as_dict()
            base_lookup = {s.name: getattr(s, "_base_name", s.name) for s in self.strategies}
            for s in self.strategies:
                weights.setdefault(s.name, 1.0)
            weights = apply_regime_preferences(weights, regime, base_lookup)
        return weights or None

    def refresh_adaptive_weights(self) -> dict[str, float]:
        """Пересчитать адаптивные веса из недавних решений и сохранить snapshot."""
        from ..adaptive.weights import (
            compute_adaptive_weights, compute_performance_snapshots,
            persist_performance_snapshots,
        )
        with session_scope() as session:
            snapshots = compute_performance_snapshots(
                session, lookback=self.settings.adaptive_lookback_decisions
            )
            weights = compute_adaptive_weights(
                snapshots,
                w_min=self.settings.adaptive_min_weight,
                w_max=self.settings.adaptive_max_weight,
            )
            now = datetime.now(timezone.utc)
            persist_performance_snapshots(
                session, snapshots,
                window_start=now - timedelta(hours=self.settings.adaptive_refresh_minutes / 60 * 24),
                window_end=now,
            )
        self.stats.adaptive_weights = weights
        if weights:
            logger.info("adaptive weights refreshed: {}", weights)
        return weights

    def reload_strategies_from_db(self) -> int:
        """Загрузить активные StrategyConfig из БД, заменить self.strategies.

        Если конфигов в БД нет — оставляем то, что построено по settings.strategies.
        Возвращает количество стратегий после загрузки.
        """
        from ..strategies.registry import build_strategies_from_db

        with session_scope() as session:
            db_strategies = build_strategies_from_db(session)
        if db_strategies:
            # сохраним base name для regime preferences
            for s in db_strategies:
                if not getattr(s, "_base_name", None):
                    s._base_name = s.name.split("__")[0] if "__" in s.name else s.name
            self.strategies = db_strategies
            self.stats.last_strategy_refresh_at = datetime.now(timezone.utc)
            logger.info("loaded {} strategies from DB", len(db_strategies))
        return len(self.strategies)

    # --------------------------------------------------------------- public
    def status(self) -> BotStatus:
        daily_pnl = self.stats.last_equity - self.stats.daily_start_equity
        daily_pnl_pct = (
            daily_pnl / self.stats.daily_start_equity * 100
            if self.stats.daily_start_equity > 0 else 0.0
        )
        return BotStatus(
            mode=self.settings.mode,
            running=self.running,
            paused=self.stats.paused,
            kill_switch=self.stats.kill_switch,
            exchange=self.settings.exchange_id,
            symbols=list(self.settings.symbols),
            timeframe=self.settings.timeframe,
            strategies=[s.name for s in self.strategies],
            started_at=self.stats.started_at,
            last_tick_at=self.stats.last_tick_at,
            last_error=self.stats.last_error,
            equity=self.stats.last_equity,
            cash=self.stats.last_cash,
            positions_value=self.stats.last_positions_value,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
        )


_engine: TradeEngine | None = None


def get_engine() -> TradeEngine:
    global _engine
    if _engine is None:
        _engine = TradeEngine()
    return _engine


def set_engine(engine: TradeEngine | None) -> None:
    global _engine
    _engine = engine
