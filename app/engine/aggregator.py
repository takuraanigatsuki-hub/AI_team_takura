from __future__ import annotations

from collections import Counter

from ..models.schemas import Signal, StrategyVote


def aggregate_votes(
    symbol: str,
    price: float,
    votes: list[StrategyVote],
    consensus: int = 2,
) -> Signal:
    """Слить голоса стратегий в один сигнал.

    Алгоритм:
    - считаем голоса 'buy'/'sell' (взвешенные по confidence);
    - выигрывает действие с большей суммарной уверенностью;
    - оно становится сигналом, только если число согласных стратегий (с conf>0.2)
      не меньше `consensus`.
    """
    actionable = [v for v in votes if v.action in ("buy", "sell") and v.confidence > 0.0]

    weighted: Counter[str] = Counter()
    for v in actionable:
        weighted[v.action] += v.confidence

    if not actionable:
        return Signal(
            symbol=symbol, action="hold", confidence=0.0, price=price,
            votes=votes, reason="нет actionable голосов",
        )

    winner = max(weighted.items(), key=lambda kv: kv[1])
    action, score = winner

    agree = [v for v in actionable if v.action == action and v.confidence >= 0.2]
    if len(agree) < consensus:
        return Signal(
            symbol=symbol, action="hold", confidence=score / max(len(actionable), 1),
            price=price, votes=votes,
            reason=(
                f"{action} поддержан {len(agree)} из {len(votes)} стратегий, "
                f"нужно {consensus}"
            ),
        )

    confidence = min(1.0, score / max(len(actionable), 1))
    reason = "; ".join(v.reason for v in agree if v.reason)
    return Signal(
        symbol=symbol, action=action, confidence=confidence, price=price,
        votes=votes, reason=reason or f"{action} по консенсусу",
    )
