"""Метрики работы бота — equity curve, дневной P&L, drawdown, Sharpe, win-rate."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.db import DecisionLog, EquityPoint, Order


@dataclass
class DailyPnL:
    date: str  # YYYY-MM-DD (UTC)
    open_equity: float
    close_equity: float
    pnl: float
    pnl_pct: float


@dataclass
class PortfolioMetrics:
    points: int
    first_at: datetime | None
    last_at: datetime | None
    starting_equity: float
    current_equity: float
    total_return: float
    total_return_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float | None  # annualized, по дневным доходностям
    sortino_ratio: float | None
    win_rate: float | None  # доля закрывших в плюс сделок
    avg_trade_pnl: float | None
    num_orders: int
    daily_pnl: list[DailyPnL] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "points": self.points,
            "first_at": self.first_at.isoformat() if self.first_at else None,
            "last_at": self.last_at.isoformat() if self.last_at else None,
            "starting_equity": self.starting_equity,
            "current_equity": self.current_equity,
            "total_return": self.total_return,
            "total_return_pct": self.total_return_pct,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "win_rate": self.win_rate,
            "avg_trade_pnl": self.avg_trade_pnl,
            "num_orders": self.num_orders,
            "daily_pnl": [d.__dict__ for d in self.daily_pnl],
        }


@dataclass
class StrategyAttribution:
    strategy: str
    votes: int
    buy_votes: int
    sell_votes: int
    hold_votes: int
    avg_confidence: float
    decisive_buys: int  # сколько раз стратегия голосовала buy, и сигнал стал buy
    decisive_sells: int

    def as_dict(self) -> dict:
        return self.__dict__


def compute_daily_pnl(session: Session) -> list[DailyPnL]:
    """Группирует equity-точки по дням (UTC) и считает изменение."""
    points = session.execute(
        select(EquityPoint).order_by(EquityPoint.ts.asc())
    ).scalars().all()
    if not points:
        return []
    by_day: dict[str, list[EquityPoint]] = {}
    for p in points:
        key = p.ts.strftime("%Y-%m-%d")
        by_day.setdefault(key, []).append(p)
    out: list[DailyPnL] = []
    prev_close: float | None = None
    for day in sorted(by_day):
        rows = by_day[day]
        open_eq = float(rows[0].equity)
        close_eq = float(rows[-1].equity)
        # Если есть прошлый день — открытие текущего дня для P&L = вчерашнее закрытие
        baseline = prev_close if prev_close is not None else open_eq
        pnl = close_eq - baseline
        pnl_pct = (pnl / baseline * 100) if baseline > 0 else 0.0
        out.append(DailyPnL(day, baseline, close_eq, pnl, pnl_pct))
        prev_close = close_eq
    return out


def compute_portfolio_metrics(session: Session) -> PortfolioMetrics:
    points = session.execute(
        select(EquityPoint).order_by(EquityPoint.ts.asc())
    ).scalars().all()
    orders = session.execute(
        select(Order).order_by(Order.created_at.asc())
    ).scalars().all()
    if not points:
        return PortfolioMetrics(
            points=0, first_at=None, last_at=None,
            starting_equity=0.0, current_equity=0.0,
            total_return=0.0, total_return_pct=0.0,
            max_drawdown=0.0, max_drawdown_pct=0.0,
            sharpe_ratio=None, sortino_ratio=None,
            win_rate=None, avg_trade_pnl=None,
            num_orders=len(orders), daily_pnl=[],
        )

    equities = [float(p.equity) for p in points]
    start = equities[0]
    end = equities[-1]
    total_return = end - start
    total_return_pct = (total_return / start * 100) if start > 0 else 0.0

    # max drawdown
    peak = equities[0]
    max_dd = 0.0
    max_dd_pct = 0.0
    for eq in equities:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
            max_dd_pct = (dd / peak * 100) if peak > 0 else 0.0

    # дневные доходности → Sharpe / Sortino (annualized by sqrt(365))
    daily_pnl = compute_daily_pnl(session)
    daily_returns: list[float] = []
    for d in daily_pnl:
        if d.open_equity > 0:
            daily_returns.append(d.close_equity / d.open_equity - 1.0)
    sharpe = _annualized_sharpe(daily_returns)
    sortino = _annualized_sortino(daily_returns)

    # win-rate из ордеров (грубая оценка: считаем sell с положительным quote vs buy)
    # лучшая оценка — pair-trade matching, но для простоты считаем:
    # средний P&L = разница между накопленным «выручка от sell» и «потрачено на buy»
    buy_quote = sum(o.quote_amount + o.fee for o in orders if o.side == "buy")
    sell_quote = sum(o.quote_amount - o.fee for o in orders if o.side == "sell")
    closed_trades = min(
        sum(1 for o in orders if o.side == "sell"),
        sum(1 for o in orders if o.side == "buy"),
    )
    win_rate, avg_trade_pnl = _trade_win_rate(orders)

    return PortfolioMetrics(
        points=len(points),
        first_at=points[0].ts,
        last_at=points[-1].ts,
        starting_equity=start,
        current_equity=end,
        total_return=total_return,
        total_return_pct=total_return_pct,
        max_drawdown=max_dd,
        max_drawdown_pct=max_dd_pct,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        win_rate=win_rate,
        avg_trade_pnl=avg_trade_pnl,
        num_orders=len(orders),
        daily_pnl=daily_pnl,
    )


def compute_strategy_attribution(session: Session, limit: int = 2000) -> list[StrategyAttribution]:
    """Анализирует журнал решений: сколько раз каждая стратегия голосовала
    и в скольких случаях её голос совпал с финальным сигналом."""
    decisions = session.execute(
        select(DecisionLog).order_by(DecisionLog.ts.desc()).limit(limit)
    ).scalars().all()

    stats: dict[str, dict] = {}
    for d in decisions:
        try:
            votes = json.loads(d.strategies) if d.strategies else []
        except json.JSONDecodeError:
            continue
        for v in votes:
            if not isinstance(v, dict):
                continue
            name = str(v.get("name", "unknown"))
            slot = stats.setdefault(name, {
                "votes": 0, "buy": 0, "sell": 0, "hold": 0,
                "conf_sum": 0.0, "dec_buy": 0, "dec_sell": 0,
            })
            slot["votes"] += 1
            action = str(v.get("action", "hold"))
            slot[action if action in ("buy", "sell", "hold") else "hold"] += 1
            try:
                slot["conf_sum"] += float(v.get("confidence", 0.0))
            except (TypeError, ValueError):
                pass
            final = d.action
            if action == "buy" and final == "buy":
                slot["dec_buy"] += 1
            elif action == "sell" and final == "sell":
                slot["dec_sell"] += 1

    out: list[StrategyAttribution] = []
    for name, s in sorted(stats.items()):
        votes = s["votes"]
        avg_conf = (s["conf_sum"] / votes) if votes else 0.0
        out.append(StrategyAttribution(
            strategy=name,
            votes=votes,
            buy_votes=s["buy"], sell_votes=s["sell"], hold_votes=s["hold"],
            avg_confidence=round(avg_conf, 4),
            decisive_buys=s["dec_buy"], decisive_sells=s["dec_sell"],
        ))
    return out


def _annualized_sharpe(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(var)
    if std <= 1e-12:
        return None
    return (mean / std) * math.sqrt(365)


def _annualized_sortino(returns: list[float]) -> float | None:
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    downside = [r for r in returns if r < 0]
    if not downside:
        return None
    dvar = sum(r * r for r in downside) / len(returns)
    dstd = math.sqrt(dvar)
    if dstd <= 1e-12:
        return None
    return (mean / dstd) * math.sqrt(365)


def _trade_win_rate(orders) -> tuple[float | None, float | None]:
    """Парит buy→sell по символу (FIFO) и считает P&L каждой пары."""
    from collections import defaultdict, deque

    queues: dict[str, deque] = defaultdict(deque)  # symbol → deque[(qty, price)]
    pnls: list[float] = []
    for o in sorted(orders, key=lambda x: (x.created_at, x.id)):
        q = queues[o.symbol]
        if o.side == "buy":
            q.append([o.quantity, o.price])
        elif o.side == "sell":
            remaining = o.quantity
            sell_price = o.price
            while remaining > 1e-12 and q:
                lot_qty, lot_price = q[0]
                used = min(lot_qty, remaining)
                pnls.append((sell_price - lot_price) * used)
                lot_qty -= used
                remaining -= used
                if lot_qty <= 1e-12:
                    q.popleft()
                else:
                    q[0][0] = lot_qty
    if not pnls:
        return None, None
    wins = sum(1 for p in pnls if p > 0)
    return wins / len(pnls), sum(pnls) / len(pnls)
