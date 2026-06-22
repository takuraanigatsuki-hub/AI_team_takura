from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ExchangeError(RuntimeError):
    pass


@dataclass
class OrderResult:
    order_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    fee: float
    timestamp: int


class BaseExchange(ABC):
    """Минимальный контракт биржи, который использует торговый движок."""

    mode: str = "paper"

    @abstractmethod
    async def fetch_ohlcv(
        self, symbol: str, timeframe: str = "15m", limit: int = 200
    ) -> list[list[float]]:
        """Вернуть OHLCV-свечи [[ts, o, h, l, c, v], ...]."""

    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> float:
        """Текущая последняя цена."""

    @abstractmethod
    async def fetch_balance(self) -> dict[str, dict[str, float]]:
        """{ASSET: {'free': x, 'used': y, 'total': z}}"""

    @abstractmethod
    async def create_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> OrderResult:
        """Разместить рыночный ордер (купить/продать на заданное количество базового актива)."""

    async def close(self) -> None:  # noqa: B027 - optional override
        return None
