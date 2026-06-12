"""Slash-команды чата — быстрый запуск задач и обучения."""

from __future__ import annotations

from typing import Optional

from room.mention_parser import AGENT_ALIASES

# cmd без / — lowercase
SLASH_COMMANDS: list[dict] = [
    {"cmd": "help", "label": "Справка по командам", "hint": "Показать все /команды", "icon": "❓"},
    {"cmd": "task", "label": "Задача команде", "hint": "Режим задачи · @все", "target": "all", "msg_type": "task", "icon": "📋"},
    {"cmd": "site", "label": "Сайт / landing", "hint": "→ Соня · frontend", "target": "frontend", "msg_type": "task", "prefix": "Сделай сайт: ", "icon": "🌐"},
    {"cmd": "table", "label": "Таблица", "hint": "→ команда · не landing", "target": "all", "msg_type": "task", "prefix": "Сделай таблицу для: ", "icon": "📊"},
    {"cmd": "api", "label": "REST API", "hint": "→ Макс · backend", "target": "backend", "msg_type": "task", "prefix": "REST API: ", "icon": "⚙️"},
    {"cmd": "ui", "label": "React UI", "hint": "→ Соня", "target": "frontend", "msg_type": "task", "prefix": "React UI: ", "icon": "🎨"},
    {"cmd": "test", "label": "Тесты", "hint": "→ Рита · QA", "target": "qa", "msg_type": "task", "prefix": "Напиши тесты: ", "icon": "🧪"},
    {"cmd": "pm", "label": "Виктор · PM", "hint": "План и оркестрация", "target": "pm", "msg_type": "task", "icon": "🎯"},
    {"cmd": "соня", "label": "Соня · Frontend", "hint": "UI и сайты", "target": "frontend", "msg_type": "task", "icon": "🎨"},
    {"cmd": "макс", "label": "Макс · Backend", "hint": "API и сервер", "target": "backend", "msg_type": "task", "icon": "⚙️"},
    {"cmd": "маша", "label": "Маша · Оценка", "hint": "Обучение и баллы", "target": "evaluator", "msg_type": "learning", "icon": "🎓"},
    {"cmd": "learn", "label": "Упражнение", "hint": "Задание для обучения → Маша", "target": "evaluator", "msg_type": "learning", "learning_mode": True, "icon": "📚"},
    {"cmd": "practice", "label": "Практика", "hint": "Команда отрабатывает тему", "target": "all", "msg_type": "learning", "learning_mode": True, "icon": "🏋️"},
    {"cmd": "collab", "label": "Совместный проект", "hint": "Обучение в паре/группе", "target": "all", "msg_type": "learning", "learning_mode": True, "collaborative": True, "icon": "🤝"},
    {"cmd": "chat", "label": "Только чат", "hint": "Без выполнения задачи", "target": "all", "msg_type": "chat", "icon": "💬"},
]

_CMD_MAP = {c["cmd"]: c for c in SLASH_COMMANDS}


def list_commands() -> list[dict]:
    out = []
    for c in SLASH_COMMANDS:
        if c["cmd"] == "help":
            continue
        item = dict(c)
        item.setdefault("prefix", c.get("prefix", ""))
        out.append(item)
    return out


def help_text() -> str:
    lines = ["**Slash-команды** (введите `/` в чате):\n"]
    for c in SLASH_COMMANDS:
        if c["cmd"] == "help":
            continue
        lines.append(f"• `/{c['cmd']}` — {c['icon']} {c['label']}: _{c['hint']}_")
    lines.append("\nПример: `/site landing для SaaS` · `/learn React hooks` · `/collab паттерны UI`")
    return "\n".join(lines)


def parse_slash_command(text: str) -> Optional[dict]:
    """Разбор `/cmd остальной текст`. Возвращает None если не команда."""
    raw = (text or "").strip()
    if not raw.startswith("/"):
        return None

    body = raw[1:].strip()
    if not body:
        return {"cmd": "", "show_help": True, "text": "", "msg_type": "chat"}

    parts = body.split(maxsplit=1)
    cmd_key = parts[0].lower().lstrip("/")
    rest = parts[1].strip() if len(parts) > 1 else ""

    # алиас агента как команда: /pm, /соня
    if cmd_key in AGENT_ALIASES and cmd_key not in _CMD_MAP:
        agent_id = AGENT_ALIASES[cmd_key]
        if agent_id == "all":
            return {"cmd": cmd_key, "text": rest or "Задача для команды", "target": "all", "msg_type": "task"}
        return {"cmd": cmd_key, "text": rest or f"Задача для {agent_id}", "target": agent_id, "msg_type": "task"}

    spec = _CMD_MAP.get(cmd_key)
    if not spec:
        return None

    if spec.get("cmd") == "help" or cmd_key == "help":
        return {"cmd": "help", "show_help": True, "text": "", "msg_type": "chat"}

    prefix = spec.get("prefix") or ""
    final_text = f"{prefix}{rest}".strip() if rest else (prefix.rstrip(": ") or spec["label"])

    result = {
        "cmd": cmd_key,
        "text": final_text,
        "target": spec.get("target"),
        "msg_type": spec.get("msg_type", "task"),
        "learning_mode": spec.get("learning_mode", False),
        "collaborative": spec.get("collaborative", False),
        "icon": spec.get("icon", ""),
        "label": spec.get("label", cmd_key),
    }
    return result
