from __future__ import annotations

import asyncio
from typing import Any

from .base import BaseExchange, ExchangeError, OrderResult


class CCXTExchange(BaseExchange):
    """Биржа через библиотеку ccxt. Используется и как источник данных,
    и как live-исполнитель (mode='live')."""

    def __init__(
        self,
        exchange_id: str,
        api_key: str = "",
        api_secret: str = "",
        api_password: str = "",
        testnet: bool = False,
        mode: str = "paper",
    ) -> None:
        try:
            import ccxt  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ExchangeError("ccxt not installed; pip install ccxt") from exc

        if not hasattr(ccxt, exchange_id):
            raise ExchangeError(f"unknown ccxt exchange '{exchange_id}'")

        klass = getattr(ccxt, exchange_id)
        params: dict[str, Any] = {"enableRateLimit": True}
        if api_key:
            params["apiKey"] = api_key
        if api_secret:
            params["secret"] = api_secret
        if api_password:
            params["password"] = api_password

        self.client = klass(params)
        self.mode = mode
        self.exchange_id = exchange_id

        if testnet and hasattr(self.client, "set_sandbox_mode"):
            try:
                self.client.set_sandbox_mode(True)
            except Exception as exc:  # pragma: no cover
                raise ExchangeError(f"cannot enable sandbox: {exc}") from exc

    async def _run(self, func, *args, **kwargs):
        # ccxt sync клиент — оборачиваем вызовы в thread pool
        return await asyncio.to_thread(func, *args, **kwargs)

    async def close(self) -> None:
        close = getattr(self.client, "close", None)
        if callable(close):
            try:
                await asyncio.to_thread(close)
            except Exception:
                pass

    async def fetch_ohlcv(
        self, symbol: str, timeframe: str = "15m", limit: int = 200
    ) -> list[list[float]]:
        try:
            data = await self._run(
                self.client.fetch_ohlcv, symbol, timeframe, None, limit
            )
        except Exception as exc:
            raise ExchangeError(f"fetch_ohlcv failed for {symbol}: {exc}") from exc
        return data or []

    async def fetch_ticker(self, symbol: str) -> float:
        try:
            data = await self._run(self.client.fetch_ticker, symbol)
        except Exception as exc:
            raise ExchangeError(f"fetch_ticker failed for {symbol}: {exc}") from exc
        price = data.get("last") or data.get("close") or data.get("bid")
        if price is None:
            raise ExchangeError(f"ticker for {symbol} has no price")
        return float(price)

    async def fetch_balance(self) -> dict[str, dict[str, float]]:
        if self.mode != "live":
            return {}
        try:
            data = await self._run(self.client.fetch_balance)
        except Exception as exc:
            raise ExchangeError(f"fetch_balance failed: {exc}") from exc

        out: dict[str, dict[str, float]] = {}
        totals = data.get("total", {}) or {}
        free = data.get("free", {}) or {}
        used = data.get("used", {}) or {}
        for asset, total in totals.items():
            try:
                t = float(total or 0)
            except (TypeError, ValueError):
                continue
            if t <= 0:
                continue
            out[asset.upper()] = {
                "free": float(free.get(asset, 0) or 0),
                "used": float(used.get(asset, 0) or 0),
                "total": t,
            }
        return out

    async def create_market_order(
        self, symbol: str, side: str, quantity: float
    ) -> OrderResult:
        if self.mode != "live":
            raise ExchangeError(
                "CCXTExchange is in non-live mode; orders disabled. "
                "Use PaperExchange or set MODE=live with API keys."
            )
        try:
            res = await self._run(
                self.client.create_order, symbol, "market", side, quantity
            )
        except Exception as exc:
            raise ExchangeError(f"create_order failed: {exc}") from exc

        price = float(res.get("average") or res.get("price") or 0.0)
        if price <= 0:
            ticker = await self.fetch_ticker(symbol)
            price = ticker
        filled = float(res.get("filled") or res.get("amount") or quantity)
        fee_info = res.get("fee") or {}
        fee_cost = float(fee_info.get("cost") or 0.0)

        return OrderResult(
            order_id=str(res.get("id") or ""),
            symbol=symbol,
            side=side.lower(),
            quantity=filled,
            price=price,
            fee=fee_cost,
            timestamp=int(res.get("timestamp") or 0),
        )
