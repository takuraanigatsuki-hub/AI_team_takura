from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..exchange.base import ExchangeError
from .deps import AuthDep, EngineDep


router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/ticker/{symbol_base}/{symbol_quote}")
async def ticker(symbol_base: str, symbol_quote: str, engine: EngineDep, _auth: AuthDep):
    symbol = f"{symbol_base.upper()}/{symbol_quote.upper()}"
    try:
        price = await engine.exchange.fetch_ticker(symbol)
    except ExchangeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"symbol": symbol, "price": price}


@router.get("/ohlcv/{symbol_base}/{symbol_quote}")
async def ohlcv(
    symbol_base: str,
    symbol_quote: str,
    engine: EngineDep,
    _auth: AuthDep,
    timeframe: str = Query("15m"),
    limit: int = Query(100, ge=10, le=500),
):
    symbol = f"{symbol_base.upper()}/{symbol_quote.upper()}"
    try:
        rows = await engine.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except ExchangeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "candles": [
            {"ts": r[0], "open": r[1], "high": r[2], "low": r[3],
             "close": r[4], "volume": r[5]}
            for r in rows
        ],
    }


@router.get("/settings")
async def market_settings(engine: EngineDep, _auth: AuthDep):
    return {
        "exchange": engine.settings.exchange_id,
        "quote_currency": engine.settings.quote_currency,
        "symbols": engine.settings.symbols,
        "timeframe": engine.settings.timeframe,
        "mode": engine.settings.mode,
        "strategies": [s.name for s in engine.strategies],
    }
