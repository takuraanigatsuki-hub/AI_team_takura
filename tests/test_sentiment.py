from app.sentiment import aggregate_sentiment, score_text


def test_score_text_bullish():
    s = score_text("Bitcoin rallies to all-time high on ETF approval")
    assert s.label == "bullish"
    assert s.score > 0.3


def test_score_text_bearish():
    s = score_text("Major exchange hacked, BTC plunges as SEC opens investigation")
    assert s.label == "bearish"
    assert s.score < -0.3


def test_score_text_neutral_for_empty_or_unknown():
    assert score_text("").label == "neutral"
    assert score_text("the quick brown fox jumps over").label == "neutral"


def test_aggregate_sentiment_per_symbol():
    news = [
        {"title": "Bitcoin surges after ETF approval", "summary": "BTC rallies",
         "source": "x", "published_at": None},
        {"title": "Ethereum delisted by major exchange", "summary": "ETH plunges",
         "source": "x", "published_at": None},
        {"title": "Random article about cats", "summary": "no crypto here",
         "source": "x", "published_at": None},
    ]
    agg = aggregate_sentiment(news, symbols=["BTC/USDT", "ETH/USDT"], max_age_hours=None)
    assert "BTC/USDT" in agg and agg["BTC/USDT"].label == "bullish"
    assert "ETH/USDT" in agg and agg["ETH/USDT"].label == "bearish"


def test_aggregate_sentiment_age_filter():
    from datetime import datetime, timedelta, timezone
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    news = [{"title": "Bitcoin rallies", "summary": "ATH", "source": "x",
             "published_at": old}]
    agg = aggregate_sentiment(news, symbols=["BTC/USDT"], max_age_hours=48)
    assert agg == {}  # старая новость отброшена
