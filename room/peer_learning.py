"""Обучение агентов друг с другом — только канал «Обучение»."""

import random
from datetime import datetime


async def share_learning_to_work_chat(agent, material: dict, room_manager) -> None:
    """После изучения — опубликовать находку в чат обучения."""
    if not room_manager:
        return
    title = material.get("title") or material.get("topic", "Тема")
    summary = (material.get("summary") or "")[:280]
    await room_manager.broadcast_learning({
        "type": "peer_learning",
        "agent_id": agent.agent_id,
        "agent_name": agent.name,
        "agent_emoji": agent.emoji,
        "topic": material.get("topic", title),
        "title": title,
        "message": (
            f"📚 **Практика · {title}**\n{summary}\n\n"
            f"_Как применю в следующей задаче пользователя._"
        ),
        "timestamp": datetime.now().isoformat(),
    })
    try:
        from room.learning_projects import LearningProjects
        LearningProjects().create_agent_project(
            agent.agent_id,
            title=title,
            summary=summary,
            collaborative=False,
            topic=material.get("topic", title),
        )
    except Exception:
        pass


async def peer_discussion_round(room_manager, agents: dict) -> None:
    """Короткий диалог 2–3 агентов — только чат обучения."""
    pool = [
        a for aid, a in agents.items()
        if aid not in ("pm", "evaluator") and getattr(a, "learned_topics", None)
    ]
    if len(pool) < 2:
        return

    a1, a2 = random.sample(pool, 2)
    t1 = a1.learned_topics[-1] if a1.learned_topics else {"topic": "best practices", "title": "Практики"}
    t2 = a2.learned_topics[-1] if a2.learned_topics else {"topic": "patterns", "title": "Паттерны"}

    msg = (
        f"💬 **Обмен опытом**\n"
        f"{a1.emoji} **{a1.name}**: изучил «{t1.get('title', t1.get('topic'))}» — "
        f"предлагаю применить в UI.\n"
        f"{a2.emoji} **{a2.name}**: согласен, у меня «{t2.get('title', t2.get('topic'))}» — "
        f"можно объединить подходы."
    )
    await room_manager.broadcast_learning({
        "type": "peer_discussion",
        "agent_id": a1.agent_id,
        "agent_name": a1.name,
        "agent_emoji": a1.emoji,
        "message": msg,
        "agents": [
            {"id": a1.agent_id, "name": a1.name, "emoji": a1.emoji},
            {"id": a2.agent_id, "name": a2.name, "emoji": a2.emoji},
        ],
        "timestamp": datetime.now().isoformat(),
    })
    try:
        from room.learning_projects import LearningProjects
        LearningProjects().create_agent_project(
            a1.agent_id,
            title=f"С {a2.name}: {t1.get('title', t1.get('topic', ''))[:60]}",
            summary=msg[:400],
            collaborative=True,
            co_agent_ids=[a2.agent_id],
            topic=t1.get("topic", ""),
        )
    except Exception:
        pass

    evaluator = agents.get("evaluator")
    if evaluator and hasattr(evaluator, "evaluate_output"):
        result = await evaluator.evaluate_output(
            f"Peer learning: {t1.get('topic')}",
            a1.agent_id,
            a1.name,
            t1.get("summary", ""),
            context="peer_learning",
        )
        await room_manager.broadcast_learning({
            "type": "skill_evaluation",
            "agent_id": "evaluator",
            "agent_name": evaluator.name,
            "agent_emoji": evaluator.emoji,
            "target_agent": a1.agent_id,
            "score": result.get("score", 7),
            "message": f"🎓 **Оценка навыков** ({result.get('score', 7)}/10)\n{result.get('feedback', '')}",
            "timestamp": datetime.now().isoformat(),
        })
