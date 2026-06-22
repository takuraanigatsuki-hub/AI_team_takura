from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any

from .base import BaseExchange, ExchangeError, OrderResult


class PaperExchange(BaseExchange):
    """In-memory paper trading: реальные цены, виртуальные деньги.

    Берёт OHLCV / тикеры с реальной биржи через переданный data-источник
    (любой объект с теми же методами `fetch_ohlcv` / `fetch_ticker`).
    """

    mode = "paper"

    DEFAULT_FEE_RATE = 0.001  # 0.1% taker

    def __init__(
        self,
        data_source: BaseExchange,
        quote_currency: str = "USDT",
        starting_balance: float = 10_000.0,
        fee_rate: float | None = None,
    ) -> None:
        self.data_source = data_source
        self.quote = quote_currency.upper()
        self.fee_rate = fee_rate if fee_rate is not None else self.DEFAULT_FEE_RATE
        self._balances: dict[str, float] = {self.quote: float(starting_balance)}
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self.data_source.close()

    async def fetch_ohlcv(
        self, symbol: str, timeframe: str = "15m", limit: int = 200
    ) -> list[list[float]]:
        return await self.data_source.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    async def fetch_ticker(self, symbol: str) -> float:
        return await self.data_source.fetch_ticker(symbol)

    async def fetch_balance(self) -> dict[str, dict[str, float]]:
        async with self._lock:
            return {
                asset: {"free": amount, "used": 0.0, "total": amount}
                for asset, amount in self._balances.items()
            }

    async def create_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> OrderResult:
        side = side.lower()
        if side not in ("buy", "sell"):
            raise ExchangeError(f"invalid side '{side}'")
        if quantity <= 0:
            raise ExchangeError("quantity must be positive")

        price = await self.fetch_ticker(symbol)
        if price <= 0:
            raise ExchangeError(f"invalid price for {symbol}: {price}")

        base, quote = _split_symbol(symbol)
        if quote.upper() != self.quote:
            raise ExchangeError(
                f"symbol {symbol} quote {quote} != paper quote {self.quote}"
            )

        notional = quantity * price
        fee = notional * self.fee_rate

        async with self._lock:
            if side == "buy":
                total_cost = notional + fee
                cash = self._balances.get(self.quote, 0.0)
                if cash + 1e-9 < total_cost:
                    raise ExchangeError(
                        f"insufficient {self.quote}: need {total_cost:.4f}, have {cash:.4f}"
                    )
                self._balances[self.quote] = cash - total_cost
                self._balances[base] = self._balances.get(base, 0.0) + quantity
            else:  # sell
                base_balance = self._balances.get(base, 0.0)
                if base_balance + 1e-12 < quantity:
                    raise ExchangeError(
                        f"insufficient {base}: need {quantity:.8f}, have {base_balance:.8f}"
                    )
                self._balances[base] = base_balance - quantity
                proceeds = notional - fee
                self._balances[self.quote] = self._balances.get(self.quote, 0.0) + proceeds

        return OrderResult(
            order_id=f"paper-{uuid.uuid4().hex[:12]}",
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            fee=fee,
            timestamp=int(time.time() * 1000),
        )

    def snapshot_balances(self) -> dict[str, float]:
        return dict(self._balances)

    def credit(self, asset: str, amount: float) -> None:
        self._balances[asset.upper()] = self._balances.get(asset.upper(), 0.0) + amount


def _split_symbol(symbol: str) -> tuple[str, str]:
    if "/" in symbol:
        base, quote = symbol.split("/", 1)
        return base.upper(), quote.upper()
    # Fallback for symbols like "BTCUSDT"
    s = symbol.upper()
    for q in ("USDT", "USDC", "USD", "BUSD", "EUR", "BTC", "ETH"):
        if s.endswith(q) and len(s) > len(q):
            return s[: -len(q)], q
    raise ExchangeError(f"cannot split symbol {symbol}")
