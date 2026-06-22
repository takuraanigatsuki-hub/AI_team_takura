from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SideT = Literal["buy", "sell"]
ActionT = Literal["buy", "sell", "hold", "skip"]
ModeT = Literal["paper", "live"]


class Candle(BaseModel):
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


class Ticker(BaseModel):
    symbol: str
    price: float
    timestamp: int | None = None


class BalanceOut(BaseModel):
    asset: str
    free: float
    used: float
    total: float


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    quantity: float
    avg_entry_price: float
    realized_pnl: float
    stop_loss: float
    take_profit: float
    opened_at: datetime
    updated_at: datetime
    current_price: float | None = None
    market_value: float | None = None
    unrealized_pnl: float | None = None
    unrealized_pnl_pct: float | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    side: SideT
    type: str
    quantity: float
    price: float
    quote_amount: float
    fee: float
    mode: ModeT
    status: str
    reason: str
    created_at: datetime


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: datetime
    symbol: str
    action: ActionT
    confidence: float
    price: float
    strategies: str
    reason: str
    mode: ModeT


class EquityPointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ts: datetime
    cash: float
    positions_value: float
    equity: float
    mode: ModeT


class StrategyVote(BaseModel):
    name: str
    action: ActionT
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = ""


class Signal(BaseModel):
    """Финальный сигнал, агрегированный из голосов стратегий."""

    symbol: str
    action: ActionT
    confidence: float = Field(ge=0.0, le=1.0)
    price: float
    votes: list[StrategyVote] = Field(default_factory=list)
    reason: str = ""


class AgentJournalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ts: datetime
    thesis: str
    actions: str
    executed: str
    market_view: str
    error: str
    mode: ModeT


class NewsItemOut(BaseModel):
    title: str
    link: str
    source: str
    summary: str
    published_at: datetime | None = None


class AgentStatus(BaseModel):
    enabled: bool
    running: bool
    interval_seconds: int
    model: str
    provider: str
    last_run_at: datetime | None = None
    last_error: str | None = None
    cycles: int = 0
    has_api_key: bool = False


class BotStatus(BaseModel):
    mode: ModeT
    running: bool
    paused: bool
    kill_switch: bool
    exchange: str
    symbols: list[str]
    timeframe: str
    strategies: list[str]
    started_at: datetime | None = None
    last_tick_at: datetime | None = None
    last_error: str | None = None
    equity: float
    cash: float
    positions_value: float
    daily_pnl: float
    daily_pnl_pct: float
