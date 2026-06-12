"""Шаблоны проектов — SaaS, E-commerce, Admin."""

TEMPLATES = {
    "saas": {
        "id": "saas",
        "name": "SaaS Dashboard",
        "icon": "📊",
        "description": "Dashboard с метриками, sidebar, auth-страницей",
        "task": (
            "Создай SaaS dashboard: landing + login + dashboard с KPI-карточками, "
            "sidebar-навигацией и таблицей пользователей. React Preview + REST API."
        ),
    },
    "ecommerce": {
        "id": "ecommerce",
        "name": "E-commerce",
        "icon": "🛒",
        "description": "Каталог, корзина, checkout",
        "task": (
            "Создай e-commerce: каталог товаров с фильтрами, карточка товара, "
            "корзина и checkout. UI в React, backend API для товаров и заказов."
        ),
    },
    "admin": {
        "id": "admin",
        "name": "Admin Panel",
        "icon": "🛡️",
        "description": "CRUD-админка с таблицами и формами",
        "task": (
            "Создай admin panel: таблица записей с поиском/фильтром, форма создания/редактирования, "
            "роли admin/user, API CRUD. Тёмная тема UI."
        ),
    },
}


def list_templates() -> list:
    return [
        {"id": t["id"], "name": t["name"], "icon": t["icon"], "description": t["description"]}
        for t in TEMPLATES.values()
    ]


def get_template(template_id: str) -> dict | None:
    return TEMPLATES.get(template_id)
