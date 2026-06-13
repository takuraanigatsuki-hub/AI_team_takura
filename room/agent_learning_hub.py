"""Хаб проектов обучения — по одному разделу на каждого агента."""

from __future__ import annotations

from typing import Optional

from knowledge_store import KnowledgeStore
from room.learning_projects import AGENT_META, LearningProjects

AGENT_TAB_ORDER = [
    "pm", "architect", "backend", "frontend", "qa", "reviewer",
    "doc_writer", "devops", "cursor", "presenter", "modeler", "evaluator",
]

_TYPE_LABELS = {
    "presentation": "Презентация",
    "model_3d": "3D",
    "ui": "UI",
    "site": "Сайт",
    "code": "Код",
    "document": "Документ",
}


def _topic_as_project(agent_id: str, topic: dict, idx: int) -> dict:
    title = (topic.get("title") or topic.get("topic") or "Изученная тема")[:120]
    summary = (topic.get("summary") or topic.get("content") or "")[:600]
    return {
        "id": f"knowledge-{agent_id}-{idx}",
        "kind": "knowledge",
        "title": title,
        "description": summary,
        "topic": topic.get("topic", ""),
        "source": topic.get("source", "learning"),
        "created_at": topic.get("timestamp") or topic.get("learned_at") or "",
        "previewable": bool(summary),
    }


def _learning_entry_as_project(entry: dict, agent_id: str) -> dict:
    kind = entry.get("kind") or "practice"
    agents = entry.get("agent_ids") or []
    return {
        "id": entry.get("id", ""),
        "kind": "collaborative" if kind == "collaborative" or len(agents) > 1 else "practice",
        "title": entry.get("title") or "Проект практики",
        "description": entry.get("description") or "",
        "topic": entry.get("topic") or "",
        "status": entry.get("status") or "active",
        "last_score": entry.get("last_score"),
        "agent_ids": agents,
        "owner_agent_id": entry.get("owner_agent_id") or agent_id,
        "created_at": entry.get("created_at") or "",
        "previewable": True,
    }


def _sonya_project_as_item(p: dict) -> dict:
    return {
        "id": p.get("id", ""),
        "kind": "sonya_studio",
        "title": p.get("title") or "UI проект",
        "description": p.get("description") or "",
        "status": p.get("status") or "draft",
        "theme": p.get("theme") or "",
        "colors": p.get("colors") or [],
        "version_count": p.get("version_count") or 1,
        "created_at": p.get("updated_at") or p.get("created_at") or "",
        "previewable": True,
    }


def _deliverable_as_project(meta: dict) -> dict:
    return {
        "id": meta.get("id", ""),
        "kind": "deliverable",
        "title": meta.get("title") or "Артефакт",
        "description": (meta.get("preview") or meta.get("summary") or "")[:400],
        "artifact_type": meta.get("type") or "",
        "type_label": _TYPE_LABELS.get(meta.get("type", ""), meta.get("type") or "Артефакт"),
        "has_preview": bool(meta.get("has_preview")),
        "created_at": meta.get("created_at") or "",
        "previewable": bool(meta.get("has_preview")),
    }


def projects_for_agent(
    agent_id: str,
    *,
    store: Optional[LearningProjects] = None,
    privileged: bool = True,
    user_id: str = "",
    task_history=None,
    deliverable_limit: int = 24,
    knowledge_limit: int = 20,
) -> list[dict]:
    store = store or LearningProjects()
    out: list[dict] = []
    seen: set[str] = set()

    def add(item: dict):
        pid = item.get("id") or ""
        if not pid or pid in seen:
            return
        seen.add(pid)
        out.append(item)

    if agent_id == "frontend":
        try:
            from integrations.sonya_studio import list_projects as list_sonya
            for p in list_sonya("learning"):
                add(_sonya_project_as_item(p))
        except Exception:
            pass

    for entry in store.projects:
        owner = entry.get("owner_agent_id")
        agents = entry.get("agent_ids") or []
        if owner == agent_id or agent_id in agents:
            add(_learning_entry_as_project(entry, agent_id))

    for idx, topic in enumerate(KnowledgeStore.load(agent_id)[-knowledge_limit:][::-1]):
        add(_topic_as_project(agent_id, topic, idx))

    try:
        from room.artifact_store import get_artifact, list_deliverables
        for meta in list_deliverables(
            limit=deliverable_limit,
            agent_id=agent_id,
            user_id=user_id,
            task_history=task_history,
            privileged=privileged,
        ):
            art = get_artifact(meta["id"])
            if art:
                preview = art.get("preview_html") or art.get("content", "")
                meta = {**meta, "has_preview": bool(preview)}
            add(_deliverable_as_project(meta))
    except Exception:
        pass

    out.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return out


def build_agent_learning_hub(
    *,
    privileged: bool = True,
    user_id: str = "",
    task_history=None,
) -> dict:
    store = LearningProjects()
    agents_out = []
    for agent_id in AGENT_TAB_ORDER:
        emoji, name = AGENT_META.get(agent_id, ("🤖", agent_id))
        projects = projects_for_agent(
            agent_id,
            store=store,
            privileged=privileged,
            user_id=user_id,
            task_history=task_history,
        )
        knowledge_count = len(KnowledgeStore.load(agent_id))
        agents_out.append({
            "agent_id": agent_id,
            "name": name,
            "emoji": emoji,
            "knowledge_count": knowledge_count,
            "projects_count": len(projects),
            "projects": projects,
        })
    return {
        "agents": agents_out,
        "tab_order": AGENT_TAB_ORDER,
    }
