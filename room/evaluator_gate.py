"""Evaluator gate — арtefact не уходит пользователю без минимального балла."""

from __future__ import annotations

import config as cfg
from typing import Optional


async def evaluate_artifact(
    task_text: str,
    agent_id: str,
    agent_name: str,
    response: str,
    artifact: Optional[dict] = None,
    room_manager=None,
) -> dict:
    evaluator = room_manager.agents.get("evaluator") if room_manager else None

    min_score = int(cfg.config.get("evaluator_min_score") or 6)

    if evaluator and hasattr(evaluator, "evaluate_output"):
        result = await evaluator.evaluate_output(
            task_text, agent_id, agent_name, response or (artifact or {}).get("description", ""),
            context="artifact",
        )
    else:
        result = {"score": 7, "feedback": "Авто-пропуск (evaluator offline)"}

    score = int(result.get("score") or 7)
    passed = score >= min_score
    return {
        "ok": True,
        "passed": passed,
        "score": score,
        "min_score": min_score,
        "feedback": result.get("feedback", ""),
        "agent_id": agent_id,
    }


async def gate_before_delivery(
    task_text: str,
    agent,
    response: str,
    saved_artifact: dict,
    room_manager,
) -> bool:
    """True = можно показывать пользователю. False = только черновик."""
    ev = await evaluate_artifact(
        task_text,
        agent.agent_id,
        agent.name,
        response,
        saved_artifact,
        room_manager=room_manager,
    )
    if room_manager:
        icon = "✅" if ev["passed"] else "⚠️"
        await room_manager.broadcast_work({
            "type": "evaluator_gate",
            "agent_id": "evaluator",
            "agent_name": "Маша",
            "agent_emoji": "🎓",
            "score": ev["score"],
            "passed": ev["passed"],
            "artifact_id": saved_artifact.get("id"),
            "message": (
                f"{icon} **Оценка качества:** {ev['score']}/10 "
                f"({'готово к показу' if ev['passed'] else f'ниже порога {ev[\"min_score\"]} — черновик'})\n"
                f"_{ev.get('feedback', '')[:300]}_"
            ),
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
    return ev["passed"]
