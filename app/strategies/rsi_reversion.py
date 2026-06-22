from __future__ import annotations

from ..models.schemas import StrategyVote
from .base import Strategy, StrategyContext
from .indicators import rsi


class RSIReversionStrategy(Strategy):
    """Mean-reversion на основе RSI: перепродан → buy, перекуплен → sell."""

    name = "rsi_reversion"

    def __init__(
        self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0
    ) -> None:
        super().__init__(period=period, oversold=oversold, overbought=overbought)
        self.period = int(period)
        self.oversold = float(oversold)
        self.overbought = float(overbought)

    def warmup_candles(self) -> int:
        return max(self.period * 4, 60)

    def evaluate(self, ctx: StrategyContext) -> StrategyVote:
        df = ctx.candles
        if len(df) < self.warmup_candles():
            return StrategyVote(name=self.name, action="hold", confidence=0.0,
                                reason="недостаточно данных")

        values = rsi(df["close"], self.period)
        last = float(values.iloc[-1])

        if last <= self.oversold:
            distance = (self.oversold - last) / max(self.oversold, 1.0)
            return StrategyVote(
                name=self.name,
                action="buy",
                confidence=float(min(1.0, 0.5 + distance)),
                reason=f"RSI={last:.1f} <= {self.oversold} — перепроданность",
            )
        if last >= self.overbought:
            distance = (last - self.overbought) / max(100 - self.overbought, 1.0)
            return StrategyVote(
                name=self.name,
                action="sell",
                confidence=float(min(1.0, 0.5 + distance)),
                reason=f"RSI={last:.1f} >= {self.overbought} — перекупленность",
            )
        return StrategyVote(
            name=self.name, action="hold", confidence=0.2,
            reason=f"RSI={last:.1f} в нейтральной зоне",
        )
