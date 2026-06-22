from __future__ import annotations

from ..models.schemas import StrategyVote
from .base import Strategy, StrategyContext
from .indicators import bollinger_bands


class BollingerBreakoutStrategy(Strategy):
    """Пробой полос Боллинджера в сторону движения."""

    name = "bollinger_breakout"

    def __init__(self, period: int = 20, num_std: float = 2.0) -> None:
        super().__init__(period=period, num_std=num_std)
        self.period = int(period)
        self.num_std = float(num_std)

    def warmup_candles(self) -> int:
        return max(self.period * 3, 60)

    def evaluate(self, ctx: StrategyContext) -> StrategyVote:
        df = ctx.candles
        if len(df) < self.warmup_candles():
            return StrategyVote(name=self.name, action="hold", confidence=0.0,
                                reason="недостаточно данных")
        close = df["close"]
        lower, mid, upper = bollinger_bands(close, self.period, self.num_std)
        last_close = float(close.iloc[-1])
        last_upper = float(upper.iloc[-1])
        last_lower = float(lower.iloc[-1])
        last_mid = float(mid.iloc[-1])
        width = max(last_upper - last_lower, 1e-9)

        if last_close > last_upper:
            distance = (last_close - last_upper) / width
            return StrategyVote(
                name=self.name,
                action="buy",
                confidence=float(min(1.0, 0.5 + distance * 5)),
                reason=f"пробой верхней полосы Боллинджера (close={last_close:.2f} > upper={last_upper:.2f})",
            )
        if last_close < last_lower:
            distance = (last_lower - last_close) / width
            return StrategyVote(
                name=self.name,
                action="sell",
                confidence=float(min(1.0, 0.5 + distance * 5)),
                reason=f"пробой нижней полосы Боллинджера (close={last_close:.2f} < lower={last_lower:.2f})",
            )
        # Возврат к средней — слабый hold-сигнал
        offset = abs(last_close - last_mid) / width
        return StrategyVote(
            name=self.name, action="hold", confidence=float(min(0.4, offset)),
            reason="цена внутри полос Боллинджера",
        )
