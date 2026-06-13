"""RAG retrieval для агентов."""

from __future__ import annotations

from integrations.rag.store import get_store


def retrieve_for_agent(agent_id: str, query: str, limit: int = 6) -> list[dict]:
    if not query or not agent_id:
        return []
    try:
        return get_store().search(agent_id, query, limit=limit)
    except Exception:
        return []


def retrieve_context_text(agent_id: str, query: str, limit: int = 5, max_chars: int = 2400) -> str:
    hits = retrieve_for_agent(agent_id, query, limit=limit)
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
