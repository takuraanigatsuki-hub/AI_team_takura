import json
from datetime import datetime, timezone

import pytest

from app.adaptive.retirement import run_retirement_cycle
from app.core.config import Settings
from app.core.database import configure, init_db, session_scope
from app.models.db import DecisionLog, Order, StrategyConfig


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    configure(f"sqlite:///{tmp_path}/r.db")
    init_db()
    # patch get_settings to return a permissive Settings without env override
    from app.core import config as cfg
    monkeypatch.setattr(cfg, "get_settings", lambda: _testing_settings())


def _testing_settings() -> Settings:
    return Settings(
        symbols=["BTC/USDT"],
        retirement_enabled=True,
        retirement_min_decisions=2,
        retirement_pnl_threshold=-0.5,
        adaptive_lookback_decisions=50,
    )


def _losing_decision(s, symbol, strategy_name, ts):
    s.add(DecisionLog(
        ts=ts, symbol=symbol, action="buy", confidence=0.7, price=100, mode="paper",
        strategies=json.dumps([
            {"name": strategy_name, "action": "buy", "confidence": 0.8, "reason": ""},
        ]),
    ))


def test_retirement_disables_losing_non_user_config(isolated_db):
    base = datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc)
    with session_scope() as s:
        s.add(StrategyConfig(
            name="ma_crossover__tune_xyz", base="ma_crossover",
            params="{}", enabled=1, created_by="tuner", backtest_score=10,
        ))
        s.add(StrategyConfig(
            name="ma_crossover__user_baseline", base="ma_crossover",
            params="{}", enabled=1, created_by="user", backtest_score=-5,
        ))
        # 3 убыточных решения от обеих стратегий
        for i in range(3):
            ts = base.replace(minute=i)
            for name in ("ma_crossover__tune_xyz", "ma_crossover__user_baseline"):
                _losing_decision(s, "BTC/USDT", name, ts)
        # сделка с убытком -10
        s.add(Order(symbol="BTC/USDT", side="buy", quantity=1, price=100,
                    quote_amount=100, fee=0, mode="paper", status="filled", created_at=base))
        s.add(Order(symbol="BTC/USDT", side="sell", quantity=1, price=90,
                    quote_amount=90, fee=0, mode="paper", status="filled", created_at=base))

    result = run_retirement_cycle(_testing_settings())
    assert "ma_crossover__tune_xyz" in result.retired  # авто-конфиг отключён
    assert "ma_crossover__user_baseline" not in result.retired  # user не трогаем
    assert result.skipped_protected == 1

    with session_scope() as s:
        rows = {
            c.name: {"enabled": c.enabled, "note": c.note}
            for c in s.query(StrategyConfig).all()
        }
    assert rows["ma_crossover__tune_xyz"]["enabled"] == 0
    assert rows["ma_crossover__user_baseline"]["enabled"] == 1
    assert "[retired" in rows["ma_crossover__tune_xyz"]["note"]


def test_retirement_skips_when_too_few_decisions(isolated_db):
    with session_scope() as s:
        s.add(StrategyConfig(
            name="fresh", base="ma_crossover",
            params="{}", enabled=1, created_by="tuner", backtest_score=0,
        ))
    result = run_retirement_cycle(_testing_settings())
    assert "fresh" not in result.retired
