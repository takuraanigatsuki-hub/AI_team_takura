"""Bulk ingest corpora + Wikipedia summaries (Фаза C)."""

from __future__ import annotations

import httpx

from integrations.rag.corpora import CORPORA_URLS, WIKIPEDIA_TOPICS
from integrations.rag.ingest import ingest_entry
from integrations.rag.url_ingest import ingest_url


async def ingest_wikipedia_topic(agent_id: str, topic: str, pack_id: str = "wiki") -> dict:
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "TakuraRAG/1.0"})
            if r.status_code != 200:
                return {"ok": False, "topic": topic, "error": f"HTTP {r.status_code}"}
            data = r.json()
        extract = (data.get("extract") or "").strip()
        if len(extract) < 80:
            return {"ok": False, "topic": topic, "error": "short extract"}
        ingest_entry(
            agent_id,
            {
                "title": data.get("title") or topic,
                "content": extract,
                "keywords": f"wikipedia {topic}",
                "source": data.get("content_urls", {}).get("desktop", {}).get("page", url),
            },
            pack_id=pack_id,
        )
        return {"ok": True, "topic": topic, "agent_id": agent_id}
    except Exception as e:
        return {"ok": False, "topic": topic, "error": str(e)}


async def ingest_all_corpora(
    include_wikipedia: bool = True,
    include_urls: bool = True,
    workspace_id: str = "",
) -> dict:
    pack_id = f"corpora-ws-{workspace_id}" if workspace_id else "corpora-v1"
    report = {"urls": [], "wiki": [], "errors": []}

    if include_urls:
        for agent_id, items in CORPORA_URLS.items():
            for item in items:
                result = await ingest_url(agent_id, item["url"], item.get("title", ""), pack_id=pack_id)
                if result.get("ok"):
                    report["urls"].append(result)
                else:
                    report["errors"].append(result)

    if include_wikipedia:
        for agent_id, topics in WIKIPEDIA_TOPICS.items():
            for topic in topics:
                result = await ingest_wikipedia_topic(agent_id, topic, pack_id=pack_id)
                if result.get("ok"):
                    report["wiki"].append(result)
                else:
                    report["errors"].append(result)

    from integrations.rag.ingest import get_index_stats
    report["index"] = get_index_stats()
    return report
