"""Артефакты агентов — проекты, код, презентации, 3D."""

import json
import os
import shutil
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
    "presentation", "model_3d", "ui", "site", "code", "document", "project",
})
HIDDEN_ARTIFACT_TYPES = frozenset({
    "review", "plan", "tests", "architecture", "infra", "checklist",
})
# Агенты, чьи артефакты показываем во вкладке «Проекты» (пустой set = не показывать)
AGENT_DELIVERABLE = {
    "presenter": frozenset({"presentation"}),
    "modeler": frozenset({"model_3d"}),
    "frontend": frozenset({"ui", "site", "code", "project"}),
    "backend": frozenset({"code"}),
    "architect": frozenset({"document"}),
    "doc_writer": frozenset({"document"}),
    "devops": frozenset({"code", "infra"}),
    "cursor": frozenset({"code"}),
    "security": frozenset({"document"}),
    "qa": frozenset(),
    "reviewer": frozenset(),
    "pm": frozenset(),
    "evaluator": frozenset(),
}
AGENT_PRIORITY = {
    "frontend": 100,
    "presenter": 90,
    "modeler": 85,
    "cursor": 80,
    "backend": 70,
    "doc_writer": 65,
    "devops": 60,
    "architect": 50,
    "security": 40,
}


def _artifact_allowed(meta: dict) -> bool:
    t = meta.get("type", "")
    aid = meta.get("agent_id", "")
    if t in HIDDEN_ARTIFACT_TYPES:
        return False
    if aid not in AGENT_DELIVERABLE:
        return t in DELIVERABLE_TYPES
    allowed = AGENT_DELIVERABLE[aid]
    if not allowed:
        return False
    return t in allowed


def _task_key(meta: dict) -> str:
    raw = (meta.get("task") or meta.get("title") or meta.get("id") or "").strip().lower()
    for prefix in ("сделай сайт:", "сверстать", "создай", "rest api", "review:", "оценка"):
        if raw.startswith(prefix):
            raw = raw[len(prefix):].strip()
    return raw[:100] or meta.get("id", "")


def _pick_better(a: dict, b: dict) -> dict:
    pa = AGENT_PRIORITY.get(a.get("agent_id", ""), 0)
    pb = AGENT_PRIORITY.get(b.get("agent_id", ""), 0)
    if pa != pb:
        return a if pa >= pb else b
    ca = a.get("created_at") or ""
    cb = b.get("created_at") or ""
    return a if ca >= cb else b


def list_deliverables(limit: int = 100, agent_id: Optional[str] = None, art_type: Optional[str] = None) -> list:
    """Финальные артефакты — без QA/review/evaluator, один лучший на задачу."""
    items = _load_index()
    filtered = []
    for i in items:
        if not _artifact_allowed(i):
            continue
        if agent_id and i.get("agent_id") != agent_id:
            continue
        if art_type and i.get("type") != art_type:
            continue
        filtered.append(i)

    best_by_task: dict[str, dict] = {}
    orphans: list = []
    for i in filtered:
        key = _task_key(i)
        if not key:
            orphans.append(i)
            continue
        prev = best_by_task.get(key)
        best_by_task[key] = i if not prev else _pick_better(prev, i)

    out = list(best_by_task.values()) + orphans
    out.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return out[:limit]


def _delete_artifact_files(artifact_id: str) -> None:
    fp = os.path.join(ARTIFACTS_DIR, f"{artifact_id}.json")
    if os.path.exists(fp):
        os.remove(fp)
    bin_dir = os.path.join(ARTIFACTS_DIR, artifact_id)
    if os.path.isdir(bin_dir):
        shutil.rmtree(bin_dir, ignore_errors=True)


def clear_non_deliverables() -> dict:
    items = _load_index()
    keep = list_deliverables(limit=MAX_TOTAL)
    keep_ids = {i["id"] for i in keep}
    removed = 0
    for i in items:
        if i.get("id") not in keep_ids:
            _delete_artifact_files(i["id"])
            removed += 1
    _save_index(keep)
    return {"removed": removed, "kept": len(keep)}


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
