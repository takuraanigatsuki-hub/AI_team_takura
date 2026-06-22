import json
from datetime import datetime, timezone

import pytest

from app.adaptive.weights import (
    StrategyPerformanceSnapshot,
    _realized_pnl_per_symbol,
    compute_adaptive_weights,
    compute_performance_snapshots,
)
from app.core.database import configure, init_db, session_scope
from app.models.db import DecisionLog, Order


@pytest.fixture()
def isolated_db(tmp_path):
    configure(f"sqlite:///{tmp_path}/aw.db")
    init_db()


def test_compute_adaptive_weights_prefers_winner():
    snaps = [
        StrategyPerformanceSnapshot("winner", votes=10, decisive_votes=8,
                                    accuracy=0.8, attributable_pnl=200.0,
                                    avg_confidence=0.7),
        StrategyPerformanceSnapshot("loser", votes=10, decisive_votes=4,
                                    accuracy=0.4, attributable_pnl=-150.0,
                                    avg_confidence=0.4),
    ]
    w = compute_adaptive_weights(snaps, w_min=0.1, w_max=3.0)
    assert w["winner"] > w["loser"]
    assert all(0.1 <= v <= 3.0 for v in w.values())


def test_compute_adaptive_weights_handles_empty():
    assert compute_adaptive_weights([]) == {}


def test_realized_pnl_per_symbol_fifo(isolated_db):
    base = datetime(2026, 6, 20, tzinfo=timezone.utc)
    with session_scope() as s:
        s.add(Order(symbol="BTC/USDT", side="buy", quantity=1.0, price=100,
                    quote_amount=100, fee=0, mode="paper", status="filled",
                    created_at=base))
        s.add(Order(symbol="BTC/USDT", side="sell", quantity=1.0, price=130,
                    quote_amount=130, fee=0, mode="paper", status="filled",
                    created_at=base))
    from sqlalchemy import select
    with session_scope() as s:
        orders = s.execute(select(Order)).scalars().all()
        result = _realized_pnl_per_symbol(orders)
    assert result["BTC/USDT"] == pytest.approx(30.0)


def test_compute_performance_snapshots_from_decisions(isolated_db):
    base = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    with session_scope() as s:
        s.add(DecisionLog(
            ts=base, symbol="BTC/USDT", action="buy", confidence=0.7,
            price=100.0, mode="paper",
            strategies=json.dumps([
                {"name": "alpha", "action": "buy", "confidence": 0.8, "reason": ""},
                {"name": "beta", "action": "sell", "confidence": 0.5, "reason": ""},
            ]),
        ))
        s.add(Order(symbol="BTC/USDT", side="buy", quantity=1.0, price=100,
                    quote_amount=100, fee=0, mode="paper", status="filled",
                    created_at=base))
        s.add(Order(symbol="BTC/USDT", side="sell", quantity=1.0, price=120,
                    quote_amount=120, fee=0, mode="paper", status="filled",
                    created_at=base))

    with session_scope() as session:
        snaps = compute_performance_snapshots(session, lookback=50)
    by_name = {s.strategy_name: s for s in snaps}
    # alpha голосовал buy и финальный был buy → decisive
    assert by_name["alpha"].decisive_votes == 1
    # beta голосовала sell → не decisive
    assert by_name["beta"].decisive_votes == 0
    # alpha должен получить положительный attributable_pnl (BTC дал +20)
    assert by_name["alpha"].attributable_pnl > 0
