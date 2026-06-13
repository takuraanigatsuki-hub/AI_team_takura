"""Индексация embeddings для hybrid RAG."""

from __future__ import annotations

from integrations.rag.embeddings import embed_texts, embedding_to_blob, is_configured
from integrations.rag.store import get_store


async def embed_all_chunks(batch_size: int = 64, force: bool = False) -> dict:
    if not is_configured():
        return {"ok": False, "reason": "OPENAI_API_KEY not set"}

    store = get_store()
    if not force and store.count_vectors() > 0:
        stats = store.stats()
        if stats.get("vector_chunks", 0) >= stats.get("total_chunks", 0) * 0.9:
            return {"ok": True, "skipped": True, "vectors": store.count_vectors()}

    chunks = store.list_fts_chunks(limit=10000)
    embedded = 0
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [f"{c.get('title', '')}\n{c.get('content', '')}" for c in batch]
        vecs = await embed_texts(texts)
        for c, vec in zip(batch, vecs):
            store.set_embedding(
                c["chunk_id"],
                c["agent_id"],
                c.get("title", ""),
                c.get("content", ""),
                embedding_to_blob(vec),
            )
            embedded += 1

    store.set_meta("vectors_embedded", str(embedded))
    return {"ok": True, "embedded": embedded, "vectors": store.count_vectors()}


async def ensure_embeddings() -> dict:
    try:
        return await embed_all_chunks(force=False)
    except Exception as e:
        return {"ok": False, "error": str(e)}
