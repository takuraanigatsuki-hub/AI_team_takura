"""Auto-tuner: walk-forward random-search по параметрам базовых стратегий.

Алгоритм:
  1. Качаем N свечей с биржи (settings.tuner_history_candles).
  2. Делим на K фолдов (walk-forward).
  3. Для каждой базовой стратегии генерируем K случайных конфигов.
  4. На каждом фолде запускаем бэктест каждого конфига.
  5. Итоговый score = средний PnL по out-of-sample фолдам.
  6. Лучшие top_n сохраняем как StrategyConfig (created_by='tuner').

Никакой исполняемый код в БД не пишется — только параметры внутри строго
описанных диапазонов из STRATEGY_FACTORIES.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sqlalchemy import select

from ..core.config import Settings, get_settings
from ..core.database import session_scope
from ..core.logging import logger
from ..engine.backtest import run_backtest
from ..engine.trader import get_engine
from ..exchange.base import ExchangeError
from ..models.db import StrategyConfig
from ..strategies.registry import (
    ParamSchema,
    STRATEGY_FACTORIES,
    build_strategy_from_config,
)


@dataclass
class TunerCandidate:
    base: str
    params: dict
    score: float
    folds: int


def _sample_params(schemas: list[ParamSchema], rng: np.random.Generator) -> dict:
    out: dict = {}
    for s in schemas:
        if s.kind == "int":
            out[s.name] = int(rng.integers(int(s.low), int(s.high) + 1))
        else:
            out[s.name] = float(rng.uniform(s.low, s.high))
    return out


def _enforce_constraints(base: str, params: dict) -> bool:
    """Проверить параметрические constraints, специфичные для базы."""
    if base == "ma_crossover":
        return params.get("slow", 26) > params.get("fast", 12) + 2
    if base == "rsi_reversion":
        return params.get("overbought", 70) > params.get("oversold", 30) + 15
    return True


async def _fetch_candles(symbol: str, timeframe: str, limit: int) -> pd.DataFrame:
    engine = get_engine()
    try:
        rows = await engine.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except ExchangeError as exc:
        logger.warning("tuner fetch_ohlcv {} failed: {}", symbol, exc)
        return pd.DataFrame()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df.set_index("ts", inplace=True)
    return df


def _score_candidate(
    candidate_base: str,
    candidate_params: dict,
    candles: pd.DataFrame,
    folds: int,
    settings: Settings,
    symbol: str,
) -> tuple[float, int]:
    """Усреднённый PnL по walk-forward фолдам."""
    if candles.empty or len(candles) < 100:
        return 0.0, 0
    instance = build_strategy_from_config(candidate_base, f"{candidate_base}__tune", candidate_params)
    if instance is None:
        return 0.0, 0
    n = len(candles)
    fold_size = max(80, n // folds)
    scores: list[float] = []
    for i in range(folds):
        start = max(0, n - fold_size * (folds - i))
        end = min(n, n - fold_size * (folds - i - 1)) if i < folds - 1 else n
        fold = candles.iloc[start:end]
        if len(fold) < instance.warmup_candles() + 5:
            continue
        local_settings = settings.model_copy(update={
            "signal_consensus": 1,
            "max_open_positions": 1,
            "risk_per_trade": 0.2,
            "min_order_notional": 1,
        })
        res = run_backtest(
            fold, [instance], local_settings, symbol=symbol,
            starting_balance=10_000.0,
        )
        scores.append(res.pnl_pct)
    if not scores:
        return 0.0, 0
    return float(sum(scores) / len(scores)), len(scores)


async def run_tuning_cycle(
    settings: Settings | None = None,
    *,
    symbol: str | None = None,
    samples_per_strategy: int | None = None,
    keep_top_n: int | None = None,
    seed: int | None = None,
) -> list[TunerCandidate]:
    """Один цикл подбора параметров. Возвращает список сохранённых лучших."""
    s = settings or get_settings()
    symbol = symbol or (s.symbols[0] if s.symbols else "BTC/USDT")
    samples = samples_per_strategy or s.tuner_samples_per_strategy
    keep = keep_top_n if keep_top_n is not None else s.tuner_keep_top_n
    rng = np.random.default_rng(seed)

    candles = await _fetch_candles(symbol, s.tuner_history_timeframe, s.tuner_history_candles)
    if candles.empty:
        logger.warning("tuner: no candles for {}", symbol)
        return []

    best: list[TunerCandidate] = []
    for base, factory in STRATEGY_FACTORIES.items():
        tried: list[TunerCandidate] = []
        for _ in range(samples):
            params = _sample_params(factory.params, rng)
            if not _enforce_constraints(base, params):
                continue
            score, folds = await asyncio.to_thread(
                _score_candidate, base, params, candles, s.tuner_walk_forward_folds, s, symbol
            )
            if folds == 0:
                continue
            tried.append(TunerCandidate(base=base, params=params, score=score, folds=folds))
        tried.sort(key=lambda c: c.score, reverse=True)
        best.extend(tried[:keep])

    # сохраним в БД
    saved_at = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    with session_scope() as session:
        for cand in best:
            param_str = ",".join(f"{k}={v}" for k, v in sorted(cand.params.items()))
            name = f"{cand.base}__tune_{saved_at}_{abs(hash(param_str)) % 10000:04d}"
            # уже есть такая комбинация?
            existing = session.execute(
                select(StrategyConfig).where(StrategyConfig.name == name)
            ).scalar_one_or_none()
            if existing is not None:
                existing.params = json.dumps(cand.params, ensure_ascii=False)
                existing.backtest_score = cand.score
                existing.note = f"walk-forward folds={cand.folds}, score={cand.score:+.2f}%"
                existing.enabled = 1
                continue
            session.add(StrategyConfig(
                name=name, base=cand.base,
                params=json.dumps(cand.params, ensure_ascii=False),
                enabled=1, created_by="tuner",
                backtest_score=cand.score,
                note=f"walk-forward folds={cand.folds}, score={cand.score:+.2f}%",
            ))

    if best:
        logger.info(
            "tuner saved {} configs; best score {:+.2f}% ({})",
            len(best), best[0].score, best[0].base,
        )
    return best


async def tuner_loop(settings: Settings | None = None) -> None:
    """Вечный цикл автотюнера."""
    s = settings or get_settings()
    if not s.tuner_enabled:
        return
    interval = max(3600, s.tuner_interval_hours * 3600)
    # первый цикл — спустя 5 минут после старта (дать engine'у инициализироваться)
    await asyncio.sleep(min(300, interval))
    while True:
        try:
            await run_tuning_cycle(s)
        except Exception as exc:  # noqa: BLE001
            logger.exception("tuner cycle failed: {}", exc)
        await asyncio.sleep(interval)
