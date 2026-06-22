"""Genetic algorithm поверх tuner-конфигов.

Берёт top-N родителей (последний результат tuner или существующие
StrategyConfig с лучшим score), генерирует детей через crossover +
mutation, бэктестит, оставляет лучших.

Дополняет random search auto-tuner'а локальным поиском вокруг
обнаруженных островков хорошего score.
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
    STRATEGY_FACTORIES,
    build_strategy_from_config,
    clamp_params,
    get_factory,
)


@dataclass
class GACandidate:
    base: str
    params: dict
    score: float
    generation: int
    parents: tuple[str, str] | None = None


def _crossover(parent_a: dict, parent_b: dict, rng: np.random.Generator) -> dict:
    """Для каждого параметра — выбрать значение от одного из родителей или интерполировать."""
    out: dict = {}
    for k, va in parent_a.items():
        vb = parent_b.get(k, va)
        choice = rng.choice(["a", "b", "interpolate"])
        if choice == "a":
            out[k] = va
        elif choice == "b":
            out[k] = vb
        else:
            mix = float(rng.uniform(0.0, 1.0))
            out[k] = va * (1 - mix) + vb * mix
    return out


def _mutate(base: str, params: dict, rate: float, rng: np.random.Generator) -> dict:
    """Случайно сдвинуть каждый параметр на ±20% от диапазона с вероятностью rate."""
    factory = get_factory(base)
    if factory is None:
        return params
    out = dict(params)
    for schema in factory.params:
        if rng.random() > rate:
            continue
        span = schema.high - schema.low
        delta = float(rng.uniform(-0.2 * span, 0.2 * span))
        cur = out.get(schema.name, schema.default)
        try:
            cur = float(cur)
        except (TypeError, ValueError):
            cur = schema.default
        out[schema.name] = cur + delta
    return clamp_params(base, out)


async def _backtest(base: str, params: dict, candles: pd.DataFrame, settings: Settings, symbol: str) -> float:
    inst = build_strategy_from_config(base, f"{base}__ga_eval", params)
    if inst is None or len(candles) < inst.warmup_candles() + 5:
        return 0.0
    local = settings.model_copy(update={
        "signal_consensus": 1, "max_open_positions": 1,
        "risk_per_trade": 0.2, "min_order_notional": 1,
    })
    res = await asyncio.to_thread(
        run_backtest, candles, [inst], local, symbol, 10_000.0,
    )
    return float(res.pnl_pct)


async def run_genetic_cycle(
    settings: Settings | None = None,
    *,
    symbol: str | None = None,
    seed: int | None = None,
) -> list[GACandidate]:
    s = settings or get_settings()
    if not s.ga_enabled:
        return []
    symbol = symbol or (s.symbols[0] if s.symbols else "BTC/USDT")
    rng = np.random.default_rng(seed)

    # 1) загрузим candles
    engine = get_engine()
    try:
        rows = await engine.exchange.fetch_ohlcv(
            symbol, timeframe=s.tuner_history_timeframe, limit=s.tuner_history_candles
        )
    except ExchangeError as exc:
        logger.warning("GA: fetch_ohlcv {} failed: {}", symbol, exc)
        return []
    if not rows:
        return []
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df.set_index("ts", inplace=True)

    saved_at = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    survivors: list[GACandidate] = []

    for base, factory in STRATEGY_FACTORIES.items():
        # 2) родители: top-K из StrategyConfig этой базы по backtest_score
        with session_scope() as session:
            parents_rows = session.execute(
                select(StrategyConfig)
                .where(StrategyConfig.base == base)
                .order_by(StrategyConfig.backtest_score.desc())
                .limit(max(2, s.ga_population_size // 3))
            ).scalars().all()
            parents = [(c.name, _safe_json_obj(c.params)) for c in parents_rows
                       if isinstance(_safe_json_obj(c.params), dict)]
        if len(parents) < 2:
            # fallback: два дефолтных + одна случайная мутация
            defaults = {p.name: p.default for p in factory.params}
            parents = [("default_a", defaults), ("default_b", defaults)]

        population = [GACandidate(base, dict(p[1]), 0.0, 0, None) for p in parents]

        for gen in range(1, s.ga_generations + 1):
            # 3) скрестить → мутировать → создать поколение
            children: list[GACandidate] = []
            for _ in range(s.ga_population_size):
                a, b = rng.choice(len(parents), size=2, replace=len(parents) < 2)
                pa, pb = parents[int(a)][1], parents[int(b)][1]
                child = _mutate(base, _crossover(pa, pb, rng), s.ga_mutation_rate, rng)
                children.append(GACandidate(
                    base, child, 0.0, gen,
                    parents=(parents[int(a)][0], parents[int(b)][0]),
                ))

            # 4) оценить
            for cand in children:
                cand.score = await _backtest(base, cand.params, df, s, symbol)

            # 5) выбрать лучших как родителей следующего поколения
            children.sort(key=lambda c: c.score, reverse=True)
            keep = max(2, s.ga_population_size // 3)
            parents = [(f"gen{gen}_top{i}", c.params) for i, c in enumerate(children[:keep])]
            population = children[:keep]

        # 6) сохранить топ-N финальных
        for i, cand in enumerate(population[: max(1, s.ga_population_size // 4)]):
            param_str = ",".join(f"{k}={v}" for k, v in sorted(cand.params.items()))
            name = f"{cand.base}__ga_{saved_at}_{abs(hash(param_str)) % 10000:04d}"
            with session_scope() as session:
                existing = session.execute(
                    select(StrategyConfig).where(StrategyConfig.name == name)
                ).scalar_one_or_none()
                if existing is not None:
                    existing.params = json.dumps(cand.params, ensure_ascii=False)
                    existing.backtest_score = cand.score
                    existing.note = f"GA gen={cand.generation} score={cand.score:+.2f}%"
                    existing.enabled = 1 if cand.score > 0 else 0
                else:
                    session.add(StrategyConfig(
                        name=name, base=cand.base,
                        params=json.dumps(cand.params, ensure_ascii=False),
                        enabled=1 if cand.score > 0 else 0,
                        created_by="ga",
                        backtest_score=cand.score,
                        note=f"GA gen={cand.generation} score={cand.score:+.2f}%",
                    ))
            survivors.append(cand)

    if survivors:
        survivors.sort(key=lambda c: c.score, reverse=True)
        logger.info(
            "GA saved {} configs; best score {:+.2f}% ({})",
            len(survivors), survivors[0].score, survivors[0].base,
        )
    return survivors


def _safe_json_obj(text: str):
    try:
        return json.loads(text) if text else {}
    except json.JSONDecodeError:
        return {}


async def ga_loop(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    if not s.ga_enabled:
        return
    interval = max(3600, s.tuner_interval_hours * 3600)
    # стартуем через 20 минут после tuner'а, чтобы у него были родители
    await asyncio.sleep(min(1200, interval))
    while True:
        try:
            await run_genetic_cycle(s)
        except Exception as exc:  # noqa: BLE001
            logger.exception("GA cycle failed: {}", exc)
        await asyncio.sleep(interval)
