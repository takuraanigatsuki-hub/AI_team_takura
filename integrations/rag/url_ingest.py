"""Ingest public documentation URLs into RAG (FTS)."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import urlparse

import httpx

from integrations.rag.ingest import ingest_entry

DEFAULT_DOC_URLS: dict[str, list[dict]] = {
    "backend": [
        {"url": "https://fastapi.tiangolo.com/tutorial/first-steps/", "title": "FastAPI First Steps"},
        {"url": "https://fastapi.tiangolo.com/tutorial/path-params/", "title": "FastAPI Path Params"},
        {"url": "https://fastapi.tiangolo.com/tutorial/query-params/", "title": "FastAPI Query Params"},
    ],
    "frontend": [
        {"url": "https://react.dev/learn", "title": "React Learn"},
        {"url": "https://react.dev/reference/react/hooks", "title": "React Hooks"},
    ],
    "security": [
        {"url": "https://owasp.org/www-project-top-ten/", "title": "OWASP Top 10"},
    ],
    "architect": [
        {"url": "https://12factor.net/", "title": "Twelve-Factor App"},
    ],
}


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = unescape(re.sub(r"\s+", " ", text)).strip()
    return text


def _chunk_text(text: str, max_len: int = 1200) -> list[str]:
    if len(text) <= max_len:
        return [text]
    parts = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_len)
        if end < len(text):
            cut = text.rfind(". ", start, end)
            if cut > start + 200:
                end = cut + 1
        parts.append(text[start:end].strip())
        start = end
    return [p for p in parts if len(p) > 80]


async def fetch_url_text(url: str, timeout: float = 25.0) -> str:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "TakuraRAG/1.0"})
        resp.raise_for_status()
        return _strip_html(resp.text)


async def ingest_url(
    agent_id: str,
    url: str,
    title: str = "",
    pack_id: str = "url-docs",
) -> dict:
    url = (url or "").strip()
    if not url:
        return {"ok": False, "error": "url required"}
    host = urlparse(url).netloc or url
    title = title or host
    try:
        raw = await fetch_url_text(url)
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}

    chunks = _chunk_text(raw)
    if not chunks:
        return {"ok": False, "url": url, "error": "empty content"}

    for i, chunk in enumerate(chunks):
        ingest_entry(
            agent_id,
            {
                "title": f"{title} ({i + 1}/{len(chunks)})",
                "content": chunk,
                "keywords": f"{host} {title}",
                "source": url,
            },
            pack_id=pack_id,
        )
    return {"ok": True, "url": url, "agent_id": agent_id, "chunks": len(chunks)}


async def ingest_default_docs(agent_ids: list[str] | None = None) -> dict:
    report: dict[str, list] = {"ingested": [], "errors": []}
    for agent_id, items in DEFAULT_DOC_URLS.items():
        if agent_ids and agent_id not in agent_ids:
            continue
        for item in items:
            result = await ingest_url(agent_id, item["url"], item.get("title", ""))
            if result.get("ok"):
                report["ingested"].append(result)
            else:
                report["errors"].append(result)
    from integrations.rag.ingest import get_index_stats
    report["index"] = get_index_stats()
    return report
