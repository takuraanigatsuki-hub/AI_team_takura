"""Запросы пользователя — распознавание намерений и цели команды."""

import re
from typing import Optional

CHAT_ONLY_PREFIXES = (
    "/chat", "/чат", "только ответ:", "просто ответь", "не делай", "без задачи",
    "just chat", "no task",
)

WORK_VERBS = (
    "сделай", "сделать", "создай", "создать", "напиши", "написать", "разработай",
    "разработать", "реализуй", "реализовать", "добавь", "добавить", "исправь",
    "исправить", "поправь", "улучши", "доработай", "переделай", "сгенерируй",
    "сверстай", "сверстать", "спроектируй", "протестируй", "проверь", "задеплой",
    "задеплой", "опиши", "оформи", "нарисуй", "смоделируй", "собери", "настрой",
    "implement", "create", "build", "fix", "add", "write", "develop", "make",
    "design", "deploy", "test", "refactor",
)

CHAT_STARTS = (
    "привет", "здравств", "спасибо", "пока", "ок", "okay", "понятно", "ясно",
    "что такое", "что это", "как работает", "как ты", "кто ты", "расскажи о",
    "объясни что", "what is", "how do you", "who are you", "hello", "hi ",
)

AGENT_GOAL_KEYWORDS = {
    "pm": ("план", "roadmap", "спринт", "задач", "команд", "pm", "менедж"),
    "architect": ("архитект", "систем", "diagram", "микросервис", "api design", "schema"),
    "backend": ("api", "backend", "бэкенд", "сервер", "база", "database", "fastapi", "python"),
    "frontend": ("ui", "ux", "react", "frontend", "фронт", "верст", "макет", "landing", "css"),
    "qa": ("тест", "qa", "bug", "регресс", "playwright"),
    "reviewer": ("review", "ревью", "code review", "качеств"),
    "doc_writer": ("документ", "readme", "docs", "описан"),
    "devops": ("docker", "ci", "cd", "deploy", "kubernetes", "devops"),
    "cursor": ("cursor", "repo", "pr", "pull request", "sdk"),
    "presenter": ("презент", "pitch", "slides", "demo"),
    "modeler": ("3d", "glb", "модел", "three.js"),
}


def classify_user_message(text: str, force_chat: bool = False) -> str:
    """Возвращает 'work' или 'chat'."""
    if force_chat:
        return "chat"
    t = (text or "").strip().lower()
    if not t or len(t) < 3:
        return "chat"

    for prefix in CHAT_ONLY_PREFIXES:
        if t.startswith(prefix):
            return "chat"

    for start in CHAT_STARTS:
        if t.startswith(start):
            return "chat"

    if any(v in t for v in WORK_VERBS):
        return "work"

    if re.search(r"\b(можешь|could you|please|нужно|надо|хочу|мне нужен|помоги|help me)\b", t):
        if len(t) > 12 and not t.endswith("?"):
            return "work"

    if len(t) > 90 and "?" not in t[-8:]:
        return "work"

    return "chat"


def record_user_wish(text: str, agent_id: Optional[str] = None) -> None:
    """Сохраняет рабочий запрос пользователя в цели проекта."""
    if classify_user_message(text) != "work":
        return
    try:
        from room.project_memory import get_memory, set_memory
    except Exception:
        return

    snippet = text.strip()[:200]
    tag = f"[{agent_id}]" if agent_id else "[user]"
    entry = f"{tag} {snippet}"

    data = get_memory()
    goals = [g for g in (data.get("goals") or []) if g != entry]
    goals.insert(0, entry)
    set_memory(goals=goals[:20])


def topics_from_user_wishes(agent_id: Optional[str] = None, limit: int = 5) -> list:
    try:
        from room.project_memory import get_memory
        goals = get_memory().get("goals") or []
    except Exception:
        return []

    keywords = AGENT_GOAL_KEYWORDS.get(agent_id or "", ())
    topics = []
    for raw in goals:
        clean = re.sub(r"^\[[\w.]+\]\s*", "", raw).strip()
        if len(clean) < 8:
            continue
        if agent_id and keywords and not any(k in clean.lower() for k in keywords):
            continue
        topics.append(clean[:120])
        if len(topics) >= limit:
            break
    return topics


def pick_idle_user_task(agent_id: str) -> Optional[str]:
    """Подобрать невыполненный запрос пользователя для агента в простое."""
    topics = topics_from_user_wishes(agent_id, limit=8)
    if not topics:
        topics = topics_from_user_wishes(None, limit=3)
    return topics[0] if topics else None
