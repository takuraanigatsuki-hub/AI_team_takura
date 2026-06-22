"""Реестр стратегий + параметризуемые фабрики для DynamicStrategy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base import Strategy
from .bollinger_breakout import BollingerBreakoutStrategy
from .llm_advisor import LLMAdvisorStrategy
from .ma_crossover import MACrossoverStrategy
from .rsi_reversion import RSIReversionStrategy


_REGISTRY: dict[str, type[Strategy]] = {
    MACrossoverStrategy.name: MACrossoverStrategy,
    RSIReversionStrategy.name: RSIReversionStrategy,
    BollingerBreakoutStrategy.name: BollingerBreakoutStrategy,
    LLMAdvisorStrategy.name: LLMAdvisorStrategy,
}


@dataclass
class ParamSchema:
    """Описание одного параметра стратегии."""
    name: str
    kind: str  # "int" | "float"
    low: float
    high: float
    default: float


@dataclass
class StrategyFactory:
    base_name: str
    cls: type[Strategy]
    params: list[ParamSchema]


# Фабрики с допустимыми диапазонами параметров — используются tuner'ом и LLM-proposer'ом.
# Любая попытка вылезти за пределы → params clamping в DynamicStrategy.
STRATEGY_FACTORIES: dict[str, StrategyFactory] = {
    "ma_crossover": StrategyFactory(
        "ma_crossover", MACrossoverStrategy, [
            ParamSchema("fast", "int", 4, 30, 12),
            ParamSchema("slow", "int", 15, 100, 26),
        ],
    ),
    "rsi_reversion": StrategyFactory(
        "rsi_reversion", RSIReversionStrategy, [
            ParamSchema("period", "int", 6, 30, 14),
            ParamSchema("oversold", "float", 15.0, 40.0, 30.0),
            ParamSchema("overbought", "float", 60.0, 85.0, 70.0),
        ],
    ),
    "bollinger_breakout": StrategyFactory(
        "bollinger_breakout", BollingerBreakoutStrategy, [
            ParamSchema("period", "int", 10, 40, 20),
            ParamSchema("num_std", "float", 1.5, 3.5, 2.0),
        ],
    ),
}


def available_strategies() -> list[str]:
    return list(_REGISTRY.keys())


def available_base_strategies() -> list[str]:
    """Только те, что параметризуемы (фабричные) — без llm_advisor."""
    return list(STRATEGY_FACTORIES.keys())


def get_factory(base: str) -> StrategyFactory | None:
    return STRATEGY_FACTORIES.get(base.lower().strip())


def clamp_params(base: str, params: dict[str, Any]) -> dict[str, Any]:
    """Привести параметры к допустимым диапазонам и типам."""
    factory = get_factory(base)
    if factory is None:
        return {}
    out: dict[str, Any] = {}
    for schema in factory.params:
        raw = params.get(schema.name, schema.default)
        try:
            num = float(raw)
        except (TypeError, ValueError):
            num = schema.default
        num = max(schema.low, min(schema.high, num))
        out[schema.name] = int(round(num)) if schema.kind == "int" else float(num)
    return out


def build_strategies(names: list[str]) -> list[Strategy]:
    out: list[Strategy] = []
    seen: set[str] = set()
    for raw in names:
        name = raw.strip().lower()
        if not name or name in seen:
            continue
        seen.add(name)
        cls = _REGISTRY.get(name)
        if cls is None:
            continue
        out.append(cls())
    return out


def build_strategy_from_config(base: str, name: str, params: dict[str, Any]) -> Strategy | None:
    """Создать экземпляр стратегии по конфигу из БД."""
    factory = get_factory(base)
    if factory is None:
        return None
    clean = clamp_params(base, params)
    instance = factory.cls(**clean)
    instance.name = name or base
    return instance


def build_strategies_from_db(session) -> list[Strategy]:
    """Загрузить активные StrategyConfig из БД и собрать набор стратегий.

    Если в БД ни одного конфига — возвращаем None, чтобы вызвавший
    использовал статический список из settings.strategies.
    """
    from sqlalchemy import select
    import json

    from ..models.db import StrategyConfig

    rows = session.execute(
        select(StrategyConfig).where(StrategyConfig.enabled == 1)
        .order_by(StrategyConfig.backtest_score.desc())
    ).scalars().all()
    out: list[Strategy] = []
    for row in rows:
        try:
            params = json.loads(row.params) if row.params else {}
        except json.JSONDecodeError:
            params = {}
        if not isinstance(params, dict):
            params = {}
        instance = build_strategy_from_config(row.base, row.name, params)
        if instance is not None:
            out.append(instance)
    return out
