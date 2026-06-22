"""Адаптивные веса стратегий — учится на собственных решениях и сделках.

Источники сигнала производительности:
  1. Журнал решений (`decisions`) — голос стратегии и финальный agregated action.
     Если стратегия голосовала за сделку, и позже эта сделка действительно
     случилась (был соответствующий ордер) — это «decisive vote».
  2. Реализованный P&L по последующим сделкам, агрегированный по символу.
     Каждой стратегии засчитывается её доля влияния (по confidence).

Вес стратегии в агрегаторе:
    w_i = clamp(BASE * exp(λ * normalized_score_i), w_min, w_max)
где normalized_score = z-score attributable_pnl + accuracy_bonus.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.db import DecisionLog, Order, StrategyPerformance


@dataclass
class StrategyPerformanceSnapshot:
    strategy_name: str
    votes: int
    decisive_votes: int
    accuracy: float                # decisive / votes
    attributable_pnl: float        # доля приписываемого strategy-vкладу P&L
    avg_confidence: float
    weight: float = 1.0
    rationale: str = ""

    def as_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "votes": self.votes,
            "decisive_votes": self.decisive_votes,
            "accuracy": round(self.accuracy, 4),
            "attributable_pnl": round(self.attributable_pnl, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "weight": round(self.weight, 4),
            "rationale": self.rationale,
        }


def compute_performance_snapshots(
    session: Session,
    lookback: int = 500,
) -> list[StrategyPerformanceSnapshot]:
    """Просканировать последние N решений + соответствующие сделки, посчитать
    metric'и для каждой стратегии."""
    decisions = session.execute(
        select(DecisionLog).order_by(DecisionLog.ts.desc()).limit(lookback)
    ).scalars().all()
    if not decisions:
        return []

    # реализованный P&L по символу за последние N времени → распределим по
    # стратегиям пропорционально их confidence в этом символе.
    earliest = min(d.ts for d in decisions)
    orders = session.execute(
        select(Order).where(Order.created_at >= earliest)
        .order_by(Order.created_at.asc())
    ).scalars().all()
    realized_per_symbol = _realized_pnl_per_symbol(orders)

    # stats per (strategy, symbol)
    stats: dict[str, dict] = {}
    sym_conf_totals: dict[str, dict[str, float]] = {}  # symbol → {strategy → sum conf}

    for d in decisions:
        try:
            votes = json.loads(d.strategies) if d.strategies else []
        except json.JSONDecodeError:
            continue
        for v in votes:
            if not isinstance(v, dict):
                continue
            name = str(v.get("name", "unknown"))
            action = str(v.get("action", "hold"))
            try:
                conf = float(v.get("confidence", 0.0))
            except (TypeError, ValueError):
                conf = 0.0
            s = stats.setdefault(name, {
                "votes": 0, "decisive": 0, "conf_sum": 0.0,
            })
            s["votes"] += 1
            s["conf_sum"] += conf
            if action == d.action and action in ("buy", "sell"):
                s["decisive"] += 1
                sym_conf_totals.setdefault(d.symbol, {}).setdefault(name, 0.0)
                sym_conf_totals[d.symbol][name] += max(conf, 0.05)

    # рассчитаем attributable P&L
    attributable: dict[str, float] = {}
    for sym, pnl in realized_per_symbol.items():
        conf_map = sym_conf_totals.get(sym, {})
        total = sum(conf_map.values()) or 1.0
        for name, conf in conf_map.items():
            attributable[name] = attributable.get(name, 0.0) + pnl * (conf / total)

    out: list[StrategyPerformanceSnapshot] = []
    for name, s in stats.items():
        votes = s["votes"] or 1
        out.append(StrategyPerformanceSnapshot(
            strategy_name=name,
            votes=s["votes"],
            decisive_votes=s["decisive"],
            accuracy=(s["decisive"] / votes) if votes else 0.0,
            attributable_pnl=attributable.get(name, 0.0),
            avg_confidence=(s["conf_sum"] / votes) if votes else 0.0,
        ))
    return out


def compute_adaptive_weights(
    snapshots: list[StrategyPerformanceSnapshot],
    *,
    base_weight: float = 1.0,
    lam: float = 0.5,
    w_min: float = 0.1,
    w_max: float = 3.0,
) -> dict[str, float]:
    """Применить экспоненциальное взвешивание по нормализованному score."""
    if not snapshots:
        return {}
    # нормализуем pnl через z-score (защита от дикого масштаба отдельных рынков)
    pnls = [s.attributable_pnl for s in snapshots]
    if len(pnls) >= 2:
        mean = sum(pnls) / len(pnls)
        var = sum((p - mean) ** 2 for p in pnls) / len(pnls)
        std = math.sqrt(var) if var > 0 else 1.0
    else:
        mean = 0.0
        std = 1.0
    weights: dict[str, float] = {}
    for s in snapshots:
        z = (s.attributable_pnl - mean) / (std or 1.0)
        accuracy_bonus = (s.accuracy - 0.5) * 0.5  # accuracy в [0,1] → бонус ±0.25
        score = 0.7 * z + 0.3 * accuracy_bonus
        w = base_weight * math.exp(lam * score)
        w = max(w_min, min(w_max, w))
        s.weight = w
        s.rationale = (
            f"votes={s.votes} decisive={s.decisive_votes} "
            f"acc={s.accuracy:.2f} attr_pnl={s.attributable_pnl:+.2f} z={z:+.2f}"
        )
        weights[s.strategy_name] = w
    return weights


def persist_performance_snapshots(
    session: Session,
    snapshots: list[StrategyPerformanceSnapshot],
    *,
    window_start: datetime,
    window_end: datetime,
) -> None:
    for s in snapshots:
        session.add(StrategyPerformance(
            strategy_name=s.strategy_name,
            window_start=window_start, window_end=window_end,
            votes=s.votes, decisive_votes=s.decisive_votes,
            accuracy=s.accuracy, attributable_pnl=s.attributable_pnl,
            avg_confidence=s.avg_confidence, weight=s.weight,
        ))


def _realized_pnl_per_symbol(orders) -> dict[str, float]:
    """FIFO-парирование buy→sell по каждому символу, возврат P&L per symbol."""
    from collections import defaultdict, deque

    queues: dict[str, deque] = defaultdict(deque)
    pnls: dict[str, float] = defaultdict(float)
    for o in sorted(orders, key=lambda x: (x.created_at, x.id)):
        q = queues[o.symbol]
        if o.side == "buy":
            q.append([o.quantity, o.price])
        elif o.side == "sell":
            remaining = o.quantity
            while remaining > 1e-12 and q:
                lot_qty, lot_price = q[0]
                used = min(lot_qty, remaining)
                pnls[o.symbol] += (o.price - lot_price) * used
                lot_qty -= used
                remaining -= used
                if lot_qty <= 1e-12:
                    q.popleft()
                else:
                    q[0][0] = lot_qty
    return dict(pnls)
