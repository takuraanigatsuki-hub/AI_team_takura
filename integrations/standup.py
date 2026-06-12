"""Standup / Recap — сводка команды от лица PM."""

from datetime import datetime, timedelta
from typing import Any, Optional


def generate_standup(room_manager) -> dict:
    now = datetime.now()
    since = now - timedelta(hours=1)

    tasks = room_manager.task_history.get_all()
    recent_tasks = [t for t in tasks if _parse_ts(t.get("completed_at") or t.get("created_at")) >= since]
    completed = [t for t in recent_tasks if t.get("status") == "completed"]
    active = [t for t in tasks if t.get("status") in ("in_progress", "queued", "submitted")]

    activity = []
    for msg in reversed(room_manager.work_history[-40:]):
        ts = _parse_ts(msg.get("timestamp"))
        if ts < since:
            break
        if msg.get("type") in ("task_done", "figma_import", "figma_portfolio", "github_sync_done", "git_sync_done", "site_ready"):
            activity.append(msg)

    agents = room_manager.agents
    working = [a for a in agents.values() if a.status in ("working", "learning", "thinking")]

    figma_studied = 0
    figma_projects = 0
    try:
        from integrations.figma_learning import get_studio_stats
        stats = get_studio_stats()
        figma_studied = stats.get("studied_count", 0)
        figma_projects = stats.get("portfolio_count", 0)
    except Exception:
        pass

    pipeline = room_manager.pipeline.get_state()
    stats = room_manager.task_history.stats()

    lines = [
        f"📊 **Standup** · {now.strftime('%H:%M')}",
        "",
        f"За последний час: **{len(completed)}** задач выполнено, **{len(active)}** в работе.",
    ]

    if working:
        lines.append(f"Сейчас активны: {', '.join(f'{a.emoji} {a.name}' for a in working[:5])}.")
    else:
        lines.append("Команда в режиме ожидания — можно давать новые задачи.")

    if pipeline and not pipeline.get("finished_at"):
        lines.append(f"🔄 Pipeline: **{pipeline.get('progress', 0)}%** — «{pipeline.get('task', '')[:50]}»")

    highlights = []
    for t in completed[:3]:
        agent = t.get("agent_name") or t.get("agent_id") or "Команда"
        highlights.append(f"• {agent}: {(t.get('task') or '')[:60]}")
    if highlights:
        lines += ["", "**Готово:**"] + highlights

    if figma_studied or figma_projects:
        lines.append(f"\n🎨 Соня: {figma_studied} макетов изучено, {figma_projects} своих проектов.")

    sync_events = [a for a in activity if a.get("type") in ("github_sync_done", "git_sync_done")]
    if sync_events:
        lines.append(f"\n📤 GitHub: {len(sync_events)} синхронизаций за час.")

    lines += [
        "",
        "**Рекомендация Виктора:**",
        _recommendation(completed, active, pipeline),
    ]

    return {
        "narrative": "\n".join(lines),
        "stats": stats,
        "completed_recent": len(completed),
        "active_count": len(active),
        "working_agents": [{"name": a.name, "emoji": a.emoji, "status": a.status} for a in working],
        "highlights": highlights,
        "pipeline": pipeline,
        "generated_at": now.isoformat(),
    }


def _recommendation(completed, active, pipeline) -> str:
    if pipeline and not pipeline.get("finished_at"):
        return "Дождитесь завершения текущего pipeline, затем проверьте React Preview и PR."
    if active:
        return "Следите за вкладкой «Задачи» — команда уже работает над вашими пунктами."
    if completed:
        return "Отличный прогресс! Можно открыть Preview или отправить follow-up задачу."
    return "Отправьте задачу «Вся команде» — Виктор составит план и запустит pipeline."


def _parse_ts(val: Optional[str]) -> datetime:
    if not val:
        return datetime.min
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00").split("+")[0])
    except Exception:
        return datetime.min
