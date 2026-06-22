from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import Settings
from app.core.database import configure, init_db, session_scope
from app.models.db import OnlineLexicon
from app.sentiment.online import (
    _detect_symbol,
    _extract_tokens,
    _update_lexicon,
    combined_score,
    load_online_weights,
    run_online_learning_cycle,
)


@pytest.fixture()
def isolated_db(tmp_path):
    configure(f"sqlite:///{tmp_path}/o.db")
    init_db()


def test_extract_tokens_strips_stopwords():
    text = "Bitcoin rallies today after ETF approval and SEC ruling"
    tokens = _extract_tokens(text)
    assert "bitcoin" in tokens
    assert "rallies" in tokens
    assert "etf" in tokens
    assert "today" not in tokens  # stopword
    assert "the" not in tokens


def test_detect_symbol_matches_keywords():
    assert _detect_symbol("ethereum surges", ["BTC/USDT", "ETH/USDT"]) == "ETH/USDT"
    assert _detect_symbol("nothing crypto-y here", ["BTC/USDT"]) is None


def test_update_lexicon_writes_rows(isolated_db):
    deltas = {"rally": [0.05, 0.04, 0.06], "crash": [-0.08, -0.05]}
    with session_scope() as s:
        n = _update_lexicon(s, deltas, lr=0.5)
    assert n == 2
    with session_scope() as s:
        weights = load_online_weights(s, min_samples=1)
    assert weights["rally"] > 0
    assert weights["crash"] < 0


def test_lexicon_update_smooths_new_words_more(isolated_db):
    with session_scope() as s:
        s.add(OnlineLexicon(word="established", weight=0.1, samples=100))
    with session_scope() as s:
        _update_lexicon(s, {"established": [0.5], "fresh": [0.5]}, lr=0.5)
    with session_scope() as s:
        rows = {r.word: r.weight for r in s.query(OnlineLexicon).all()}
    # fresh ушёл сильнее в сторону 0.5, established почти не сдвинулся
    assert abs(rows["fresh"] - 0.5) < abs(rows["established"] - 0.5)


def test_combined_score_blends_static_and_online():
    text = "frobnicating the gadget"  # нет в static lexicon
    # online словарь даёт мощный сигнал
    online = {"frobnicating": 0.9, "gadget": 0.6}
    score = combined_score(text, online)
    # static = 0 (нейтрально), online средний ≈ 0.75 → итог 0.3 * 0.75 = 0.225
    assert score > 0.1


def test_combined_score_falls_back_to_static_without_online():
    text = "bitcoin rallies on ETF approval"
    s_static = combined_score(text, {})
    assert s_static > 0  # должен распознать как bullish


@pytest.mark.asyncio
async def test_run_online_learning_cycle_with_mocks(isolated_db):
    @dataclass
    class FakeNews:
        title: str
        summary: str
        published_at: datetime

    settings = Settings(
        symbols=["BTC/USDT", "ETH/USDT"],
        sentiment_online_enabled=True,
        sentiment_online_horizon_hours=8,
        sentiment_online_learning_rate=0.5,
    )
    base = datetime.now(timezone.utc) - timedelta(hours=12)
    news = [
        FakeNews("Bitcoin rallies hard", "BTC surge surge", base),
        FakeNews("Ethereum delisted", "ETH plunges", base + timedelta(minutes=10)),
    ]

    async def fake_news(): return news

    async def fake_price(symbol, ts, horizon):
        return 8.0 if symbol == "BTC/USDT" else -6.0

    result = await run_online_learning_cycle(
        settings, news_fetcher=fake_news, fetch_price_change=fake_price,
    )
    assert result["sampled_news"] == 2
    assert result["updated"] >= 2

    with session_scope() as s:
        weights = load_online_weights(s, min_samples=1)
    # хотя бы одно из слов BTC-связанных стало положительным,
    # хотя бы одно из ETH-связанных — отрицательным
    bull = [w for word, w in weights.items() if word in {"rallies", "rally", "surge"}]
    bear = [w for word, w in weights.items() if word in {"delisted", "plunges"}]
    assert bull and any(x > 0 for x in bull)
    assert bear and any(x < 0 for x in bear)
