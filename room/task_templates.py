"""Шаблоны задач — пресеты для PM и пользователей."""

from __future__ import annotations

TASK_TEMPLATES = [
    {
        "id": "landing_1h",
        "title": "Landing за 1 час",
        "emoji": "🚀",
        "description": "Создай современный landing page с hero, features, CTA и footer. Адаптив, тёмная тема.",
        "agents": ["pm", "frontend", "qa"],
        "kind": "site",
        "credits": 25,
    },
    {
        "id": "mvp_backend",
        "title": "MVP Backend",
        "emoji": "⚙️",
        "description": "REST API на FastAPI: auth, CRUD, PostgreSQL, тесты pytest, OpenAPI docs.",
        "agents": ["architect", "backend", "qa", "reviewer"],
        "kind": "api",
        "credits": 40,
    },
    {
        "id": "investor_pitch",
        "title": "Pitch для инвестора",
        "emoji": "📊",
        "description": "Презентация для инвесторов: problem, solution, market, traction, team, ask. 10 слайдов.",
        "agents": ["pm", "presenter", "evaluator"],
        "kind": "presentation",
        "credits": 30,
    },
    {
        "id": "security_audit",
        "title": "Security Audit",
        "emoji": "🛡",
        "description": "Проведи аудит безопасности приложения: OWASP Top 10, auth, API, secrets, dependencies.",
        "agents": ["security", "reviewer", "devops"],
        "kind": "security",
        "credits": 35,
    },
    {
        "id": "figma_to_react",
        "title": "Figma → React",
        "emoji": "🎨",
        "description": "Импорт макета из Figma и реализация React-компонентов с Tailwind.",
        "agents": ["frontend", "qa"],
        "kind": "ui",
        "credits": 45,
    },
    {
        "id": "full_pipeline",
        "title": "Full Pipeline",
        "emoji": "⚡",
        "description": "Полный цикл: дизайн → код → тесты → deploy preview.",
        "agents": ["pm", "frontend", "backend", "qa", "devops", "cursor"],
        "kind": "pipeline",
        "credits": 80,
    },
    {
        "id": "weekly_standup",
        "title": "Weekly Standup",
        "emoji": "📋",
        "description": "Подготовь standup-отчёт: что сделано, блокеры, планы на неделю.",
        "agents": ["pm", "doc_writer"],
        "kind": "document",
        "credits": 10,
    },
    {
        "id": "collab_learning",
        "title": "Совместное обучение",
        "emoji": "🎓",
        "description": "Командное упражнение: frontend + backend + qa решают задачу, Маша оценивает.",
        "agents": ["frontend", "backend", "qa", "evaluator"],
        "kind": "learning",
        "credits": 20,
        "learning": True,
    },
]


def list_templates(category: str = "") -> list:
    if not category:
        return TASK_TEMPLATES
    return [t for t in TASK_TEMPLATES if t.get("kind") == category]


def get_template(template_id: str) -> dict | None:
    for t in TASK_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
