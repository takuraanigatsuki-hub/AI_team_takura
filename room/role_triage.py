"""Проверка: входит ли задача в обязанности роли — до начала работы."""

from room.task_routing import classify_task_kind

ROLE_FIT = {
    "pm": ["план", "координ", "sprint", "задач", "команд", "pm", "оркестр"],
    "architect": ["архитектур", "diagram", "c4", "adr", "микросервис", "структур", "api", "сайт", "backend"],
    "backend": ["api", "backend", "бэкенд", "сервер", "endpoint", "fastapi", "rest", "баз", "database", "сайт"],
    "frontend": ["ui", "ux", "react", "frontend", "фронт", "верст", "интерфейс", "сайт", "landing", "таблиц", "компонент", "css"],
    "qa": ["тест", "test", "pytest", "playwright", "e2e", "qa", "сайт", "api"],
    "reviewer": ["review", "ревью", "качеств", "код", "api", "архитектур"],
    "evaluator": ["оцен", "качеств", "навык", "review", "ревью", "таблиц", "презентац", "ui", "сайт", "документ"],
    "doc_writer": ["документ", "readme", "описан", "инструкци", "текст", "презентац"],
    "devops": ["docker", "deploy", "kubernetes", "ci/cd", "devops", "инфраструктур"],
    "cursor": ["код", "code", "cursor", "github", "implement", "refactor", "sdk"],
    "presenter": ["презентац", "slides", "pitch", "слайд", "deck", "доклад"],
    "modeler": ["3d", "3д", "three", "glb", "gltf", "blender", "webgl", "модел", "сцен"],
    "security": ["безопас", "security", "owasp", "уязвим", "cve", "audit", "pen test"],
}


def agent_fits_role(agent_id: str, task_text: str, subtask: str) -> tuple[bool, str]:
    """Входит ли подзадача в компетенцию агента."""
    kind = classify_task_kind(task_text)
    blob = f"{task_text} {subtask}".lower()

    kind_map = {
        "table": ("frontend", "evaluator"),
        "presentation": ("presenter", "evaluator"),
        "model_3d": ("modeler", "evaluator"),
        "site": ("architect", "frontend", "backend", "qa", "evaluator"),
        "api": ("architect", "backend", "qa", "reviewer"),
        "ui": ("frontend", "evaluator"),
        "document": ("doc_writer", "evaluator"),
        "architecture": ("architect", "evaluator"),
        "tests": ("qa", "evaluator"),
        "infra": ("devops", "evaluator"),
        "security": ("security", "reviewer", "evaluator"),
    }
    primary = kind_map.get(kind, ())
    if agent_id in primary:
        return True, f"Роль подходит для задачи типа «{kind}»."

    keywords = ROLE_FIT.get(agent_id, [])
    if any(k in blob for k in keywords):
        return True, "Задача совпадает с профилем роли."

    if agent_id == "evaluator":
        return True, "Оценка и проверка результата."

    if agent_id == "reviewer" and kind in ("api", "site", "tests", "infra", "architecture"):
        return True, "Code/architecture review."

    if agent_id == "pm":
        return False, "PM уже составил план — не исполняет подзадачи."

    return False, f"Не входит в зону ответственности {agent_id} для «{kind}»."


async def run_role_triage(
    task_text: str,
    assignments: dict,
    agents: dict,
    room_manager,
    parent_id: str = None,
    silent: bool = True,
) -> dict:
    """Фильтр ролей; silent=True — одна сводка вместо сообщения от каждого агента."""
    accepted: dict[str, str] = {}
    declined: list[dict] = []

    for agent_id, subtask in assignments.items():
        agent = agents.get(agent_id)
        if not agent:
            continue
        fits, reason = agent_fits_role(agent_id, task_text, subtask)
        if fits:
            accepted[agent_id] = subtask
            if not silent:
                await room_manager.broadcast_work({
                    "type": "role_triage",
                    "agent_id": agent_id,
                    "agent_name": agent.name,
                    "agent_emoji": agent.emoji,
                    "fits_role": True,
                    "reason": reason,
                    "subtask": subtask,
                    "parent_id": parent_id,
                    "message": f"✅ Беру: *{subtask[:120]}*\n_{reason}_",
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                })
        else:
            declined.append({"agent_id": agent_id, "reason": reason})

    if "evaluator" not in accepted and "evaluator" in agents:
        accepted["evaluator"] = f"Оценить результат и навыки: {task_text}"

    if not accepted:
        accepted = dict(assignments)

    if room_manager and parent_id:
        p = room_manager.task_history._find(parent_id)
        if p:
            p["triage"] = {"accepted": list(accepted.keys()), "declined": declined}
            p["status"] = "triaging"
            room_manager.task_history._save()

    if silent and room_manager and accepted:
        names = ", ".join(
            f"{agents[a].emoji} {agents[a].name}" for a in accepted if a in agents
        )
        skipped = len(declined)
        await room_manager.broadcast_work({
            "type": "role_triage_summary",
            "parent_id": parent_id,
            "message": (
                f"🎯 **В работу:** {names}"
                + (f" _(не по роли: {skipped})_" if skipped else "")
            ),
            "accepted": list(accepted.keys()),
            "declined_count": skipped,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })

    return accepted
