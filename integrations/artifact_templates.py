"""Шаблоны артефактов — быстрый старт."""

ARTIFACT_TEMPLATES = [
    {"id": "pitch", "name": "Pitch Deck", "icon": "📽️", "task": "Создай pitch deck на 8 слайдов для стартапа", "target": "presenter"},
    {"id": "3d-hero", "name": "3D Hero", "icon": "🧊", "task": "Создай интерактивную 3D-сцену hero для продукта", "target": "modeler"},
    {"id": "landing", "name": "Landing UI", "icon": "🎨", "task": "Создай landing page с hero, features, CTA", "target": "frontend"},
    {"id": "rest-api", "name": "REST API", "icon": "⚙️", "task": "REST API CRUD с FastAPI + PostgreSQL", "target": "backend"},
    {"id": "e2e-tests", "name": "E2E Tests", "icon": "🧪", "task": "Playwright E2E тесты для главных user flows", "target": "qa"},
    {"id": "arch-doc", "name": "Architecture", "icon": "🏛️", "task": "C4 architecture + ADR для системы", "target": "architect"},
    {"id": "readme", "name": "README", "icon": "📝", "task": "Полный README с setup, API, deploy", "target": "doc_writer"},
    {"id": "docker-ci", "name": "Docker CI", "icon": "🔧", "task": "Dockerfile + GitHub Actions CI/CD pipeline", "target": "devops"},
]


def list_templates() -> list:
    return ARTIFACT_TEMPLATES
