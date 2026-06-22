import numpy as np
import pytest

from app.adaptive.genetic import _crossover, _mutate
from app.strategies.registry import STRATEGY_FACTORIES


def test_crossover_produces_valid_dict():
    rng = np.random.default_rng(0)
    a = {"fast": 10, "slow": 26}
    b = {"fast": 20, "slow": 40}
    child = _crossover(a, b, rng)
    assert set(child) == {"fast", "slow"}
    # каждое значение либо родительское, либо в пределах [min, max] двух родителей
    for k in ("fast", "slow"):
        assert min(a[k], b[k]) <= child[k] <= max(a[k], b[k])


def test_mutate_keeps_within_factory_bounds():
    rng = np.random.default_rng(0)
    factory = STRATEGY_FACTORIES["ma_crossover"]
    params = {"fast": 12, "slow": 26}
    for _ in range(20):
        mutated = _mutate("ma_crossover", params, rate=1.0, rng=rng)
        schema = {p.name: p for p in factory.params}
        for k, v in mutated.items():
            assert schema[k].low <= v <= schema[k].high


def test_mutate_respects_rate_zero():
    rng = np.random.default_rng(0)
    params = {"fast": 12, "slow": 26}
    # с rate=0 параметры могут пройти через clamp_params, но логически не должны меняться
    out = _mutate("ma_crossover", params, rate=0.0, rng=rng)
    assert out["fast"] == 12
    assert out["slow"] == 26


def test_mutate_clamps_types():
    rng = np.random.default_rng(0)
    factory = STRATEGY_FACTORIES["rsi_reversion"]
    params = {"period": 14, "oversold": 30.0, "overbought": 70.0}
    out = _mutate("rsi_reversion", params, rate=1.0, rng=rng)
    schema_by_name = {p.name: p for p in factory.params}
    assert isinstance(out["period"], int)
    assert isinstance(out["oversold"], float)
    assert isinstance(out["overbought"], float)
