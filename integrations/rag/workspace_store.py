"""Workspace-scoped RAG helpers (Фаза C)."""

from __future__ import annotations

import os
import shutil

from integrations.rag.store import get_store, WS_ROOT, DEFAULT_DB


def ensure_workspace_store(workspace_id: str, seed_from_global: bool = True):
    """Создать изолированную БД знаний для workspace."""
    ws = (workspace_id or "").strip()
    if not ws:
        return get_store("")
    path = os.path.abspath(os.path.join(WS_ROOT, ws, "knowledge.db"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    store = get_store(ws)
    if seed_from_global and store.stats().get("total_chunks", 0) == 0:
        global_path = os.path.abspath(DEFAULT_DB)
        if os.path.exists(global_path) and global_path != path:
            shutil.copy2(global_path, path)
            from integrations.rag.store import clear_store_cache
            clear_store_cache()
            store = get_store(ws)
    return store
