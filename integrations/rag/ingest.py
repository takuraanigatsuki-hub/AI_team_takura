"""Загрузка knowledge packs в RAG."""

from __future__ import annotations

from datetime import datetime, timezone

from integrations.rag.store import get_store


def ingest_entry(agent_id: str, entry: dict, pack_id: str = "v1") -> None:
    store = get_store()
    kw = entry.get("keywords") or []
    if isinstance(kw, list):
        kw = " ".join(kw)
    store.add_entry(
        agent_id=agent_id,
        title=entry.get("title") or entry.get("topic", ""),
        content=entry.get("content") or entry.get("summary", ""),
        keywords=kw,
        source=entry.get("source", "pack"),
        pack_id=pack_id,
    )


def ingest_agent_pack(agent_id: str, entries: list, pack_id: str = "v1", replace: bool = False) -> int:
    store = get_store()
    if replace:
        store.clear_agent(agent_id)
    n = 0
    for e in entries:
        if not e.get("content") and not e.get("summary"):
            continue
        if not e.get("title") and not e.get("topic"):
            continue
        ingest_entry(agent_id, e, pack_id=pack_id)
        n += 1
    return n


def ingest_all_packs(replace: bool = False) -> dict:
    from knowledge_packs.packs_data import get_all_packs

    if replace:
        get_store().clear_all()

    report = {}
    total = 0
    for agent_id, entries in get_all_packs().items():
        report[agent_id] = ingest_agent_pack(agent_id, entries, replace=False)
        total += report[agent_id]

    store = get_store()
    store.set_meta("last_ingest", datetime.now(timezone.utc).isoformat())
    store.set_meta("pack_version", "v1")
    store.set_meta("total_entries", str(total))
    return {"agents": report, "total": total}


def get_index_stats() -> dict:
    return get_store().stats()


def ensure_indexed(min_total: int = 100) -> dict:
    """Индексировать packs при старте, если база пустая или устарела."""
    stats = get_index_stats()
    total = stats.get("total_chunks", 0)
    if total >= min_total:
        return {"skipped": True, "total": total, "reason": "already indexed"}

    result = ingest_all_packs(replace=total == 0)
    result["skipped"] = False
    return result
