"""Доставка результата в чат + Microsoft 365."""

from datetime import datetime
from typing import Optional


async def try_deliver_m365(
    task_text: str,
    agent,
    artifact: Optional[dict] = None,
    room_manager=None,
) -> Optional[dict]:
    from room.task_routing import should_use_m365
    from integrations.m365_client import deliver_for_task, is_configured, status

    if not should_use_m365(task_text):
        return None
    if not is_configured():
        if room_manager:
            await room_manager.broadcast_work({
                "type": "m365_hint",
                "message": (
                    "ℹ️ **Microsoft 365** не настроен — результат только в «Проекты» и React Preview.\n"
                    "Добавьте `MS365_TENANT_ID`, `MS365_CLIENT_ID`, `MS365_CLIENT_SECRET`, "
                    "`MS365_USER_EMAIL` в `.env`."
                ),
                "timestamp": datetime.now().isoformat(),
            })
        return None

    try:
        result = await deliver_for_task(task_text, artifact)
        if not result or not room_manager:
            return result

        kind_label = {"excel": "Excel", "word": "Word", "presentation": "Презентация"}.get(
            result.get("kind"), "Файл"
        )
        await room_manager.broadcast_work({
            "type": "m365_ready",
            "agent_id": agent.agent_id,
            "agent_name": agent.name,
            "agent_emoji": agent.emoji,
            "title": result.get("title", task_text[:60]),
            "web_url": result.get("web_url", ""),
            "file_kind": result.get("kind", "file"),
            "message": (
                f"📎 **{kind_label} готов в Microsoft 365**\n"
                f"«{result.get('title', title_short(task_text))}»\n"
                f"Откройте в OneDrive / Office Online ↓"
            ),
            "timestamp": datetime.now().isoformat(),
        })
        return result
    except Exception as e:
        if room_manager:
            await room_manager.broadcast_work({
                "type": "error",
                "message": f"⚠️ Microsoft 365: {e}",
                "timestamp": datetime.now().isoformat(),
            })
        return None


def title_short(task_text: str) -> str:
    t = (task_text or "").strip()
    return t[:60] + ("…" if len(t) > 60 else "")
