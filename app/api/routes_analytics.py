from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

import pandas as pd

from ..analytics import (
    compute_portfolio_factors,
    compute_portfolio_risk,
    compute_returns,
    monte_carlo_var,
    run_stress_tests,
)
from ..exchange.base import ExchangeError
from ..models.db import Position
from ..news.feeds import get_news_service
from ..optimizer import max_sharpe, min_variance, risk_parity
from ..sentiment import aggregate_sentiment
from sqlalchemy import select
from .deps import AuthDep, EngineDep, SessionDep


router = APIRouter(prefix="/api", tags=["analytics"])


# ---------------------------- helpers --------------------------------------

async def _fetch_returns_matrix(
    engine,
    symbols: list[str],
    timeframe: str,
    candles: int,
) -> tuple[pd.DataFrame, dict[str, float]]:
    """Скачать OHLCV для каждого символа и собрать матрицу лог-доходностей.

    Возвращает (returns DataFrame, current_prices dict).
    """
    series: dict[str, pd.Series] = {}
    prices: dict[str, float] = {}
    for symbol in symbols:
        try:
            rows = await engine.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=candles)
        except ExchangeError as exc:
            raise HTTPException(status_code=502, detail=f"{symbol}: {exc}") from exc
        if not rows:
            continue
        df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
        df.set_index("ts", inplace=True)
        series[symbol] = df["close"]
        prices[symbol] = float(df["close"].iloc[-1])
    returns = compute_returns(series)
    return returns, prices


def _periods_per_year(timeframe: str) -> int:
    table = {
        "1m": 525_600, "3m": 175_200, "5m": 105_120, "15m": 35_040,
        "30m": 17_520, "1h": 8_760, "2h": 4_380, "4h": 2_190,
        "6h": 1_460, "12h": 730, "1d": 365,
    }
    return table.get(timeframe, 365)


async def _holdings_value(engine, session) -> dict[str, float]:
    """Текущая стоимость каждой открытой позиции в котировочной валюте."""
    rows = session.execute(
        select(Position).where(Position.quantity > 0)
    ).scalars().all()
    out: dict[str, float] = {}
    for row in rows:
        try:
            price = await engine.exchange.fetch_ticker(row.symbol)
        except ExchangeError:
            continue
        out[row.symbol] = float(row.quantity) * float(price)
    return out


# ---------------------------- risk endpoints --------------------------------

@router.get("/analytics/risk")
async def risk(
    engine: EngineDep,
    _auth: AuthDep,
    timeframe: str = Query("1h"),
    candles: int = Query(500, ge=50, le=1500),
    var_alpha: float = Query(0.05, gt=0.0, lt=0.5),
):
    """Полная картина риска текущего портфеля + VaR/CVaR/β/корреляции/contributions."""
    symbols = engine.settings.symbols
    returns, prices = await _fetch_returns_matrix(engine, symbols, timeframe, candles)
    if returns.empty:
        return {"error": "no returns data"}

    from sqlalchemy import select
    from ..core.database import session_scope
    from ..models.db import Position

    with session_scope() as session:
        rows = session.execute(
            select(Position).where(Position.quantity > 0)
        ).scalars().all()
        holdings = {r.symbol: float(r.quantity) for r in rows}

    if holdings:
        weights = {}
        total_val = 0.0
        for sym, qty in holdings.items():
            v = qty * prices.get(sym, 0.0)
            weights[sym] = v
            total_val += v
        if total_val > 0:
            weights = {k: v / total_val for k, v in weights.items()}
        # символы без позиций — нулевой вес
        for s in symbols:
            weights.setdefault(s, 0.0)
    else:
        weights = None  # equal-weight

    risk = compute_portfolio_risk(
        returns, weights,
        periods_per_year=_periods_per_year(timeframe),
        var_alpha=var_alpha,
    )
    return risk.as_dict()


@router.get("/analytics/monte_carlo")
async def monte_carlo(
    engine: EngineDep,
    _auth: AuthDep,
    timeframe: str = Query("1h"),
    candles: int = Query(500, ge=50, le=1500),
    n_simulations: int = Query(10_000, ge=500, le=200_000),
    horizon: int = Query(1, ge=1, le=30),
    var_alpha: float = Query(0.05, gt=0.0, lt=0.5),
):
    """Monte Carlo VaR/CVaR из multivariate normal под текущую ковариацию."""
    from sqlalchemy import select
    from ..core.database import session_scope
    from ..models.db import Position

    symbols = engine.settings.symbols
    returns, prices = await _fetch_returns_matrix(engine, symbols, timeframe, candles)
    if returns.empty:
        raise HTTPException(status_code=400, detail="no returns data")

    with session_scope() as session:
        rows = session.execute(
            select(Position).where(Position.quantity > 0)
        ).scalars().all()
        holdings = {r.symbol: float(r.quantity) for r in rows}

    if holdings:
        weights_val: dict[str, float] = {}
        total = 0.0
        for sym, qty in holdings.items():
            v = qty * prices.get(sym, 0.0)
            weights_val[sym] = v
            total += v
        weights = {k: v / total for k, v in weights_val.items()} if total > 0 else {}
        for s in symbols:
            weights.setdefault(s, 0.0)
    else:
        weights = {s: 1.0 / len(symbols) for s in symbols}

    result = monte_carlo_var(
        returns, weights,
        n_simulations=n_simulations,
        horizon=horizon,
        var_alpha=var_alpha,
    )
    return result.as_dict()


@router.get("/analytics/factors")
async def factors(
    engine: EngineDep,
    _auth: AuthDep,
    timeframe: str = Query("1h"),
    candles: int = Query(500, ge=50, le=1500),
):
    """Факторное разложение: BTC β, ETH β, momentum, volatility per asset + портфельно."""
    from sqlalchemy import select
    from ..core.database import session_scope
    from ..models.db import Position

    symbols = engine.settings.symbols
    returns, prices = await _fetch_returns_matrix(engine, symbols, timeframe, candles)
    if returns.empty:
        raise HTTPException(status_code=400, detail="no returns data")

    with session_scope() as session:
        rows = session.execute(
            select(Position).where(Position.quantity > 0)
        ).scalars().all()
        holdings = {r.symbol: float(r.quantity) for r in rows}

    if holdings:
        weights_val: dict[str, float] = {}
        total = 0.0
        for sym, qty in holdings.items():
            v = qty * prices.get(sym, 0.0)
            weights_val[sym] = v
            total += v
        weights = {k: v / total for k, v in weights_val.items()} if total > 0 else {
            s: 1.0 / len(symbols) for s in symbols
        }
    else:
        weights = {s: 1.0 / len(symbols) for s in symbols}

    res = compute_portfolio_factors(returns, weights)
    return res.as_dict()


@router.get("/analytics/stress")
async def stress(
    engine: EngineDep,
    session: SessionDep,
    _auth: AuthDep,
):
    holdings = await _holdings_value(engine, session)
    return [r.__dict__ for r in run_stress_tests(holdings)]


# ---------------------------- optimizer endpoints --------------------------

@router.get("/optimizer/{method}")
async def optimize(
    method: str,
    engine: EngineDep,
    _auth: AuthDep,
    timeframe: str = Query("1h"),
    candles: int = Query(500, ge=50, le=1500),
    w_min: float = Query(0.0, ge=0.0, le=1.0),
    w_max: float = Query(1.0, ge=0.0, le=1.0),
    risk_free: float = Query(0.0, ge=0.0, le=1.0),
):
    if method not in {"max_sharpe", "min_variance", "risk_parity"}:
        raise HTTPException(status_code=404, detail="unknown method")
    symbols = engine.settings.symbols
    returns, _ = await _fetch_returns_matrix(engine, symbols, timeframe, candles)
    if returns.empty:
        raise HTTPException(status_code=400, detail="no returns data")
    ppy = _periods_per_year(timeframe)
    if method == "max_sharpe":
        res = max_sharpe(returns, periods_per_year=ppy, w_min=w_min, w_max=w_max, risk_free=risk_free)
    elif method == "min_variance":
        res = min_variance(returns, periods_per_year=ppy, w_min=w_min, w_max=w_max, risk_free=risk_free)
    else:
        res = risk_parity(returns, periods_per_year=ppy, risk_free=risk_free)
    return res.as_dict()


# ---------------------------- sentiment endpoint ---------------------------

@router.get("/sentiment")
async def sentiment(
    engine: EngineDep,
    _auth: AuthDep,
    limit: int = Query(50, ge=5, le=200),
    max_age_hours: int = Query(48, ge=1, le=240),
):
    items = await get_news_service().fetch(limit=limit)
    payload = [
        {
            "title": i.title, "summary": i.summary, "source": i.source,
            "published_at": i.published_at.isoformat() if i.published_at else None,
        }
        for i in items
    ]
    agg = aggregate_sentiment(payload, symbols=engine.settings.symbols,
                              max_age_hours=max_age_hours)
    return [v.as_dict() for v in agg.values()]
