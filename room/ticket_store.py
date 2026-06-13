"""Тикеты поддержки — обращения пользователей и ответы операторов."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Optional

TICKETS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "tickets.json")
MAX_TICKETS = 2000

TICKET_TEMPLATES = [
    {
        "id": "login",
        "icon": "🔐",
        "title": "Не могу войти",
        "hint": "Ошибка входа, забыли пароль, сессия сбрасывается",
        "category": "auth",
        "subject": "Проблема со входом в аккаунт",
        "solution": (
            "Попробуйте следующее:\n"
            "1. Проверьте email и пароль (раскладка клавиатуры, Caps Lock).\n"
            "2. Выйдите и войдите снова через «Вход» на главной странице.\n"
            "3. Очистите cookies для сайта и обновите страницу (Ctrl+F5).\n"
            "4. Если регистрировались недавно — завершите первичную настройку в кабинете.\n\n"
            "Если не помогло — опишите ошибку ниже, мы ответим в течение рабочего дня."
        ),
    },
    {
        "id": "task_stuck",
        "icon": "⏳",
        "title": "Задача зависла",
        "hint": "Долго в работе, нет результата, ошибка агента",
        "category": "tasks",
        "subject": "Задача не завершается или зависла",
        "solution": (
            "Частые причины:\n"
            "1. Сложная задача — агенты могут работать несколько минут.\n"
            "2. Проверьте Inbox: статус «На проверке» означает, что результат ждёт вашего одобрения.\n"
            "3. Нажмите «Отменить активные» в Inbox, если задача явно зависла.\n"
            "4. Упростите формулировку и отправьте задачу заново.\n\n"
            "Укажите текст задачи и время — мы проверим лог."
        ),
    },
    {
        "id": "billing",
        "icon": "💳",
        "title": "Подписка и баланс",
        "hint": "Тариф, кредиты, оплата, лимиты",
        "category": "billing",
        "subject": "Вопрос по подписке или балансу",
        "solution": (
            "Информация о тарифе и балансе — в 👤 Кабинете → вкладка «Подписка».\n"
            "• Тариф определяет доступные разделы (Studio, Sprint и др.).\n"
            "• Кредиты списываются за отдельные действия (генерация, деплой).\n\n"
            "Для смены тарифа или пополнения — опишите желаемый план, поддержка передаст запрос администратору."
        ),
    },
    {
        "id": "chat_error",
        "icon": "💬",
        "title": "Ошибка в чате",
        "hint": "Сообщения не отправляются, пустой ответ, обрыв связи",
        "category": "technical",
        "subject": "Проблема с рабочим чатом",
        "solution": (
            "1. Обновите страницу (Ctrl+F5).\n"
            "2. Проверьте интернет-соединение.\n"
            "3. Если видите «LLM не настроен» — это техническая проблема платформы, уже передана админам.\n"
            "4. Скопируйте текст ошибки из чата, если он есть.\n\n"
            "Приложите скриншот или точное время сбоя — так быстрее найдём причину."
        ),
    },
    {
        "id": "file_delivery",
        "icon": "📎",
        "title": "Нет файла / результата",
        "hint": "Презентация, таблица, сайт — не появился результат",
        "category": "delivery",
        "subject": "Не получил ожидаемый результат",
        "solution": (
            "1. Откройте Inbox — готовые задачи со статусом «На проверке» содержат ссылку на скачивание.\n"
            "2. Презентации — кнопка «PowerPoint (.pptx)»; таблицы — ссылка M365 или файл в чате.\n"
            "3. Одобрите задачу (✓), если результат уже показан в карточке.\n\n"
            "Напишите, какую задачу отправляли и что ожидали получить."
        ),
    },
    {
        "id": "other",
        "icon": "✉️",
        "title": "Другое",
        "hint": "Любой вопрос, не подошли варианты выше",
        "category": "other",
        "subject": "Обращение в поддержку",
        "solution": (
            "Опишите проблему максимально конкретно: что делали, что ожидали, что получили.\n"
            "Чем больше деталей — тем быстрее поможем."
        ),
    },
]


def _load() -> list:
    if not os.path.exists(TICKETS_FILE):
        return []
    try:
        with open(TICKETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(items: list) -> None:
    os.makedirs(os.path.dirname(TICKETS_FILE), exist_ok=True)
    with open(TICKETS_FILE, "w", encoding="utf-8") as f:
        json.dump(items[-MAX_TICKETS:], f, ensure_ascii=False, indent=2)


def list_templates() -> list[dict]:
    return [dict(t) for t in TICKET_TEMPLATES]


def get_template(template_id: str) -> Optional[dict]:
    for t in TICKET_TEMPLATES:
        if t["id"] == template_id:
            return dict(t)
    return None


def _now() -> str:
    return datetime.now().isoformat()


def create_ticket(
    *,
    user_id: str,
    user_email: str,
    user_name: str,
    subject: str,
    message: str,
    category: str = "other",
    template_id: str = "",
) -> dict:
    ticket_id = str(uuid.uuid4())[:10]
    text = (message or "").strip()
    if not text:
        text = subject or "Обращение без описания"
    ticket = {
        "id": ticket_id,
        "user_id": user_id,
        "user_email": user_email,
        "user_name": user_name or user_email,
        "category": category or "other",
        "template_id": template_id or "",
        "subject": (subject or "Обращение в поддержку")[:160],
        "status": "open",
        "priority": "normal",
        "created_at": _now(),
        "updated_at": _now(),
        "assigned_to": "",
        "messages": [
            {
                "id": str(uuid.uuid4())[:8],
                "author_id": user_id,
                "author_role": "user",
                "author_name": user_name or user_email,
                "text": text[:4000],
                "created_at": _now(),
                "is_solution": False,
            }
        ],
    }
    items = _load()
    items.append(ticket)
    _save(items)
    return ticket


def list_for_user(user_id: str, limit: int = 50) -> list[dict]:
    items = [t for t in _load() if t.get("user_id") == user_id]
    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return items[:limit]


def list_for_support(
    *,
    status: str = "",
    limit: int = 100,
) -> list[dict]:
    items = _load()
    if status:
        items = [t for t in items if t.get("status") == status]
    items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return items[:limit]


def get_ticket(ticket_id: str) -> Optional[dict]:
    for t in _load():
        if t.get("id") == ticket_id:
            return t
    return None


def add_message(
    ticket_id: str,
    *,
    author_id: str,
    author_role: str,
    author_name: str,
    text: str,
    is_solution: bool = False,
) -> Optional[dict]:
    text = (text or "").strip()
    if not text:
        return None
    items = _load()
    for t in items:
        if t.get("id") != ticket_id:
            continue
        t.setdefault("messages", []).append({
            "id": str(uuid.uuid4())[:8],
            "author_id": author_id,
            "author_role": author_role,
            "author_name": author_name,
            "text": text[:4000],
            "created_at": _now(),
            "is_solution": bool(is_solution),
        })
        t["updated_at"] = _now()
        if author_role == "support" and t.get("status") == "open":
            t["status"] = "in_progress"
        _save(items)
        return t
    return None


def update_ticket(
    ticket_id: str,
    *,
    status: str = None,
    priority: str = None,
    assigned_to: str = None,
) -> Optional[dict]:
    items = _load()
    for t in items:
        if t.get("id") != ticket_id:
            continue
        if status is not None:
            t["status"] = status
        if priority is not None:
            t["priority"] = priority
        if assigned_to is not None:
            t["assigned_to"] = assigned_to
        t["updated_at"] = _now()
        _save(items)
        return t
    return None


def counts_by_status() -> dict:
    counts = {"open": 0, "in_progress": 0, "resolved": 0, "closed": 0, "total": 0}
    for t in _load():
        st = t.get("status", "open")
        counts["total"] += 1
        if st in counts:
            counts[st] += 1
    return counts
