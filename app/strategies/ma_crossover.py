from __future__ import annotations

from ..models.schemas import StrategyVote
from .base import Strategy, StrategyContext
from .indicators import ema


class MACrossoverStrategy(Strategy):
    """Классический пересечение быстрой и медленной EMA."""

    name = "ma_crossover"

    def __init__(self, fast: int = 12, slow: int = 26) -> None:
        super().__init__(fast=fast, slow=slow)
        self.fast = int(fast)
        self.slow = int(slow)

    def warmup_candles(self) -> int:
        return max(self.slow * 3, 60)

    def evaluate(self, ctx: StrategyContext) -> StrategyVote:
        df = ctx.candles
        if len(df) < self.warmup_candles():
            return StrategyVote(name=self.name, action="hold", confidence=0.0,
                                reason="недостаточно данных")
        close = df["close"]
        f = ema(close, self.fast)
        s = ema(close, self.slow)
        if f.iloc[-1] is None or s.iloc[-1] is None:
            return StrategyVote(name=self.name, action="hold", confidence=0.0,
                                reason="нет значений EMA")

        diff = float(f.iloc[-1] - s.iloc[-1])
        prev_diff = float(f.iloc[-2] - s.iloc[-2])
        rel = abs(diff) / max(close.iloc[-1], 1e-9)
        confidence = float(min(1.0, rel * 50.0))

        if prev_diff <= 0 < diff:
            return StrategyVote(
                name=self.name, action="buy", confidence=max(0.4, confidence),
                reason=f"EMA{self.fast} пересекла EMA{self.slow} снизу вверх",
            )
        if prev_diff >= 0 > diff:
            return StrategyVote(
                name=self.name, action="sell", confidence=max(0.4, confidence),
                reason=f"EMA{self.fast} пересекла EMA{self.slow} сверху вниз",
            )
        # Тренд продолжается — слабый сигнал в сторону тренда
        if diff > 0:
            return StrategyVote(
                name=self.name, action="hold", confidence=confidence * 0.5,
                reason=f"восходящий тренд (EMA{self.fast}>EMA{self.slow})",
            )
        return StrategyVote(
            name=self.name, action="hold", confidence=confidence * 0.5,
            reason=f"нисходящий тренд (EMA{self.fast}<EMA{self.slow})",
        )
