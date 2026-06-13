"""LLM + keyword маршрутизация: какие агенты нужны для задачи."""

from __future__ import annotations

import json
import re
from typing import Optional

from room.task_routing import classify_task_kind

# Все известные agent_id
ALL_AGENT_IDS = [
    "pm", "architect", "backend", "frontend", "qa", "reviewer",
    "doc_writer", "devops", "cursor", "presenter", "modeler",
    "evaluator", "security",
]

KIND_DEFAULT_AGENTS = {
    "presentation": ["presenter", "evaluator"],
    "model_3d": ["modeler", "evaluator"],
    "table": ["frontend", "evaluator"],
    "site": ["architect", "frontend", "backend", "qa", "evaluator"],
    "api": ["architect", "backend", "qa", "reviewer"],
    "architecture": ["architect", "reviewer", "evaluator"],
    "tests": ["qa", "reviewer"],
    "infra": ["devops", "reviewer"],
    "document": ["doc_writer", "evaluator"],
    "ui": ["frontend", "evaluator"],
    "security": ["security", "reviewer"],
    "plan": ["pm"],
}


def _keyword_route(task_text: str, pm_assignments: dict) -> dict[str, str]:
    """Fallback без LLM: фильтрует PM assignments по kind + keywords."""
    kind = classify_task_kind(task_text)
    preferred = set(KIND_DEFAULT_AGENTS.get(kind, []))
    blob = task_text.lower()
    filtered: dict[str, str] = {}

    for agent_id, subtask in pm_assignments.items():
        if agent_id == "pm":
            continue
        if preferred and agent_id in preferred:
            filtered[agent_id] = subtask
            continue
        if not preferred and agent_id in pm_assignments:
            # generic task — keep PM picks but drop obvious misfits via role_triage later
            filtered[agent_id] = subtask

    if not filtered:
        # минимальный набор
        if kind == "presentation":
            filtered["presenter"] = pm_assignments.get("presenter") or f"Презентация: {task_text}"
        elif kind == "model_3d":
            filtered["modeler"] = pm_assignments.get("modeler") or f"3D: {task_text}"
        else:
            for aid in list(pm_assignments.keys())[:3]:
                if aid != "pm":
                    filtered[aid] = pm_assignments[aid]

    if "evaluator" not in filtered and kind not in ("plan",):
        filtered["evaluator"] = f"Оценить результат: {task_text[:200]}"

    return filtered


async def route_task(
    task_text: str,
    pm_assignments: dict,
    agents: dict,
) -> tuple[dict[str, str], str]:
    """
    Возвращает (assignments, router_note).
    С LLM — умный выбор; без — keyword fallback.
    """
    from integrations.llm_client import is_configured, chat

    if not is_configured():
        routed = _keyword_route(task_text, pm_assignments)
        return routed, "router:keyword (OPENAI_API_KEY не задан)"

    kind = classify_task_kind(task_text)
    agent_list = "\n".join(
        f"- {aid}: {getattr(agents.get(aid), 'role', aid)}"
        for aid in ALL_AGENT_IDS if aid in agents
    )
    current = json.dumps(pm_assignments, ensure_ascii=False)[:800]

    prompt = f"""Ты router AI-команды. Задача пользователя:
«{task_text}»

Тип задачи: {kind}
Текущие назначения PM: {current}

Доступные агенты:
{agent_list}

Выбери ТОЛЬКО агентов, которым реально нужно работать (обычно 1–4, не всю команду).
PM (pm) не исполняет — не включай.
Evaluator включай для проверки результата если задача создаёт арtefact.

Ответь СТРОГО JSON без markdown:
{{"agents": ["presenter", "evaluator"], "reason": "кратко на русском"}}"""

    try:
        raw = await chat(
            [{"role": "system", "content": "Ты JSON router. Только валидный JSON."},
             {"role": "user", "content": prompt}],
            max_tokens=300,
            model=__import__("integrations.llm_client", fromlist=["router_model"]).router_model(),
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```\w*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
        data = json.loads(raw)
        ids = [a for a in data.get("agents", []) if a in agents and a != "pm"]
        reason = data.get("reason", "LLM router")
        if not ids:
            routed = _keyword_route(task_text, pm_assignments)
            return routed, f"router:keyword (LLM вернул пусто)"
        routed = {}
        for aid in ids:
            routed[aid] = pm_assignments.get(aid) or f"{task_text} — {aid}"
        if "evaluator" not in routed and kind not in ("plan",):
            routed["evaluator"] = f"Оценить результат: {task_text[:200]}"
        try:
            from room.router_logs import log_route
            log_route(task_text, pm_assignments, routed, f"router:llm — {reason}", kind=kind)
        except Exception:
            pass
        return routed, f"router:llm — {reason}"
    except Exception as e:
        routed = _keyword_route(task_text, pm_assignments)
        try:
            from room.router_logs import log_route
            log_route(task_text, pm_assignments, routed, f"router:keyword (LLM error: {e})", kind=kind)
        except Exception:
            pass
        return routed, f"router:keyword (LLM error: {e})"
