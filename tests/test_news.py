import asyncio

import pytest

from app.news.feeds import NewsItem, NewsService


@pytest.mark.asyncio
async def test_news_service_uses_cache(monkeypatch):
    svc = NewsService(feeds=["https://example.com/feed"], ttl_seconds=60)
    calls = {"n": 0}

    def fake_sync():
        calls["n"] += 1
        return [
            NewsItem(title="BTC hits new high", link="https://x/1",
                     source="x", summary="", published_at=None),
            NewsItem(title="ETH merge update", link="https://x/2",
                     source="x", summary="", published_at=None),
        ]

    monkeypatch.setattr(svc, "_fetch_sync", fake_sync)
    a = await svc.fetch(limit=10)
    b = await svc.fetch(limit=10)
    assert calls["n"] == 1  # cache hit
    assert len(a) == 2 and len(b) == 2


@pytest.mark.asyncio
async def test_news_search_matches_terms(monkeypatch):
    svc = NewsService(feeds=["https://example.com/feed"], ttl_seconds=60)
    items = [
        NewsItem(title="BTC hits new high", link="https://x/1",
                 source="x", summary="bitcoin rally", published_at=None),
        NewsItem(title="ETH merge update", link="https://x/2",
                 source="x", summary="ethereum smooth", published_at=None),
        NewsItem(title="SEC issues guidance", link="https://x/3",
                 source="x", summary="regulators speak", published_at=None),
    ]
    monkeypatch.setattr(svc, "_fetch_sync", lambda: items)
    found = await svc.search("ethereum", limit=5)
    assert len(found) == 1
    assert found[0].title.startswith("ETH")
