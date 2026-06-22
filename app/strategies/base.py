from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

from ..models.schemas import StrategyVote


@dataclass
class StrategyContext:
    symbol: str
    timeframe: str
    candles: pd.DataFrame  # columns: open, high, low, close, volume; index = ts (ms)
    position_quantity: float = 0.0
    extra: dict | None = None


class Strategy(ABC):
    name: str = "base"

    def __init__(self, **params) -> None:
        self.params = params

    @abstractmethod
    def evaluate(self, ctx: StrategyContext) -> StrategyVote:
        """Принять решение по одному символу."""

    def warmup_candles(self) -> int:
        """Минимум свечей, нужный для адекватной работы."""
        return 50
