"""Thompson Sampling bandit для выбора стратегий.

Каждая стратегия моделируется как Beta(α, β). При каждом «успехе» (голос
совпал с прибыльным финальным сигналом) → α += 1. При «неудаче» → β += 1.

На каждом тике sample(Beta(α, β)) для каждой стратегии → нормализуем →
получаем веса. Это даёт принципиальный explore/exploit:
  • новые стратегии (малое количество samples) имеют широкое распределение
    → шанс получить высокий вес и быть проверенными;
  • устоявшиеся проигрывающие имеют узкое распределение около низкого p
    → почти всегда низкий вес.

Mixed mode: итоговый вес = adaptive_weight * (1 - blend) + bandit_weight * blend.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.db import BanditPosterior, DecisionLog, Order
from .weights import _realized_pnl_per_symbol


@dataclass
class BanditState:
    strategy_name: str
    alpha: float
    beta: float
    samples: int
    mean: float       # ожидание Beta(α,β) = α/(α+β)
    weight: float = 0.0
    last_weight: float = 0.0

    def as_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "alpha": round(self.alpha, 4),
            "beta": round(self.beta, 4),
            "samples": self.samples,
            "mean": round(self.mean, 4),
            "weight": round(self.weight, 4),
        }


def load_bandit_states(session: Session, names: list[str] | None = None) -> dict[str, BanditState]:
    """Прочитать постериоры из БД. Если стратегия отсутствует — Beta(1, 1) prior."""
    if names is None:
        rows = session.execute(select(BanditPosterior)).scalars().all()
    else:
        rows = session.execute(
            select(BanditPosterior).where(BanditPosterior.strategy_name.in_(names))
        ).scalars().all()
    out: dict[str, BanditState] = {}
    for r in rows:
        a, b = max(0.001, r.alpha), max(0.001, r.beta)
        out[r.strategy_name] = BanditState(
            strategy_name=r.strategy_name, alpha=a, beta=b,
            samples=int(r.samples), mean=a / (a + b),
            last_weight=float(r.last_weight),
        )
    if names is not None:
        for n in names:
            out.setdefault(n, BanditState(n, 1.0, 1.0, 0, 0.5))
    return out


def sample_weights(states: dict[str, BanditState], seed: int | None = None) -> dict[str, float]:
    """Sample Beta(α, β) для каждой стратегии и вернуть нормализованные веса."""
    if not states:
        return {}
    rng = np.random.default_rng(seed)
    samples = {}
    for name, st in states.items():
        try:
            samples[name] = float(rng.beta(st.alpha, st.beta))
        except ValueError:
            samples[name] = st.mean
    total = sum(samples.values())
    if total <= 0:
        return {n: 1.0 for n in states}
    n = len(states)
    # масштабируем к average=1 (как делают adaptive_weights)
    return {name: max(0.01, (v / total) * n) for name, v in samples.items()}


def update_bandit_from_history(
    session: Session,
    *,
    lookback: int = 500,
    success_threshold_pct: float = 0.0,
) -> dict[str, BanditState]:
    """Пройти по последним N decisions + сделкам, обновить α, β для каждой стратегии.

    «Успех» определяется так:
      - стратегия проголосовала за `action` (buy/sell);
      - финальный сигнал совпал с её голосом;
      - реализованный P&L по этому символу за окно > порога → α += 1;
        иначе β += 1.

    Симметричная hold-голосование не учитывается (нейтрально).
    """
    decisions = session.execute(
        select(DecisionLog).order_by(DecisionLog.ts.desc()).limit(lookback)
    ).scalars().all()
    if not decisions:
        return {}
    earliest = min(d.ts for d in decisions)
    orders = session.execute(
        select(Order).where(Order.created_at >= earliest)
        .order_by(Order.created_at.asc())
    ).scalars().all()
    realized = _realized_pnl_per_symbol(orders)
    symbol_starting_capital = 10_000.0  # для нормализации к %

    import json

    deltas: dict[str, tuple[int, int]] = {}  # name → (successes, failures)
    for d in decisions:
        try:
            votes = json.loads(d.strategies) if d.strategies else []
        except json.JSONDecodeError:
            continue
        for v in votes:
            if not isinstance(v, dict):
                continue
            name = str(v.get("name", "")).strip()
            if not name:
                continue
            action = str(v.get("action", "hold"))
            if action not in ("buy", "sell"):
                continue
            if action != d.action:
                continue  # стратегия не определила финальное решение
            pnl_for_symbol = realized.get(d.symbol, 0.0)
            pnl_pct = pnl_for_symbol / symbol_starting_capital * 100
            success = pnl_pct > success_threshold_pct
            s, f = deltas.get(name, (0, 0))
            deltas[name] = (s + 1, f) if success else (s, f + 1)

    # запишем в БД
    updated: dict[str, BanditState] = {}
    for name, (succ, fail) in deltas.items():
        row = session.get(BanditPosterior, name)
        if row is None:
            row = BanditPosterior(strategy_name=name, alpha=1.0, beta=1.0, samples=0)
            session.add(row)
        row.alpha = float(row.alpha) + succ
        row.beta = float(row.beta) + fail
        row.samples = int(row.samples) + succ + fail
        a, b = row.alpha, row.beta
        updated[name] = BanditState(
            strategy_name=name, alpha=a, beta=b,
            samples=row.samples, mean=a / (a + b),
        )
    return updated


def blend_weights(
    adaptive: dict[str, float],
    bandit: dict[str, float],
    blend: float = 0.5,
) -> dict[str, float]:
    """Смешать линейные adaptive-веса с bandit-sampling.

    blend ∈ [0, 1]. blend=0 — только adaptive; blend=1 — только bandit.
    """
    if not adaptive and not bandit:
        return {}
    keys = set(adaptive) | set(bandit)
    out: dict[str, float] = {}
    blend = max(0.0, min(1.0, float(blend)))
    for k in keys:
        a = float(adaptive.get(k, 1.0))
        b = float(bandit.get(k, 1.0))
        out[k] = a * (1 - blend) + b * blend
    return out
