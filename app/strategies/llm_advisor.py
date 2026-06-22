from __future__ import annotations

import json

from ..core.config import get_settings
from ..llm.client import LLMUnavailable, get_llm_client
from ..models.schemas import StrategyVote
from .base import Strategy, StrategyContext
from .indicators import bollinger_bands, ema, rsi


SYSTEM_PROMPT = (
    "Ты — осторожный криптотрейдер-помощник. Тебе дают свежие технические показатели "
    "одного инструмента и просят оценить вероятный краткосрочный сценарий. "
    "Отвечай СТРОГО валидным JSON формата "
    '{"action":"buy|sell|hold","confidence":0..1,"reason":"короткое объяснение"}. '
    "Если данных мало или сигналы противоречат друг другу — возвращай 'hold' с низкой уверенностью."
)


class LLMAdvisorStrategy(Strategy):
    """Опциональная стратегия: LLM-советник, читающий снимок индикаторов."""

    name = "llm_advisor"

    def warmup_candles(self) -> int:
        return 60

    def evaluate(self, ctx: StrategyContext) -> StrategyVote:
        settings = get_settings()
        if not settings.llm_api_key:
            return StrategyVote(
                name=self.name, action="hold", confidence=0.0,
                reason="LLM API key не задан",
            )
        df = ctx.candles
        if len(df) < self.warmup_candles():
            return StrategyVote(name=self.name, action="hold", confidence=0.0,
                                reason="недостаточно данных")

        close = df["close"]
        ema_fast = float(ema(close, 12).iloc[-1])
        ema_slow = float(ema(close, 26).iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])
        lower, mid, upper = bollinger_bands(close, 20, 2.0)
        snapshot = {
            "symbol": ctx.symbol,
            "timeframe": ctx.timeframe,
            "price": float(close.iloc[-1]),
            "price_24h_change_pct": float(
                (close.iloc[-1] / close.iloc[-min(len(close) - 1, 96)] - 1.0) * 100
            ),
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "rsi_14": rsi_val,
            "bollinger_lower": float(lower.iloc[-1]),
            "bollinger_mid": float(mid.iloc[-1]),
            "bollinger_upper": float(upper.iloc[-1]),
            "in_position": ctx.position_quantity > 0,
        }

        user_prompt = (
            "Технический снапшот:\n```json\n"
            + json.dumps(snapshot, indent=2)
            + "\n```\nОцени и верни JSON-ответ."
        )

        try:
            client = get_llm_client()
            text = client.complete(SYSTEM_PROMPT, user_prompt)
        except LLMUnavailable as exc:
            return StrategyVote(
                name=self.name, action="hold", confidence=0.0,
                reason=f"LLM недоступен: {exc}",
            )

        return _parse_llm_response(text, self.name)


def _parse_llm_response(text: str, name: str) -> StrategyVote:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return StrategyVote(name=name, action="hold", confidence=0.0,
                                    reason="LLM вернул нераспознаваемый ответ")
        else:
            return StrategyVote(name=name, action="hold", confidence=0.0,
                                reason="LLM вернул нераспознаваемый ответ")

    action = str(data.get("action", "hold")).lower()
    if action not in ("buy", "sell", "hold"):
        action = "hold"
    try:
        confidence = float(data.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    reason = str(data.get("reason", ""))[:200]
    return StrategyVote(name=name, action=action, confidence=confidence, reason=reason)
