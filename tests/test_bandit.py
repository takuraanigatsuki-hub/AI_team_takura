import json
from datetime import datetime, timezone

import pytest

from app.adaptive.bandit import (
    BanditState,
    blend_weights,
    load_bandit_states,
    sample_weights,
    update_bandit_from_history,
)
from app.core.database import configure, init_db, session_scope
from app.models.db import BanditPosterior, DecisionLog, Order


@pytest.fixture()
def isolated_db(tmp_path):
    configure(f"sqlite:///{tmp_path}/b.db")
    init_db()


def test_load_bandit_states_uses_prior_when_missing(isolated_db):
    with session_scope() as s:
        states = load_bandit_states(s, names=["never_seen"])
    assert states["never_seen"].alpha == 1.0
    assert states["never_seen"].beta == 1.0
    assert states["never_seen"].samples == 0


def test_sample_weights_normalizes_average_to_one():
    states = {
        "a": BanditState("a", 5, 1, 6, 5/6),
        "b": BanditState("b", 1, 5, 6, 1/6),
        "c": BanditState("c", 2, 2, 4, 0.5),
    }
    w = sample_weights(states, seed=42)
    avg = sum(w.values()) / len(w)
    # средний вес ≈ 1 (нормализация к N)
    assert 0.7 < avg < 1.3
    assert set(w.keys()) == {"a", "b", "c"}


def test_sample_weights_handles_empty():
    assert sample_weights({}) == {}


def test_update_bandit_from_history_marks_success(isolated_db):
    base = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    with session_scope() as s:
        # winner проголосовал buy и финальный был buy и сделка дала +20
        s.add(DecisionLog(
            ts=base, symbol="BTC/USDT", action="buy", confidence=0.7, price=100,
            mode="paper",
            strategies=json.dumps([
                {"name": "winner", "action": "buy", "confidence": 0.8, "reason": ""},
                {"name": "loser", "action": "buy", "confidence": 0.5, "reason": ""},
            ]),
        ))
        s.add(Order(symbol="BTC/USDT", side="buy", quantity=1.0, price=100,
                    quote_amount=100, fee=0, mode="paper", status="filled",
                    created_at=base))
        s.add(Order(symbol="BTC/USDT", side="sell", quantity=1.0, price=120,
                    quote_amount=120, fee=0, mode="paper", status="filled",
                    created_at=base))
    with session_scope() as s:
        result = update_bandit_from_history(s, lookback=10)
    # обе стратегии получили α += 1 (так как сделка была прибыльной)
    assert "winner" in result and "loser" in result
    assert result["winner"].alpha == pytest.approx(2.0)  # 1 prior + 1 success
    assert result["winner"].beta == pytest.approx(1.0)


def test_update_bandit_marks_failure(isolated_db):
    base = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    with session_scope() as s:
        s.add(DecisionLog(
            ts=base, symbol="ETH/USDT", action="buy", confidence=0.5, price=50,
            mode="paper",
            strategies=json.dumps([
                {"name": "bad", "action": "buy", "confidence": 0.5, "reason": ""},
            ]),
        ))
        s.add(Order(symbol="ETH/USDT", side="buy", quantity=2.0, price=50,
                    quote_amount=100, fee=0, mode="paper", status="filled",
                    created_at=base))
        s.add(Order(symbol="ETH/USDT", side="sell", quantity=2.0, price=40,
                    quote_amount=80, fee=0, mode="paper", status="filled",
                    created_at=base))
    with session_scope() as s:
        result = update_bandit_from_history(s, lookback=10)
    # bad голосовал buy, сделка вышла в минус → β += 1
    assert result["bad"].beta == pytest.approx(2.0)
    assert result["bad"].alpha == pytest.approx(1.0)


def test_blend_weights_midpoint():
    a = {"x": 1.0, "y": 3.0}
    b = {"x": 3.0, "y": 1.0}
    mid = blend_weights(a, b, blend=0.5)
    assert mid["x"] == pytest.approx(2.0)
    assert mid["y"] == pytest.approx(2.0)


def test_blend_weights_extremes():
    a = {"x": 1.0, "y": 0.5}
    b = {"x": 5.0, "y": 2.0}
    only_a = blend_weights(a, b, blend=0.0)
    only_b = blend_weights(a, b, blend=1.0)
    assert only_a == a
    assert only_b == b
