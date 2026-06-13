"""Hybrid RAG retrieval — FTS + vector embeddings."""

from __future__ import annotations

import config as cfg
from integrations.rag.store import get_store


async def retrieve_for_agent(agent_id: str, query: str, limit: int = 6) -> list[dict]:
    if not query or not agent_id:
        return []
    store = get_store()
    fts_hits = store.search(agent_id, query, limit=limit)

    if not cfg.config.get("rag_hybrid", True):
        return fts_hits

    try:
        from integrations.rag.embeddings import embed_query, is_configured
        if not is_configured() or store.count_vectors() == 0:
            return fts_hits
        qvec = await embed_query(query)
        if not qvec:
            return fts_hits
        vec_hits = store.vector_search(agent_id, qvec, limit=limit)
    except Exception:
        return fts_hits

    return _merge_hits(fts_hits, vec_hits, limit)


def _merge_hits(fts: list[dict], vec: list[dict], limit: int) -> list[dict]:
    combined: dict[str, dict] = {}
    for h in fts:
        key = (h.get("title") or "") + (h.get("content") or "")[:80]
        combined[key] = {**h, "hybrid_score": 0.4 * _norm_bm25(h.get("score", 0))}
    for h in vec:
        key = (h.get("title") or "") + (h.get("content") or "")[:80]
        vs = h.get("vector_score", h.get("score", 0))
        if key in combined:
            combined[key]["hybrid_score"] = combined[key].get("hybrid_score", 0) + 0.6 * vs
        else:
            combined[key] = {**h, "hybrid_score": 0.6 * vs}
    ranked = sorted(combined.values(), key=lambda x: -x.get("hybrid_score", 0))
    return ranked[:limit]


def _norm_bm25(score) -> float:
    try:
        s = float(score)
        return max(0.0, min(1.0, 1.0 / (1.0 + abs(s))))
    except Exception:
        return 0.3


def retrieve_context_text(agent_id: str, query: str, limit: int = 5, max_chars: int = 2400) -> str:
    hits = get_store().search(agent_id, query, limit=limit)
    if not hits:
        return ""
    lines = []
    used = 0
    for h in hits:
        title = h.get("title", "")
        content = (h.get("content") or "")[:500]
        line = f"- **{title}**: {content}"
        if used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines)


async def retrieve_context_text_async(agent_id: str, query: str, limit: int = 5, max_chars: int = 2400) -> str:
    hits = await retrieve_for_agent(agent_id, query, limit=limit)
    if not hits:
        return ""
    lines = []
    used = 0
    for h in hits:
        title = h.get("title", "")
        content = (h.get("content") or "")[:500]
        line = f"- **{title}**: {content}"
        if used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
    return "\n".join(lines)
