"""Agent debates — Architect vs Reviewer."""

import random
from datetime import datetime


DEBATE_PAIRS = [
    ("architect", "reviewer", "Архитектура vs Code Review"),
    ("backend", "qa", "Backend vs QA"),
    ("frontend", "reviewer", "UI vs Review"),
]


async def maybe_start_debate(task_text: str, assignments: dict, agents: dict, room_manager) -> bool:
    from room.task_routing import should_run_architecture_debate

    if not should_run_architecture_debate(task_text):
        return False
    if "architect" not in assignments or "reviewer" not in assignments:
        return False
    if random.random() > 0.45:
        return False

    architect = agents.get("architect")
    reviewer = agents.get("reviewer")
    if not architect or not reviewer:
        return False

    pro = (
        f"Предлагаю модульную архитектуру с чёткими границами для: {task_text[:80]}. "
        "Разделим слои API / domain / infra, чтобы масштабировать без боли."
    )
    con = (
        "Согласен с модулями, но сначала — простота и тестируемость. "
        "Не over-engineering: MVP, покрытие тестами, потом рефакторинг."
    )

    try:
        from integrations.llm_client import is_configured, agent_reply
        if is_configured():
            pro = await agent_reply(architect.name, architect.role, architect.description, f"Аргумент ЗА решение: {task_text}", [])
            con = await agent_reply(reviewer.name, reviewer.role, reviewer.description, f"Критика и улучшения: {task_text}", [])
    except Exception:
        pass

    await room_manager.broadcast_work({
        "type": "agent_debate",
        "topic": task_text[:100],
        "rounds": [
            {"agent_id": "architect", "agent_name": architect.name, "agent_emoji": architect.emoji, "message": pro},
            {"agent_id": "reviewer", "agent_name": reviewer.name, "agent_emoji": reviewer.emoji, "message": con},
        ],
        "timestamp": datetime.now().isoformat(),
    })
    return True
