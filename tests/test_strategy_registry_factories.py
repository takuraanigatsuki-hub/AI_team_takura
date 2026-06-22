import pytest

from app.strategies.bollinger_breakout import BollingerBreakoutStrategy
from app.strategies.ma_crossover import MACrossoverStrategy
from app.strategies.registry import (
    STRATEGY_FACTORIES,
    available_base_strategies,
    build_strategy_from_config,
    clamp_params,
    get_factory,
)


def test_factories_cover_three_base_strategies():
    bases = set(available_base_strategies())
    assert {"ma_crossover", "rsi_reversion", "bollinger_breakout"} == bases


def test_clamp_params_respects_bounds():
    out = clamp_params("ma_crossover", {"fast": 999, "slow": -1})
    schema = {p.name: p for p in get_factory("ma_crossover").params}
    assert out["fast"] == schema["fast"].high
    assert out["slow"] == schema["slow"].low
    # int kind enforced
    assert isinstance(out["fast"], int) and isinstance(out["slow"], int)


def test_clamp_params_handles_garbage():
    out = clamp_params("rsi_reversion", {"period": "abc", "oversold": None})
    # fallback на defaults
    assert out["period"] == 14
    assert out["oversold"] == 30.0


def test_build_strategy_from_config_creates_instance():
    inst = build_strategy_from_config("ma_crossover", "custom_name",
                                       {"fast": 9, "slow": 33})
    assert isinstance(inst, MACrossoverStrategy)
    assert inst.name == "custom_name"
    assert inst.fast == 9
    assert inst.slow == 33


def test_build_strategy_from_config_unknown_base():
    assert build_strategy_from_config("does_not_exist", "x", {}) is None


def test_factories_have_safe_constraint_check():
    # эта проверка тоже срабатывает в tuner._enforce_constraints, проверим напрямую
    from app.adaptive.tuner import _enforce_constraints
    assert _enforce_constraints("ma_crossover", {"fast": 5, "slow": 26}) is True
    assert _enforce_constraints("ma_crossover", {"fast": 25, "slow": 26}) is False
    assert _enforce_constraints("rsi_reversion", {"oversold": 30, "overbought": 70}) is True
    assert _enforce_constraints("rsi_reversion", {"oversold": 40, "overbought": 45}) is False
