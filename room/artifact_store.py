"""Артефакты агентов — проекты, код, презентации, 3D."""

import json
import os
import uuid
from datetime import datetime
from typing import Optional

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "artifacts")
INDEX_FILE = os.path.join(ARTIFACTS_DIR, "index.json")
MAX_PER_AGENT = 80
MAX_TOTAL = 500


def _ensure():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)


def _load_index() -> list:
    _ensure()
    if not os.path.exists(INDEX_FILE):
        return []
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_index(items: list) -> None:
    _ensure()
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(items[:MAX_TOTAL], f, ensure_ascii=False, indent=2)


def _persist_files(artifact_id: str, files: dict) -> dict:
    """Сохраняет бинарные файлы на диск; в JSON — метаданные."""
    if not files:
        return {}
    out = {}
    bin_dir = os.path.join(ARTIFACTS_DIR, artifact_id)
    for name, content in files.items():
        if isinstance(content, bytes):
            os.makedirs(bin_dir, exist_ok=True)
            safe = os.path.basename(name)
            fp = os.path.join(bin_dir, safe)
            with open(fp, "wb") as f:
                f.write(content)
            out[safe] = {"binary": True, "size": len(content), "download": f"/api/projects/{artifact_id}/file/{safe}"}
        else:
            out[name] = content
    return out


def save_artifact(agent_id: str, artifact: dict) -> dict:
    _ensure()
    entry = {
        "id": artifact.get("id") or f"art-{uuid.uuid4().hex[:12]}",
        "agent_id": agent_id,
        "agent_name": artifact.get("agent_name", ""),
        "agent_emoji": artifact.get("agent_emoji", ""),
        "type": artifact.get("type", "project"),
        "title": artifact.get("title", "Проект")[:200],
        "description": (artifact.get("description") or "")[:500],
        "task": (artifact.get("task") or "")[:500],
        "content": artifact.get("content") or "",
        "preview_html": artifact.get("preview_html") or "",
        "files": {},
        "tags": artifact.get("tags") or [],
        "status": artifact.get("status", "completed"),
        "revision_of": artifact.get("revision_of"),
        "version": 1,
        "created_at": artifact.get("created_at") or datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    if entry.get("revision_of"):
        prev = get_artifact(entry["revision_of"])
        entry["version"] = (prev.get("version") or 1) + 1 if prev else 2

    raw_files = artifact.get("files") or {}
    entry["files"] = _persist_files(entry["id"], raw_files)

    path = os.path.join(ARTIFACTS_DIR, f"{entry['id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False, indent=2)

    items = _load_index()
    items = [i for i in items if i.get("id") != entry["id"]]
    items.insert(0, {k: entry[k] for k in (
        "id", "agent_id", "agent_name", "agent_emoji", "type", "title",
        "description", "tags", "status", "created_at", "updated_at", "revision_of"
    )})
    agent_count = sum(1 for i in items if i.get("agent_id") == agent_id)
    if agent_count > MAX_PER_AGENT:
        to_drop = [i["id"] for i in items if i.get("agent_id") == agent_id][MAX_PER_AGENT:]
        items = [i for i in items if i["id"] not in to_drop]
        for drop_id in to_drop:
            fp = os.path.join(ARTIFACTS_DIR, f"{drop_id}.json")
            if os.path.exists(fp):
                os.remove(fp)
    _save_index(items)
    return entry


def get_artifact(artifact_id: str) -> Optional[dict]:
    path = os.path.join(ARTIFACTS_DIR, f"{artifact_id}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def get_agent_artifacts(agent_id: str, limit: int = 30) -> list:
    items = _load_index()
    return [i for i in items if i.get("agent_id") == agent_id][:limit]


def get_latest_artifact(agent_id: str) -> Optional[dict]:
    items = get_agent_artifacts(agent_id, limit=1)
    if not items:
        return None
    return get_artifact(items[0]["id"])


DELIVERABLE_TYPES = frozenset({
    "presentation", "model_3d", "ui", "site", "code", "document",
})
HIDDEN_ARTIFACT_TYPES = frozenset({
    "review", "plan", "tests", "architecture", "infra", "checklist",
})
AGENT_DELIVERABLE = {
    "presenter": {"presentation"},
    "modeler": {"model_3d"},
    "frontend": {"ui", "site", "code"},
    "backend": {"code"},
    "architect": {"architecture", "document"},
    "doc_writer": {"document"},
    "qa": set(),
    "reviewer": set(),
    "pm": set(),
    "devops": {"infra", "code"},
    "cursor": {"code"},
    "evaluator": set(),
    "security": {"document"},
}


def list_deliverables(limit: int = 100, agent_id: Optional[str] = None, art_type: Optional[str] = None) -> list:
    """Только финальные артефакты — по одному последнему на задачу/тип."""
    items = _load_index()
    filtered = []
    for i in items:
        t = i.get("type", "")
        aid = i.get("agent_id", "")
        if t in HIDDEN_ARTIFACT_TYPES:
            continue
        allowed = AGENT_DELIVERABLE.get(aid)
        if allowed is not None and allowed and t not in allowed:
            continue
        if t not in DELIVERABLE_TYPES and t not in ("document",):
            if t not in ("project",):
                continue
        if agent_id and aid != agent_id:
            continue
        if art_type and t != art_type:
            continue
        filtered.append(i)
    # dedupe by task title — keep newest
    seen_tasks = {}
    out = []
    for i in filtered:
        key = (i.get("task") or i.get("title") or i.get("id", "")).strip().lower()[:120]
        if not key:
            out.append(i)
            continue
        prev = seen_tasks.get(key)
        if not prev:
            seen_tasks[key] = i
            out.append(i)
        else:
            if (i.get("created_at") or "") > (prev.get("created_at") or ""):
                out.remove(prev)
                seen_tasks[key] = i
                out.insert(0, i)
    return out[:limit]


def clear_non_deliverables() -> int:
    items = _load_index()
    keep = list_deliverables(limit=MAX_TOTAL)
    keep_ids = {i["id"] for i in keep}
    removed = 0
    for i in items:
        if i.get("id") not in keep_ids:
            fp = os.path.join(ARTIFACTS_DIR, f"{i['id']}.json")
            if os.path.exists(fp):
                os.remove(fp)
            removed += 1
    _save_index(keep)
    return removed


def list_all(limit: int = 100, agent_id: Optional[str] = None, art_type: Optional[str] = None,
             deliverables_only: bool = False) -> list:
    if deliverables_only:
        return list_deliverables(limit=limit, agent_id=agent_id, art_type=art_type)
    items = _load_index()
    if agent_id:
        items = [i for i in items if i.get("agent_id") == agent_id]
    if art_type:
        items = [i for i in items if i.get("type") == art_type]
    return items[:limit]


def stats() -> dict:
    items = _load_index()
    by_agent = {}
    by_type = {}
    for i in items:
        by_agent[i.get("agent_id", "?")] = by_agent.get(i.get("agent_id", "?"), 0) + 1
        by_type[i.get("type", "?")] = by_type.get(i.get("type", "?"), 0) + 1
    return {"total": len(items), "by_agent": by_agent, "by_type": by_type}
