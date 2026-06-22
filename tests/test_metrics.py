from datetime import datetime, timedelta, timezone

import pytest

from app.core.database import configure, init_db, session_scope
from app.metrics.performance import (
    compute_daily_pnl,
    compute_portfolio_metrics,
    compute_strategy_attribution,
)
from app.models.db import DecisionLog, EquityPoint, Order


@pytest.fixture()
def isolated_db(tmp_path):
    configure(f"sqlite:///{tmp_path}/m.db")
    init_db()


def _eq(session, ts, equity, cash=0.0, pv=0.0, mode="paper"):
    session.add(EquityPoint(ts=ts, cash=cash, positions_value=pv, equity=equity, mode=mode))


def test_daily_pnl_aggregates_by_day(isolated_db):
    base = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    with session_scope() as s:
        _eq(s, base, 1000)
        _eq(s, base + timedelta(hours=6), 1050)
        _eq(s, base + timedelta(days=1), 1100)
        _eq(s, base + timedelta(days=1, hours=8), 1020)

    with session_scope() as s:
        days = compute_daily_pnl(s)
    assert len(days) == 2
    assert days[0].pnl == 50.0
    # second day open = previous close = 1050, close = 1020 → -30
    assert days[1].pnl == pytest.approx(-30.0)


def test_portfolio_metrics_max_drawdown(isolated_db):
    base = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    with session_scope() as s:
        _eq(s, base, 1000)
        _eq(s, base + timedelta(days=1), 1200)
        _eq(s, base + timedelta(days=2), 900)   # drawdown 300 / 1200 = 25%
        _eq(s, base + timedelta(days=3), 1100)

    with session_scope() as s:
        m = compute_portfolio_metrics(s)
    assert m.starting_equity == 1000
    assert m.current_equity == 1100
    assert m.total_return == 100
    assert m.max_drawdown == pytest.approx(300.0)
    assert m.max_drawdown_pct == pytest.approx(25.0)


def test_portfolio_metrics_win_rate_with_fifo_pairing(isolated_db):
    base = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    with session_scope() as s:
        _eq(s, base, 1000)
        s.add(Order(symbol="BTC/USDT", side="buy", quantity=1.0, price=100,
                    quote_amount=100, fee=0, mode="paper", status="filled",
                    created_at=base))
        s.add(Order(symbol="BTC/USDT", side="sell", quantity=1.0, price=120,
                    quote_amount=120, fee=0, mode="paper", status="filled",
                    created_at=base + timedelta(hours=1)))
        s.add(Order(symbol="ETH/USDT", side="buy", quantity=1.0, price=50,
                    quote_amount=50, fee=0, mode="paper", status="filled",
                    created_at=base + timedelta(hours=2)))
        s.add(Order(symbol="ETH/USDT", side="sell", quantity=1.0, price=40,
                    quote_amount=40, fee=0, mode="paper", status="filled",
                    created_at=base + timedelta(hours=3)))

    with session_scope() as s:
        m = compute_portfolio_metrics(s)
    # 1 win (+20) + 1 loss (-10) → win_rate = 0.5, avg = 5
    assert m.win_rate == pytest.approx(0.5)
    assert m.avg_trade_pnl == pytest.approx(5.0)
    assert m.num_orders == 4


def test_strategy_attribution_counts_per_strategy(isolated_db):
    import json

    base = datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)
    with session_scope() as s:
        s.add(DecisionLog(
            ts=base, symbol="BTC/USDT", action="buy", confidence=0.7,
            price=100.0, mode="paper",
            strategies=json.dumps([
                {"name": "ma_crossover", "action": "buy", "confidence": 0.8, "reason": ""},
                {"name": "rsi_reversion", "action": "buy", "confidence": 0.6, "reason": ""},
                {"name": "bollinger_breakout", "action": "hold", "confidence": 0.1, "reason": ""},
            ]),
        ))
        s.add(DecisionLog(
            ts=base + timedelta(minutes=1), symbol="BTC/USDT", action="hold",
            confidence=0.0, price=100.0, mode="paper",
            strategies=json.dumps([
                {"name": "ma_crossover", "action": "hold", "confidence": 0.2, "reason": ""},
                {"name": "rsi_reversion", "action": "sell", "confidence": 0.4, "reason": ""},
                {"name": "bollinger_breakout", "action": "hold", "confidence": 0.0, "reason": ""},
            ]),
        ))

    with session_scope() as s:
        attrs = compute_strategy_attribution(s)
    by_name = {a.strategy: a for a in attrs}
    assert by_name["ma_crossover"].votes == 2
    assert by_name["ma_crossover"].buy_votes == 1
    assert by_name["ma_crossover"].decisive_buys == 1
    assert by_name["rsi_reversion"].sell_votes == 1
    # rsi проголосовал sell, но финальный был hold → decisive_sells = 0
    assert by_name["rsi_reversion"].decisive_sells == 0
