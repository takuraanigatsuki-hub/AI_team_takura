"""Лёгкий RSS-агрегатор: читает несколько крипто-новостных лент без API-ключей."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import feedparser

from ..core.config import get_settings
from ..core.logging import logger


DEFAULT_FEEDS = [
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://cointelegraph.com/rss",
    "https://decrypt.co/feed",
    "https://bitcoinmagazine.com/.rss/full/",
]


@dataclass
class NewsItem:
    title: str
    link: str
    source: str
    summary: str
    published_at: datetime | None

    def as_dict(self) -> dict:
        return {
            "title": self.title,
            "link": self.link,
            "source": self.source,
            "summary": self.summary,
            "published_at": (
                self.published_at.isoformat() if self.published_at else None
            ),
        }


class NewsService:
    """Кэширующий fetcher RSS-фидов. Один TTL-слой на все ленты."""

    def __init__(
        self,
        feeds: list[str] | None = None,
        ttl_seconds: int = 300,
        user_agent: str = "trade-bot/0.1",
        request_timeout: float = 8.0,
    ) -> None:
        self.feeds = feeds or list(DEFAULT_FEEDS)
        self.ttl = ttl_seconds
        self.user_agent = user_agent
        self.request_timeout = request_timeout
        self._cache: tuple[float, list[NewsItem]] | None = None
        self._lock = asyncio.Lock()

    async def fetch(self, limit: int = 30, force: bool = False) -> list[NewsItem]:
        async with self._lock:
            if not force and self._cache is not None:
                stored_at, items = self._cache
                if time.monotonic() - stored_at < self.ttl:
                    return items[:limit]
            items = await asyncio.to_thread(self._fetch_sync)
            self._cache = (time.monotonic(), items)
            return items[:limit]

    def _fetch_sync(self) -> list[NewsItem]:
        out: list[NewsItem] = []
        for feed_url in self.feeds:
            try:
                parsed = feedparser.parse(
                    feed_url,
                    agent=self.user_agent,
                    request_headers={"User-Agent": self.user_agent},
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("rss fetch failed for {}: {}", feed_url, exc)
                continue
            source = (
                getattr(parsed.feed, "title", None)
                or _domain_of(feed_url)
            )
            for entry in parsed.entries[:25]:
                published = _parse_time(entry)
                summary = (
                    getattr(entry, "summary", "")
                    or getattr(entry, "description", "")
                )
                out.append(
                    NewsItem(
                        title=str(getattr(entry, "title", "")).strip(),
                        link=str(getattr(entry, "link", "")).strip(),
                        source=str(source).strip(),
                        summary=_clean_summary(summary),
                        published_at=published,
                    )
                )
        out.sort(key=lambda i: i.published_at or datetime.fromtimestamp(0, timezone.utc),
                 reverse=True)
        return out

    async def search(self, query: str, limit: int = 10) -> list[NewsItem]:
        """Простой in-memory поиск по заголовкам/summary последних новостей."""
        items = await self.fetch(limit=200)
        q = query.lower().strip()
        if not q:
            return items[:limit]
        terms = [t for t in q.split() if t]
        scored: list[tuple[int, NewsItem]] = []
        for item in items:
            text = f"{item.title} {item.summary}".lower()
            score = sum(text.count(term) for term in terms)
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda kv: kv[0], reverse=True)
        return [item for _, item in scored[:limit]]


def _parse_time(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = getattr(entry, key, None)
        if value:
            try:
                return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc)
            except (TypeError, ValueError, OverflowError):
                continue
    return None


def _clean_summary(html: str) -> str:
    import re

    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:280]


def _domain_of(url: str) -> str:
    from urllib.parse import urlparse

    return urlparse(url).netloc or url


_singleton: NewsService | None = None


def get_news_service() -> NewsService:
    global _singleton
    if _singleton is None:
        # Можно расширить конфигом, пока — дефолтный набор.
        _singleton = NewsService()
    return _singleton


def set_news_service(svc: NewsService | None) -> None:
    global _singleton
    _singleton = svc
