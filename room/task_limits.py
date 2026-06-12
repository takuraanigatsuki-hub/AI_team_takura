"""Дневные лимиты задач по тарифу."""

from __future__ import annotations

import json
import os
from datetime import datetime

from room.subscriptions import effective_tier, SUBSCRIPTION_PLANS, is_unlimited

COUNTS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "task_daily_counts.json")


def _load() -> dict:
    if not os.path.exists(COUNTS_FILE):
        return {}
    try:
        with open(COUNTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(COUNTS_FILE), exist_ok=True)
    with open(COUNTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_daily_count(user_id: str) -> int:
    data = _load()
    return int(data.get(user_id, {}).get(_today(), 0))


def check_daily_limit(user: dict) -> tuple[bool, str]:
    if not user:
        return True, ""
    if is_unlimited(user):
        return True, ""
    tier = effective_tier(user)
    plan = SUBSCRIPTION_PLANS.get(tier, SUBSCRIPTION_PLANS["free"])
    max_day = plan.get("max_tasks_per_day", 10)
    if not max_day:
        return True, ""
    count = get_daily_count(user.get("id", ""))
    if count >= max_day:
        return False, f"Дневной лимит задач ({max_day}) исчерпан. Обновите тариф или подождите до завтра."
    return True, ""


def record_task(user_id: str) -> int:
    if not user_id:
        return 0
    data = _load()
    day = _today()
    entry = data.setdefault(user_id, {})
    entry[day] = int(entry.get(day, 0)) + 1
    data[user_id] = {k: v for k, v in entry.items() if k >= day or k == day}
    _save(data)
    return entry[day]


def check_and_record(user: dict) -> tuple[bool, str]:
    ok, msg = check_daily_limit(user)
    if not ok:
        return False, msg
    if user.get("id"):
        record_task(user["id"])
    return True, ""
