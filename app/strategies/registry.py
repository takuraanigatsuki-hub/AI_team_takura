from __future__ import annotations

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


def available_strategies() -> list[str]:
    return list(_REGISTRY.keys())


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
