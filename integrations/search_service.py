"""Глобальный поиск по данным комнаты."""

from typing import Any, Optional


def _match(query: str, *parts: Any) -> bool:
    hay = " ".join(str(p or "") for p in parts).lower()
    return query in hay


def search_room(
    query: str,
    room,
    limit: int = 30,
    user_id: str = "",
    privileged: bool = False,
    viewer: Optional[dict] = None,
) -> dict:
    q = (query or "").strip().lower()
    if len(q) < 2:
        return {"query": query, "results": [], "count": 0}

    from room.message_filter import filter_messages_for_viewer

    results: list[dict] = []

    if privileged:
        task_iter = room.task_history.get_all()
    elif user_id:
        task_iter = room.task_history.get_for_user(user_id, 200)
    else:
        task_iter = []

    for task in task_iter:
        if not _match(q, task.get("task"), task.get("response"), task.get("agent_name"), task.get("target")):
            continue
        results.append({
            "type": "task",
            "id": task.get("id"),
            "title": (task.get("task") or "Задача")[:120],
            "snippet": (task.get("response") or task.get("task") or "")[:160],
            "meta": f"{task.get('agent_emoji', '')} {task.get('agent_name', '')} · {task.get('status', '')}".strip(),
            "view": "tasks",
        })

    from room.artifact_store import list_all

    for meta in list_all(limit=200):
        if not _match(q, meta.get("title"), meta.get("description"), " ".join(meta.get("tags") or [])):
            continue
        results.append({
            "type": "project",
            "id": meta.get("id"),
            "title": meta.get("title") or "Проект",
            "snippet": (meta.get("description") or "")[:160],
            "meta": f"{meta.get('agent_emoji', '')} {meta.get('agent_name', '')} · {meta.get('type', '')}".strip(),
            "view": "projects",
        })

    work_msgs = filter_messages_for_viewer(room.work_history, viewer or {})
    for msg in reversed(work_msgs):
        if msg.get("type") in ("agents_state", "history", "task_history", "direct_user_echo"):
            continue
        text = msg.get("message") or msg.get("text") or ""
        if not text or not _match(q, text, msg.get("agent_name")):
            continue
        results.append({
            "type": "message",
            "id": msg.get("timestamp") or msg.get("id"),
            "title": (text[:100] + ("…" if len(text) > 100 else "")),
            "snippet": text[:160],
            "meta": f"{msg.get('agent_emoji', '')} {msg.get('agent_name', 'Чат')}".strip(),
            "view": "chat",
        })

    if privileged or (viewer or {}).get("role") in ("owner", "admin", "tech_admin"):
        for msg in reversed(room.learning_history):
            text = msg.get("message") or ""
            if not text or not _match(q, text, msg.get("agent_name")):
                continue
            results.append({
                "type": "learning",
                "id": msg.get("timestamp") or msg.get("id"),
                "title": (text[:100] + ("…" if len(text) > 100 else "")),
                "snippet": text[:160],
                "meta": f"{msg.get('agent_emoji', '')} {msg.get('agent_name', 'Обучение')}".strip(),
                "view": "learning",
            })

    try:
        from integrations.sonya_studio import list_projects

        for project in list_projects():
            if not _match(q, project.get("title"), project.get("description"), project.get("status")):
                continue
            results.append({
                "type": "sonya",
                "id": project.get("id"),
                "title": project.get("title") or "Sonya Studio",
                "snippet": (project.get("description") or "")[:160],
                "meta": f"Studio · {project.get('status', 'draft')}",
                "view": "sonya-studio",
            })
    except Exception:
        pass

    trimmed = results[: max(1, min(limit, 100))]
    return {"query": query, "results": trimmed, "count": len(trimmed)}
