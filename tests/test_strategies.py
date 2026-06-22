import numpy as np
import pandas as pd

from app.strategies import StrategyContext, build_strategies
from app.strategies.bollinger_breakout import BollingerBreakoutStrategy
from app.strategies.ma_crossover import MACrossoverStrategy
from app.strategies.rsi_reversion import RSIReversionStrategy


def _candles(closes):
    df = pd.DataFrame({
        "open": closes,
        "high": [c * 1.001 for c in closes],
        "low": [c * 0.999 for c in closes],
        "close": closes,
        "volume": [1.0] * len(closes),
    })
    df.index = np.arange(len(closes)) * 60_000
    return df


def test_ma_crossover_detects_uptrend():
    closes = list(np.linspace(100, 80, 80)) + list(np.linspace(80, 120, 40))
    ctx = StrategyContext(symbol="X/USDT", timeframe="1h", candles=_candles(closes))
    vote = MACrossoverStrategy(fast=12, slow=26).evaluate(ctx)
    assert vote.action in ("buy", "hold")


def test_rsi_reversion_marks_oversold_as_buy():
    closes = list(np.linspace(100, 60, 120))  # сильный downtrend → RSI низкий
    ctx = StrategyContext(symbol="X/USDT", timeframe="1h", candles=_candles(closes))
    vote = RSIReversionStrategy(period=14, oversold=30, overbought=70).evaluate(ctx)
    assert vote.action == "buy"
    assert vote.confidence > 0.5


def test_bollinger_breakout_detects_upper_break():
    # 80 flat candles to settle a tight Bollinger band, then a sharp spike.
    closes = [100.0] * 80 + [180.0]
    ctx = StrategyContext(symbol="X/USDT", timeframe="1h", candles=_candles(closes))
    vote = BollingerBreakoutStrategy(period=20, num_std=2.0).evaluate(ctx)
    assert vote.action == "buy"


def test_build_strategies_filters_unknown_names():
    strats = build_strategies(["ma_crossover", "unknown", "rsi_reversion"])
    assert [s.name for s in strats] == ["ma_crossover", "rsi_reversion"]
