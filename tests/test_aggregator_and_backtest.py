import numpy as np
import pandas as pd

from app.core.config import Settings
from app.engine.aggregator import aggregate_votes
from app.engine.backtest import run_backtest
from app.models.schemas import StrategyVote
from app.strategies.bollinger_breakout import BollingerBreakoutStrategy
from app.strategies.ma_crossover import MACrossoverStrategy
from app.strategies.rsi_reversion import RSIReversionStrategy


def test_aggregator_requires_consensus():
    votes = [
        StrategyVote(name="a", action="buy", confidence=0.8, reason=""),
        StrategyVote(name="b", action="hold", confidence=0.2, reason=""),
        StrategyVote(name="c", action="sell", confidence=0.3, reason=""),
    ]
    sig = aggregate_votes("X/USDT", 100.0, votes, consensus=2)
    assert sig.action == "hold"  # only 1 buy with conf>=0.2


def test_aggregator_buy_with_consensus():
    votes = [
        StrategyVote(name="a", action="buy", confidence=0.8, reason="r1"),
        StrategyVote(name="b", action="buy", confidence=0.6, reason="r2"),
        StrategyVote(name="c", action="hold", confidence=0.2, reason=""),
    ]
    sig = aggregate_votes("X/USDT", 100.0, votes, consensus=2)
    assert sig.action == "buy"
    assert sig.confidence > 0


def _ohlcv(closes):
    return pd.DataFrame({
        "open": closes,
        "high": [c * 1.002 for c in closes],
        "low": [c * 0.998 for c in closes],
        "close": closes,
        "volume": [1.0] * len(closes),
    }, index=np.arange(len(closes)) * 60_000)


def test_backtest_runs_and_returns_curve():
    rng = np.random.default_rng(42)
    closes = (100 + np.cumsum(rng.normal(0, 0.6, size=400))).tolist()
    settings = Settings(
        symbols=["X/USDT"],
        risk_per_trade=0.2,
        stop_loss_pct=0.05,
        take_profit_pct=0.1,
        signal_consensus=1,
        max_open_positions=1,
        min_order_notional=1,
    )
    strats = [MACrossoverStrategy(), RSIReversionStrategy(), BollingerBreakoutStrategy()]
    res = run_backtest(_ohlcv(closes), strats, settings, starting_balance=1_000.0)
    assert res.starting_balance == 1_000.0
    assert len(res.equity_curve) > 0
    assert res.num_trades >= 0  # may be zero on this random walk, but no crash
