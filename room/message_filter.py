"""Фильтрация сообщений и задач по роли пользователя."""

from __future__ import annotations

PRIVILEGED_ROLES = frozenset({"owner", "admin", "tech_admin"})

HIDDEN_MSG_TYPES = frozenset({
    "security_alert",
    "github_sync_started",
    "github_sync_done",
    "git_sync_done",
    "cursor_progress",
    "pr_ready",
})

HIDDEN_AGENT_IDS = frozenset({"security"})

TIMELINE_LEARNING_TYPES = frozenset({
    "learning", "learning_result", "reflection", "rest", "figma_study",
    "peer_learning", "peer_discussion", "skill_evaluation", "learning_project",
})

TIMELINE_SKIP_TYPES = frozenset({
    "agents_state", "history", "task_history", "agent_stream", "agent_stream_start",
    "presence_update", "balance_update", "pipeline_update", "cursor_progress",
    "react_preview", "sonya_studio_update",
})


def is_privileged(role: str = "") -> bool:
    return (role or "") in PRIVILEGED_ROLES


def viewer_from_meta(meta: dict | None) -> dict:
    if not meta:
        return {"user_id": "", "role": "guest"}
    return {"user_id": meta.get("user_id", ""), "role": meta.get("role", "guest")}


def should_show_message(message: dict, viewer: dict | None) -> bool:
    """Скрыть GitHub/Security от обычных пользователей."""
    viewer = viewer or {}
    if is_privileged(viewer.get("role", "")):
        return True

    msg_type = message.get("type", "")
    if msg_type in HIDDEN_MSG_TYPES:
        return False
    if msg_type == "task_history":
        return True

    agent_id = (message.get("agent_id") or "").lower()
    if agent_id in HIDDEN_AGENT_IDS:
        return False

    text = (message.get("message") or message.get("text") or "").lower()
    if any(k in text for k in (
        "github sync", "git sync", "security alert", "threat:", "ip заблок",
        "commit на github", "commit:", "github.com/",
    )):
        return False

    return True


def filter_messages_for_viewer(messages: list, viewer: dict | None) -> list:
    return [m for m in messages if should_show_message(m, viewer)]


def should_show_timeline_event(event: dict, viewer: dict | None) -> bool:
    """Скрыть процесс обучения агентов от обычных пользователей."""
    viewer = viewer or {}
    if is_privileged(viewer.get("role", "")):
        return True
    if event.get("channel") == "learning":
        return False
    if event.get("type", "") in TIMELINE_LEARNING_TYPES:
        return False
    return should_show_message(event, viewer)


def filter_timeline_for_viewer(events: list, viewer: dict | None) -> list:
    return [e for e in events if should_show_timeline_event(e, viewer)]


def should_record_timeline_event(event: dict) -> bool:
    """Не писать в timeline служебные WS-события без текста."""
    msg_type = event.get("type", "")
    if msg_type in TIMELINE_SKIP_TYPES:
        return False
    text = (event.get("message") or event.get("text") or "").strip()
    if not text and msg_type in TIMELINE_SKIP_TYPES:
        return False
    if not text and not event.get("agent_id") and not event.get("agent_name"):
        return False
    return True


def filter_timeline_noise(events: list) -> list:
    return [e for e in events if should_record_timeline_event(e)]


def filter_agents_for_viewer(agents: list, viewer: dict | None) -> list:
    viewer = viewer or {}
    if is_privileged(viewer.get("role", "")):
        return agents
    return [a for a in agents if a.get("agent_id") not in HIDDEN_AGENT_IDS]
