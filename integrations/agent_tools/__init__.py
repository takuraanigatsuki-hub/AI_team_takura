"""Реестр инструментов агентов (Phase B)."""

from __future__ import annotations

AGENT_TOOLS: dict[str, list[dict]] = {
    "pm": [
        {"name": "rag_search", "description": "Поиск в базе знаний PM"},
        {"name": "project_memory", "description": "Контекст проекта пользователя"},
        {"name": "create_plan", "description": "Сформировать план работ"},
    ],
    "architect": [
        {"name": "rag_search", "description": "Архитектурные паттерны и ADR"},
        {"name": "web_fetch", "description": "Загрузить документацию по URL"},
    ],
    "backend": [
        {"name": "rag_search", "description": "Backend/API знания"},
        {"name": "code_gen", "description": "Генерация Python/FastAPI кода"},
        {"name": "sandbox_run", "description": "Выполнить Python в Docker sandbox"},
    ],
    "frontend": [
        {"name": "rag_search", "description": "React/CSS/UI знания"},
        {"name": "figma_import", "description": "Импорт макета Figma"},
        {"name": "react_preview", "description": "React Preview"},
    ],
    "qa": [
        {"name": "rag_search", "description": "Testing/QA знания"},
        {"name": "write_tests", "description": "Генерация pytest/Playwright"},
        {"name": "sandbox_run", "description": "Запуск тестового кода в sandbox"},
        {"name": "browser_test", "description": "Playwright smoke-тест URL"},
        {"name": "playwright_snapshot", "description": "Снимок страницы в браузере"},
    ],
    "reviewer": [
        {"name": "rag_search", "description": "Code review checklist"},
        {"name": "code_review", "description": "Ревью фрагмента кода"},
    ],
    "doc_writer": [
        {"name": "rag_search", "description": "Technical writing"},
        {"name": "write_doc", "description": "Markdown/README/OpenAPI"},
    ],
    "devops": [
        {"name": "rag_search", "description": "Docker/K8s/CI"},
        {"name": "pipeline", "description": "Запуск pipeline"},
    ],
    "cursor": [
        {"name": "cursor_run", "description": "Cursor Cloud Agent"},
        {"name": "git_sync", "description": "Git sync репозитория"},
    ],
    "presenter": [
        {"name": "rag_search", "description": "Pitch/slides знания"},
        {"name": "create_pptx", "description": "PowerPoint файл"},
    ],
    "modeler": [
        {"name": "rag_search", "description": "Three.js/glTF"},
        {"name": "create_3d_scene", "description": "HTML Three.js сцена"},
    ],
    "evaluator": [
        {"name": "evaluate_artifact", "description": "Оценка качества 1-10"},
    ],
    "security": [
        {"name": "rag_search", "description": "OWASP/security"},
        {"name": "security_scan", "description": "Чеклист уязвимостей"},
    ],
}


def tools_for(agent_id: str) -> list[dict]:
    return AGENT_TOOLS.get(agent_id, [{"name": "rag_search", "description": "База знаний"}])


def tool_names(agent_id: str) -> list[str]:
    return [t["name"] for t in tools_for(agent_id)]
