import json
from datetime import datetime, timezone

import pytest

from app.agent.reflection import _parse_reflection, _realized_pnl
from app.core.database import configure, init_db, session_scope
from app.models.db import Order


@pytest.fixture()
def isolated_db(tmp_path):
    configure(f"sqlite:///{tmp_path}/r.db")
    init_db()


def test_parse_reflection_extracts_summary_and_rules():
    raw = """```json
    {
      "summary": "agent over-traded BTC during low-vol regime",
      "rules_learned": [
        "Don't open BTC long when RSI > 70 in the last 24h",
        "Reduce size by 50% after a losing day"
      ]
    }
    ```"""
    summary, rules = _parse_reflection(raw)
    assert "over-traded" in summary
    assert len(rules) == 2
    assert any("RSI" in r for r in rules)


def test_parse_reflection_handles_garbage():
    summary, rules = _parse_reflection("nope not json")
    assert rules == []
    assert "parse failed" in summary


def test_parse_reflection_filters_non_strings():
    raw = '{"summary": "ok", "rules_learned": ["good rule", 123, null, "another"]}'
    _, rules = _parse_reflection(raw)
    assert rules == ["good rule", "another"]


def test_realized_pnl_fifo_pairing(isolated_db):
    base = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    with session_scope() as s:
        s.add(Order(symbol="BTC/USDT", side="buy", quantity=1.0, price=100,
                    quote_amount=100, fee=0, mode="paper", status="filled",
                    created_at=base))
        s.add(Order(symbol="BTC/USDT", side="sell", quantity=1.0, price=120,
                    quote_amount=120, fee=0, mode="paper", status="filled",
                    created_at=base))
        s.add(Order(symbol="ETH/USDT", side="buy", quantity=2.0, price=50,
                    quote_amount=100, fee=0, mode="paper", status="filled",
                    created_at=base))
        s.add(Order(symbol="ETH/USDT", side="sell", quantity=2.0, price=45,
                    quote_amount=90, fee=0, mode="paper", status="filled",
                    created_at=base))
    with session_scope() as s:
        from sqlalchemy import select
        orders = s.execute(select(Order)).scalars().all()
        # BTC: +20, ETH: -10 → net +10
        assert _realized_pnl(orders) == pytest.approx(10.0)
