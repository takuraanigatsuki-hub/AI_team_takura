"""Фильтрация сообщений и задач по роли пользователя."""

from __future__ import annotations

PRIVILEGED_ROLES = frozenset({"owner", "admin", "tech_admin"})

HIDDEN_MSG_TYPES = frozenset({
    "security_alert",
    "github_sync_started",
    "github_sync_done",
    "git_sync_done",
    "cursor_progress",
})

HIDDEN_AGENT_IDS = frozenset({"security"})


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
    if any(k in text for k in ("github sync", "git sync", "security alert", "threat:", "ip заблок")):
        return False

    return True


def filter_messages_for_viewer(messages: list, viewer: dict | None) -> list:
    return [m for m in messages if should_show_message(m, viewer)]


def filter_agents_for_viewer(agents: list, viewer: dict | None) -> list:
    viewer = viewer or {}
    if is_privileged(viewer.get("role", "")):
        return agents
    return [a for a in agents if a.get("agent_id") not in HIDDEN_AGENT_IDS]
