"""Online learning for sentiment: лексикон корректируется по реакции цены.

Алгоритм:
  1. Берём новости за окно [T - horizon, T].
  2. Для каждой новости: считаем последующее движение цены упомянутого
     инструмента за `horizon_hours` после публикации.
  3. Для каждого слова в новости: обновляем средневзвешенное движение
     цены SGD-подобным правилом
        weight ← weight + lr * (price_change_pct / 100 - weight) * scale
     где scale ~ 1 / sqrt(samples + 1) (новые слова обновляются сильнее).
  4. Сохраняем в OnlineLexicon. Эти веса используются как ДОБАВКА к
     статическому лексикону при scoring.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..core.database import session_scope
from ..core.logging import logger
from ..models.db import OnlineLexicon
from .analyzer import COIN_KEYS


TOKEN_RE = re.compile(r"[a-z][a-z\-0-9]+")

# Стоп-слова, которые точно не несут sentiment-сигнал.
STOPWORDS = {
    "the", "and", "for", "with", "from", "this", "that", "have", "has", "was",
    "were", "are", "into", "over", "under", "after", "before", "while", "their",
    "they", "them", "than", "then", "would", "should", "could", "about", "would",
    "today", "yesterday", "between", "during", "what", "when", "where", "which",
    "year", "years", "month", "week", "weeks", "billion", "million", "new",
    "said", "says", "according", "report", "reports", "reported",
}


@dataclass
class OnlineSentimentSample:
    word: str
    weight: float
    samples: int


def _extract_tokens(text: str) -> set[str]:
    return {
        t for t in TOKEN_RE.findall((text or "").lower())
        if len(t) >= 3 and t not in STOPWORDS
    }


def _detect_symbol(text: str, symbols: list[str]) -> str | None:
    """Найти упоминание инструмента из allowlist."""
    text_lc = (text or "").lower()
    for symbol in symbols:
        keys = COIN_KEYS.get(symbol, set())
        if any(k in text_lc for k in keys):
            return symbol
    return None


def _update_lexicon(
    session: Session,
    word_to_change: dict[str, list[float]],
    lr: float,
) -> int:
    """Применить SGD-update к каждому слову. Возвращает число обновлённых строк."""
    updated = 0
    for word, deltas in word_to_change.items():
        if not deltas:
            continue
        avg_change = sum(deltas) / len(deltas)
        row = session.get(OnlineLexicon, word)
        if row is None:
            row = OnlineLexicon(word=word, weight=0.0, samples=0)
            session.add(row)
        # масштаб обучения: новые слова обновляются сильнее
        scale = 1.0 / ((row.samples or 0) + 1) ** 0.5
        # target: средняя реакция цены в долях
        delta = lr * scale * (avg_change - row.weight)
        new_weight = max(-1.0, min(1.0, row.weight + delta))
        row.weight = float(new_weight)
        row.samples = int(row.samples or 0) + len(deltas)
        updated += 1
    return updated


async def run_online_learning_cycle(
    settings: Settings | None = None,
    *,
    fetch_price_change=None,
    news_fetcher=None,
) -> dict:
    """Один цикл обучения. Возвращает diagnostic.

    fetch_price_change: callable(symbol, ts, horizon_hours) -> float | None
                        Возвращает % изменение цены после ts.
    news_fetcher: callable() -> list[NewsItem]. Для тестов можно подставить мок.
    """
    s = settings or get_settings()
    if not s.sentiment_online_enabled:
        return {"updated": 0, "skipped": "disabled"}

    if news_fetcher is None:
        from ..news.feeds import get_news_service
        news_fetcher = lambda: get_news_service().fetch(limit=80, force=True)
    if fetch_price_change is None:
        fetch_price_change = _real_price_change

    horizon = s.sentiment_online_horizon_hours
    cutoff = datetime.now(timezone.utc) - timedelta(hours=horizon)

    news = await news_fetcher()
    if not news:
        return {"updated": 0, "skipped": "no news"}

    word_to_change: dict[str, list[float]] = {}
    sampled = 0
    for item in news:
        published = getattr(item, "published_at", None)
        if not published or published > cutoff:
            continue
        title = getattr(item, "title", "") or ""
        summary = getattr(item, "summary", "") or ""
        text = f"{title} {summary}"
        symbol = _detect_symbol(text, list(s.symbols))
        if symbol is None:
            continue
        change = await fetch_price_change(symbol, published, horizon)
        if change is None:
            continue
        change_pct = max(-30.0, min(30.0, float(change)))
        tokens = _extract_tokens(text)
        if not tokens:
            continue
        for w in tokens:
            word_to_change.setdefault(w, []).append(change_pct / 100.0)
        sampled += 1

    if not word_to_change:
        return {"updated": 0, "sampled_news": sampled}

    with session_scope() as session:
        n = _update_lexicon(session, word_to_change, s.sentiment_online_learning_rate)
    logger.info("online sentiment: {} words updated from {} news items", n, sampled)
    return {"updated": n, "sampled_news": sampled, "unique_words": len(word_to_change)}


async def _real_price_change(symbol: str, ts: datetime, horizon_hours: int) -> float | None:
    """Запросить у биржи % изменение цены за horizon после ts."""
    from ..engine.trader import get_engine

    engine = get_engine()
    try:
        # берём дневные свечи, выберем ближайшие к ts и +horizon
        rows = await engine.exchange.fetch_ohlcv(symbol, timeframe="1h", limit=500)
    except Exception:
        return None
    if not rows:
        return None
    ts_ms = int(ts.timestamp() * 1000)
    end_ts = ts_ms + horizon_hours * 3600_000
    # найдём ближайшие свечи к ts и end_ts
    times = [r[0] for r in rows]
    start_price = _nearest_price(times, rows, ts_ms)
    end_price = _nearest_price(times, rows, end_ts)
    if start_price is None or end_price is None or start_price <= 0:
        return None
    return (end_price / start_price - 1) * 100


def _nearest_price(times: list[int], rows: list[list], target_ms: int) -> float | None:
    """Линейный поиск ближайшего ts (rows маленький)."""
    best_idx = None
    best_diff = float("inf")
    for i, t in enumerate(times):
        diff = abs(t - target_ms)
        if diff < best_diff:
            best_diff = diff
            best_idx = i
    if best_idx is None:
        return None
    return float(rows[best_idx][4])  # close price


def load_online_weights(session: Session, min_samples: int = 3) -> dict[str, float]:
    """Прочитать обученные веса с фильтром по числу samples."""
    rows = session.execute(
        select(OnlineLexicon).where(OnlineLexicon.samples >= min_samples)
    ).scalars().all()
    return {r.word: float(r.weight) for r in rows}


def combined_score(text: str, online_weights: dict[str, float]) -> float:
    """Расширенный scorer: статический лексикон + online learning.

    Возвращает score ∈ [-1, 1].
    """
    from .analyzer import score_text

    static = score_text(text).score
    if not online_weights:
        return static
    tokens = _extract_tokens(text)
    online_sum = sum(online_weights.get(t, 0.0) for t in tokens)
    online_count = sum(1 for t in tokens if t in online_weights)
    if online_count == 0:
        return static
    online_avg = online_sum / online_count
    # средневзвешенно: статический вклад × 0.7 + online × 0.3
    combined = 0.7 * static + 0.3 * online_avg
    return float(max(-1.0, min(1.0, combined)))


async def online_loop(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    if not s.sentiment_online_enabled:
        return
    interval = max(1800, s.sentiment_online_interval_hours * 3600)
    await asyncio.sleep(min(900, interval))
    while True:
        try:
            await run_online_learning_cycle(s)
        except Exception as exc:  # noqa: BLE001
            logger.exception("online sentiment cycle failed: {}", exc)
        await asyncio.sleep(interval)
