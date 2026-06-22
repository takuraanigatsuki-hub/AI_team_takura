from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..engine.backtest import run_backtest
from ..exchange.base import ExchangeError
from ..strategies import available_strategies, build_strategies
from .deps import AuthDep, EngineDep


router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("/")
def list_strategies(_auth: AuthDep):
    return {"available": available_strategies()}


@router.post("/backtest")
async def backtest(
    engine: EngineDep,
    _auth: AuthDep,
    symbol_base: str = Query(...),
    symbol_quote: str = Query(...),
    timeframe: str = Query("1h"),
    limit: int = Query(500, ge=100, le=1500),
    starting_balance: float = Query(10_000.0, gt=0),
    strategies: list[str] | None = Query(default=None),
):
    symbol = f"{symbol_base.upper()}/{symbol_quote.upper()}"
    try:
        rows = await engine.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except ExchangeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if not rows:
        raise HTTPException(status_code=404, detail="no historical data")

    import pandas as pd

    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df.set_index("ts", inplace=True)

    names = strategies or engine.settings.strategies
    strats = build_strategies(names)
    if not strats:
        raise HTTPException(status_code=400, detail="no valid strategies")

    result = run_backtest(
        candles=df,
        strategies=strats,
        settings=engine.settings,
        symbol=symbol,
        starting_balance=starting_balance,
    )
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "starting_balance": result.starting_balance,
        "final_equity": result.final_equity,
        "pnl": result.pnl,
        "pnl_pct": result.pnl_pct,
        "num_trades": result.num_trades,
        "trades": [
            {"side": t.side, "ts": t.timestamp, "price": t.price,
             "quantity": t.quantity, "reason": t.reason}
            for t in result.trades
        ],
        "equity_curve": [{"ts": ts, "equity": eq} for ts, eq in result.equity_curve],
    }
