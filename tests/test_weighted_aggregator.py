from app.engine.aggregator import aggregate_votes
from app.models.schemas import StrategyVote


def test_weights_amplify_winning_strategy():
    votes = [
        StrategyVote(name="trusted", action="buy", confidence=0.4, reason="r1"),
        StrategyVote(name="other", action="buy", confidence=0.4, reason="r2"),
        StrategyVote(name="contrarian", action="sell", confidence=0.8, reason="r3"),
    ]
    # без весов sell бы выиграл по сумме confidence (0.8 > 0.8)
    sig_no_weights = aggregate_votes("BTC/USDT", 100.0, votes, consensus=2)
    # с бустом trusted * 3 — buy выигрывает
    sig_boosted = aggregate_votes("BTC/USDT", 100.0, votes, consensus=2,
                                   weights={"trusted": 3.0})
    assert sig_boosted.action == "buy"


def test_weight_zero_silences_strategy():
    votes = [
        StrategyVote(name="silent", action="buy", confidence=0.9, reason=""),
        StrategyVote(name="loud", action="sell", confidence=0.3, reason=""),
        StrategyVote(name="loud2", action="sell", confidence=0.3, reason=""),
    ]
    sig = aggregate_votes("BTC/USDT", 100.0, votes, consensus=2,
                          weights={"silent": 0.0})
    assert sig.action == "sell"


def test_weights_dont_break_default_path():
    votes = [
        StrategyVote(name="a", action="buy", confidence=0.6, reason=""),
        StrategyVote(name="b", action="buy", confidence=0.5, reason=""),
    ]
    sig_default = aggregate_votes("BTC/USDT", 100.0, votes, consensus=2)
    sig_with_ones = aggregate_votes("BTC/USDT", 100.0, votes, consensus=2,
                                     weights={"a": 1.0, "b": 1.0})
    assert sig_default.action == sig_with_ones.action == "buy"


def test_consensus_uses_effective_confidence():
    # каждая стратегия делает голос с conf 0.3 → effective с weight=0.5 = 0.15 < 0.2
    # → ни один не считается «согласным» → hold
    votes = [
        StrategyVote(name="a", action="buy", confidence=0.3, reason=""),
        StrategyVote(name="b", action="buy", confidence=0.3, reason=""),
    ]
    sig = aggregate_votes("BTC/USDT", 100.0, votes, consensus=2,
                          weights={"a": 0.5, "b": 0.5})
    assert sig.action == "hold"
