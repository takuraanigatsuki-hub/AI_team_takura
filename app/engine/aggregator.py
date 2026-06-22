from __future__ import annotations

from collections import Counter

from ..models.schemas import Signal, StrategyVote


def aggregate_votes(
    symbol: str,
    price: float,
    votes: list[StrategyVote],
    consensus: int = 2,
    weights: dict[str, float] | None = None,
) -> Signal:
    """Слить голоса стратегий в один сигнал.

    Алгоритм:
    - confidence каждого голоса умножается на адаптивный вес стратегии
      (weights[strategy_name], default 1.0);
    - выигрывает действие с большей взвешенной суммарной уверенностью;
    - становится сигналом, только если число согласных стратегий (с
      conf*weight ≥ 0.2) не меньше `consensus`.
    """
    weights = weights or {}
    enriched = []
    for v in votes:
        w = float(weights.get(v.name, 1.0))
        eff_conf = v.confidence * w
        enriched.append((v, w, eff_conf))

    actionable = [(v, w, eff) for v, w, eff in enriched
                  if v.action in ("buy", "sell") and eff > 0.0]

    weighted: Counter[str] = Counter()
    for v, _w, eff in actionable:
        weighted[v.action] += eff

    if not actionable:
        return Signal(
            symbol=symbol, action="hold", confidence=0.0, price=price,
            votes=votes, reason="нет actionable голосов",
        )

    action, score = max(weighted.items(), key=lambda kv: kv[1])

    agree = [v for v, _w, eff in actionable if v.action == action and eff >= 0.2]
    if len(agree) < consensus:
        return Signal(
            symbol=symbol, action="hold", confidence=score / max(len(actionable), 1),
            price=price, votes=votes,
            reason=(
                f"{action} поддержан {len(agree)} из {len(votes)} стратегий "
                f"(взвешенно), нужно {consensus}"
            ),
        )

    confidence = min(1.0, score / max(len(actionable), 1))
    reason = "; ".join(v.reason for v in agree if v.reason)
    return Signal(
        symbol=symbol, action=action, confidence=confidence, price=price,
        votes=votes, reason=reason or f"{action} по взвешенному консенсусу",
    )
