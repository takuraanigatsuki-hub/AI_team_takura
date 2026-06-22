from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class Order(Base):
    """Сделанный (или сэмулированный) ордер."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exchange_order_id: Mapped[str] = mapped_column(String(128), default="", index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))  # buy | sell
    type: Mapped[str] = mapped_column(String(16), default="market")  # market | limit
    quantity: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    fee: Mapped[float] = mapped_column(Float, default=0.0)
    quote_amount: Mapped[float] = mapped_column(Float, default=0.0)  # qty * price
    mode: Mapped[str] = mapped_column(String(8), default="paper")  # paper | live
    status: Mapped[str] = mapped_column(String(16), default="filled")
    reason: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )


class Position(Base):
    """Открытая (или закрытая) позиция, агрегированная по символу."""

    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0)
    avg_entry_price: Mapped[float] = mapped_column(Float, default=0.0)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    stop_loss: Mapped[float] = mapped_column(Float, default=0.0)
    take_profit: Mapped[float] = mapped_column(Float, default=0.0)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EquityPoint(Base):
    """Снимок капитала во времени — для equity curve."""

    __tablename__ = "equity_points"
    __table_args__ = (Index("ix_equity_ts", "ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    cash: Mapped[float] = mapped_column(Float, default=0.0)
    positions_value: Mapped[float] = mapped_column(Float, default=0.0)
    equity: Mapped[float] = mapped_column(Float, default=0.0)
    mode: Mapped[str] = mapped_column(String(8), default="paper")


class DecisionLog(Base):
    """Аудит-лог: что бот увидел и почему принял решение."""

    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    action: Mapped[str] = mapped_column(String(16))  # buy | sell | hold | skip
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    strategies: Mapped[str] = mapped_column(Text, default="")  # JSON-строка с разбивкой
    reason: Mapped[str] = mapped_column(Text, default="")
    mode: Mapped[str] = mapped_column(String(8), default="paper")


class StrategyConfig(Base):
    """Конфигурация конкретного экземпляра стратегии (база + параметры).

    Параметры — JSON. Базовая стратегия (`base`) обязана быть в реестре
    `app/strategies/registry.py::STRATEGY_FACTORIES`. Никакой исполняемый код
    в БД не хранится — это критическое safety-свойство.
    """

    __tablename__ = "strategy_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(96), unique=True, index=True)
    base: Mapped[str] = mapped_column(String(64), index=True)
    params: Mapped[str] = mapped_column(Text, default="{}")  # JSON-словарь параметров
    enabled: Mapped[int] = mapped_column(Integer, default=1)  # 1/0 — для активации
    created_by: Mapped[str] = mapped_column(String(16), default="user")  # user|tuner|llm
    backtest_score: Mapped[float] = mapped_column(Float, default=0.0)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class StrategyPerformance(Base):
    """Snapshot производительности конкретной стратегии за окно."""

    __tablename__ = "strategy_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    strategy_name: Mapped[str] = mapped_column(String(96), index=True)
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, default=0)
    decisive_votes: Mapped[int] = mapped_column(Integer, default=0)
    accuracy: Mapped[float] = mapped_column(Float, default=0.0)  # доля «правильных» решений
    attributable_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    avg_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    weight: Mapped[float] = mapped_column(Float, default=1.0)  # назначенный после анализа вес
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )


class BotState(Base):
    """Ключ-значение для рантайм-флагов (running / paused / kill-switch / итд)."""

    __tablename__ = "bot_state"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AgentMemo(Base):
    """Memo, написанное агентом самому себе в результате периодической рефлексии.

    Самая лёгкая форма «обучения без ML»: после N циклов агент перечитывает
    собственный дневник + результаты сделок, формулирует уроки и кладёт сюда.
    На следующих циклах memo подмешивается в его контекст.
    """

    __tablename__ = "agent_memos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    summary: Mapped[str] = mapped_column(Text, default="")  # 1-3 предложения, что выяснилось
    rules_learned: Mapped[str] = mapped_column(Text, default="")  # JSON: список конкретных правил
    journal_entries_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    orders_reviewed: Mapped[int] = mapped_column(Integer, default=0)
    realized_pnl_window: Mapped[float] = mapped_column(Float, default=0.0)
    mode: Mapped[str] = mapped_column(String(8), default="paper")


class AgentJournal(Base):
    """Дневник автономного LLM-агента — что он подумал и сделал на каждом шаге."""

    __tablename__ = "agent_journal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ts: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    thesis: Mapped[str] = mapped_column(Text, default="")  # короткое резюме рассуждений
    actions: Mapped[str] = mapped_column(Text, default="")  # JSON: список запрошенных действий
    executed: Mapped[str] = mapped_column(Text, default="")  # JSON: что в итоге исполнилось
    market_view: Mapped[str] = mapped_column(Text, default="")  # JSON: снимок рынка/портфеля
    error: Mapped[str] = mapped_column(Text, default="")
    mode: Mapped[str] = mapped_column(String(8), default="paper")
