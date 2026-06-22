"""Sentiment-анализ крипто-новостей.

Подход 1: лексикон, заточенный под крипту — без зависимостей и LLM-ключей.
Подход 2: при наличии LLM_API_KEY — можно классифицировать через LLM
           (тяжелее, точнее на длинных текстах).
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone


BULLISH = {
    "rally": 1, "surge": 1, "soar": 1, "gain": 0.5, "gains": 0.5, "rises": 0.5,
    "rise": 0.5, "rallies": 1, "breakout": 1, "bullish": 1, "bull": 0.7,
    "all-time-high": 1.2, "ath": 1.2, "record-high": 1.2,
    "etf": 0.7, "approval": 0.8, "approved": 0.8, "adoption": 0.6, "partnership": 0.6,
    "listing": 0.5, "listed": 0.5, "integration": 0.4, "launches": 0.4,
    "upgrade": 0.5, "merger": 0.4, "acquires": 0.4, "acquisition": 0.4,
    "buyback": 0.5, "halving": 0.4, "inflow": 0.6, "inflows": 0.6,
}

BEARISH = {
    "crash": 1, "plunge": 1, "tumble": 0.9, "drop": 0.5, "drops": 0.5,
    "fall": 0.5, "falls": 0.5, "sell-off": 0.9, "selloff": 0.9, "dump": 0.8,
    "bearish": 1, "bear": 0.7, "correction": 0.4, "downtrend": 0.6,
    "hack": 1.2, "hacked": 1.2, "exploit": 1.2, "stolen": 1, "stolen-funds": 1.2,
    "scam": 1.2, "rugpull": 1.2, "rug-pull": 1.2, "rug": 0.7,
    "sec": 0.6, "lawsuit": 1, "subpoena": 0.9, "investigation": 0.7,
    "regulation": 0.5, "ban": 1, "bans": 1, "banned": 1,
    "delisting": 1, "delisted": 1, "halt": 0.6, "halts": 0.6, "halted": 0.6,
    "bankruptcy": 1.5, "bankrupt": 1.5, "insolvent": 1.5, "default": 1,
    "liquidation": 0.8, "liquidations": 0.8,
    "fud": 0.6, "fear": 0.5,
    "outflow": 0.5, "outflows": 0.5,
}

# Многословные триггеры — проверяются до токенизации
PHRASES = [
    ("all time high", 1.2),
    ("record high", 1.2),
    ("etf approval", 1.5),
    ("etf approved", 1.5),
    ("rug pull", -1.3),
    ("flash crash", -1.2),
    ("interest rate cut", 0.6),
    ("interest rate hike", -0.5),
    ("rate hike", -0.4),
    ("rate cut", 0.5),
]

TOKEN_RE = re.compile(r"[a-z][a-z\-0-9]+")

# Кейворды → крипто-инструмент (грубо, для аггрегации per-symbol)
COIN_KEYS = {
    "BTC/USDT": {"bitcoin", "btc"},
    "ETH/USDT": {"ethereum", "eth", "ether"},
    "SOL/USDT": {"solana", "sol"},
    "BNB/USDT": {"binance", "bnb"},
    "XRP/USDT": {"ripple", "xrp"},
    "DOGE/USDT": {"dogecoin", "doge"},
    "ADA/USDT": {"cardano", "ada"},
    "AVAX/USDT": {"avalanche", "avax"},
    "MATIC/USDT": {"polygon", "matic"},
    "DOT/USDT": {"polkadot", "dot"},
}


@dataclass
class SentimentScore:
    score: float  # в диапазоне [-1, 1]
    pos_hits: int
    neg_hits: int
    tokens: int
    label: str  # "bullish" | "bearish" | "neutral"


def score_text(text: str) -> SentimentScore:
    if not text:
        return SentimentScore(0.0, 0, 0, 0, "neutral")
    raw = text.lower()
    pos = 0.0
    neg = 0.0
    pos_hits = 0
    neg_hits = 0

    for phrase, weight in PHRASES:
        if phrase in raw:
            if weight > 0:
                pos += weight
                pos_hits += 1
            else:
                neg += -weight
                neg_hits += 1

    tokens = TOKEN_RE.findall(raw)
    for t in tokens:
        if t in BULLISH:
            pos += BULLISH[t]
            pos_hits += 1
        elif t in BEARISH:
            neg += BEARISH[t]
            neg_hits += 1

    total = pos + neg
    if total <= 0:
        return SentimentScore(0.0, 0, 0, len(tokens), "neutral")
    raw_score = (pos - neg) / total  # [-1, 1]
    label = "bullish" if raw_score > 0.15 else ("bearish" if raw_score < -0.15 else "neutral")
    return SentimentScore(
        score=round(float(raw_score), 4),
        pos_hits=pos_hits,
        neg_hits=neg_hits,
        tokens=len(tokens),
        label=label,
    )


@dataclass
class AggregatedSentiment:
    symbol: str
    score: float
    label: str
    matched_articles: int
    sample_titles: list[str]

    def as_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "score": self.score,
            "label": self.label,
            "matched_articles": self.matched_articles,
            "sample_titles": self.sample_titles,
        }


def aggregate_sentiment(
    news_items: list[dict],
    symbols: list[str] | None = None,
    *,
    max_age_hours: int | None = 48,
) -> dict[str, AggregatedSentiment]:
    """Агрегировать сентимент по списку новостей и набору символов.

    news_items: список dict вида {title, summary, source, published_at(isoformat|None)}.
    """
    if not news_items:
        return {}
    symbols = symbols or list(COIN_KEYS.keys())
    now = datetime.now(timezone.utc)

    by_symbol_scores: dict[str, list[tuple[float, str]]] = defaultdict(list)
    matches: dict[str, int] = defaultdict(int)
    titles_keep: dict[str, list[str]] = defaultdict(list)

    for item in news_items:
        text = (item.get("title", "") + " " + item.get("summary", "")).lower()
        if max_age_hours is not None:
            published = item.get("published_at")
            if isinstance(published, str):
                try:
                    pub = datetime.fromisoformat(published.replace("Z", "+00:00"))
                except ValueError:
                    pub = None
                if pub and (now - pub).total_seconds() > max_age_hours * 3600:
                    continue

        s = score_text(text)
        if s.tokens == 0:
            continue

        for symbol in symbols:
            keys = COIN_KEYS.get(symbol, set())
            if any(k in text for k in keys):
                by_symbol_scores[symbol].append((s.score, item.get("title", "")))
                matches[symbol] += 1
                if len(titles_keep[symbol]) < 3 and item.get("title"):
                    titles_keep[symbol].append(item["title"])

    out: dict[str, AggregatedSentiment] = {}
    for symbol, scores in by_symbol_scores.items():
        if not scores:
            continue
        avg = sum(s for s, _ in scores) / len(scores)
        label = "bullish" if avg > 0.15 else ("bearish" if avg < -0.15 else "neutral")
        out[symbol] = AggregatedSentiment(
            symbol=symbol,
            score=round(avg, 4),
            label=label,
            matched_articles=matches[symbol],
            sample_titles=titles_keep[symbol],
        )
    return out
