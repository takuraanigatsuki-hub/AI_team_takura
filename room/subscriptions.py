"""Подписки, баланс (кредиты) и уровни доступа."""

from datetime import datetime
from typing import Optional

# Уровни: чем выше number — тем больше возможностей
TIER_ORDER = ("free", "starter", "pro", "team", "owner")

SUBSCRIPTION_PLANS = {
    "free": {
        "id": "free",
        "name_ru": "Бесплатный",
        "emoji": "🌱",
        "level": 1,
        "price_rub": 0,
        "monthly_credits": 50,
        "signup_bonus": 100,
        "max_tasks_per_day": 10,
        "description": "3D-студия, чат и базовые задачи",
    },
    "starter": {
        "id": "starter",
        "name_ru": "Starter",
        "emoji": "🚀",
        "level": 2,
        "price_rub": 990,
        "monthly_credits": 500,
        "signup_bonus": 200,
        "max_tasks_per_day": 50,
        "description": "+ Kanban, проекты, Sprint",
    },
    "pro": {
        "id": "pro",
        "name_ru": "Pro",
        "emoji": "⭐",
        "level": 3,
        "price_rub": 2990,
        "monthly_credits": 2000,
        "signup_bonus": 500,
        "max_tasks_per_day": 200,
        "description": "+ Sonya Studio, Design, Timeline",
    },
    "team": {
        "id": "team",
        "name_ru": "Team",
        "emoji": "👥",
        "level": 4,
        "price_rub": 7990,
        "monthly_credits": 10000,
        "signup_bonus": 2000,
        "max_tasks_per_day": 1000,
        "description": "+ Pipeline, Deploy, Cursor, все вкладки",
    },
    "owner": {
        "id": "owner",
        "name_ru": "Owner",
        "emoji": "👑",
        "level": 5,
        "price_rub": 0,
        "monthly_credits": 0,
        "signup_bonus": 0,
        "max_tasks_per_day": 0,
        "unlimited": True,
        "description": "Полный доступ — только владелец проекта",
    },
}

# Минимальный тариф для вкладки / функции
VIEW_MIN_TIER = {
    "studio": "free",
    "chat": "free",
    "learning": "free",
    "tasks": "free",
    "dashboard": "free",
    "profile": "free",
    "kanban": "starter",
    "projects": "starter",
    "sprint": "starter",
    "design": "pro",
    "sonya-studio": "pro",
    "timeline": "pro",
}

FEATURE_MIN_TIER = {
    "pipeline": "team",
    "deploy": "team",
    "cursor": "team",
    "backup": "team",
    "view_link": "pro",
    "sonya_publish": "pro",
    "figma_import": "starter",
}

# Стоимость операций в кредитах (0 = бесплатно для тарифа с доступом)
ACTION_COSTS = {
    "task": 5,
    "sonya_create": 15,
    "sonya_apply": 10,
    "figma_import": 20,
    "deploy": 50,
    "pipeline": 30,
    "cursor_run": 25,
}


def tier_level(tier_id: str) -> int:
    plan = SUBSCRIPTION_PLANS.get(tier_id or "free", SUBSCRIPTION_PLANS["free"])
    return plan.get("level", 1)


def effective_tier(user: dict) -> str:
    """Owner-роль всегда получает тариф owner."""
    if user.get("role") == "owner":
        return "owner"
    tier = (user.get("subscription_tier") or "free").lower()
    if tier not in SUBSCRIPTION_PLANS:
        return "free"
    return tier


def is_unlimited(user: dict) -> bool:
    if user.get("role") == "owner" or user.get("is_owner"):
        return True
    sub = user.get("subscription") or {}
    if sub.get("unlimited"):
        return True
    tier = effective_tier(user)
    return bool(SUBSCRIPTION_PLANS.get(tier, {}).get("unlimited"))


def normalize_user_billing(raw: dict) -> dict:
    """Дополняет пользователя полями подписки при чтении."""
    tier = effective_tier(raw)
    if raw.get("role") == "owner":
        tier = "owner"
        raw["subscription_tier"] = "owner"
    if "balance" not in raw:
        plan = SUBSCRIPTION_PLANS.get(tier, SUBSCRIPTION_PLANS["free"])
        raw["balance"] = plan.get("signup_bonus", 100)
    if "subscription_tier" not in raw:
        raw["subscription_tier"] = "free"
    return raw


def initial_billing_for_register() -> dict:
    plan = SUBSCRIPTION_PLANS["free"]
    return {
        "subscription_tier": "free",
        "balance": plan["signup_bonus"],
        "balance_updated_at": datetime.now().isoformat(),
    }


def initial_billing_for_owner() -> dict:
    return {
        "subscription_tier": "owner",
        "balance": 999_999_999,
        "balance_updated_at": datetime.now().isoformat(),
    }


def public_subscription(user: dict) -> dict:
    raw = normalize_user_billing(dict(user))
    tier = effective_tier(raw)
    plan = SUBSCRIPTION_PLANS[tier]
    unlimited = is_unlimited(raw)
    balance = raw.get("balance", 0)
    return {
        "tier": tier,
        "tier_name": plan["name_ru"],
        "tier_emoji": plan.get("emoji", ""),
        "level": plan["level"],
        "balance": balance if not unlimited else None,
        "balance_display": "∞" if unlimited else balance,
        "unlimited": unlimited,
        "price_rub": plan.get("price_rub", 0),
        "monthly_credits": plan.get("monthly_credits", 0),
        "max_tasks_per_day": plan.get("max_tasks_per_day", 10),
        "description": plan.get("description", ""),
        "expires_at": raw.get("subscription_expires_at"),
        "features_unlocked": _unlocked_features(tier),
        "views_unlocked": _unlocked_views(tier),
    }


def list_plans_public() -> list:
    out = []
    for tid in TIER_ORDER:
        if tid == "owner":
            continue
        p = SUBSCRIPTION_PLANS[tid]
        out.append({
            "id": tid,
            "name_ru": p["name_ru"],
            "emoji": p.get("emoji", ""),
            "level": p["level"],
            "price_rub": p["price_rub"],
            "monthly_credits": p["monthly_credits"],
            "description": p["description"],
            "views": _unlocked_views(tid),
            "features": _unlocked_features(tid),
        })
    out.append({
        "id": "owner",
        "name_ru": SUBSCRIPTION_PLANS["owner"]["name_ru"],
        "emoji": "👑",
        "level": 5,
        "price_rub": 0,
        "monthly_credits": 0,
        "description": SUBSCRIPTION_PLANS["owner"]["description"],
        "views": _unlocked_views("owner"),
        "features": _unlocked_features("owner"),
        "owner_only": True,
    })
    return out


def _unlocked_views(tier_id: str) -> list:
    lvl = tier_level(tier_id)
    return [v for v, min_t in VIEW_MIN_TIER.items() if tier_level(min_t) <= lvl]


def _unlocked_features(tier_id: str) -> list:
    lvl = tier_level(tier_id)
    feats = [f"views:{','.join(_unlocked_views(tier_id))}"]
    for feat, min_t in FEATURE_MIN_TIER.items():
        if tier_level(min_t) <= lvl:
            feats.append(feat)
    if tier_id == "owner":
        feats.extend(["admin", "manage_users", "unlimited_balance"])
    return feats


def has_tier_at_least(user: dict | None, min_tier: str) -> bool:
    if not user:
        return False
    if is_unlimited(user):
        return True
    return tier_level(effective_tier(user)) >= tier_level(min_tier)


def can_access_view(user: dict | None, view: str) -> bool:
    min_t = VIEW_MIN_TIER.get(view, "free")
    return has_tier_at_least(user, min_t)


def can_use_feature(user: dict | None, feature: str) -> bool:
    min_t = FEATURE_MIN_TIER.get(feature, "free")
    return has_tier_at_least(user, min_t)


def get_action_cost(action: str) -> int:
    return ACTION_COSTS.get(action, 0)


def _balance_value(user: dict) -> int:
    if "subscription" in user and isinstance(user["subscription"], dict):
        b = user["subscription"].get("balance")
        if b is None and user["subscription"].get("unlimited"):
            return 999_999_999
        return int(b or 0)
    return int(user.get("balance", 0))


def check_balance(user: dict | None, action: str) -> tuple[bool, str]:
    if not user:
        return False, "Требуется вход в аккаунт"
    if is_unlimited(user):
        return True, ""
    cost = get_action_cost(action)
    if cost <= 0:
        return True, ""
    balance = _balance_value(user)
    if balance < cost:
        return False, f"Недостаточно кредитов ({balance}/{cost}). Пополните баланс или смените тариф."
    return True, ""


def deduct_balance(user_id: str, action: str, *, users_loader, users_saver, find_user) -> tuple[bool, str, int]:
    """Списание кредитов. Возвращает (ok, message, new_balance)."""
    user = find_user(user_id)
    if not user:
        return False, "Пользователь не найден", 0
    normalize_user_billing(user)
    if is_unlimited(user):
        return True, "", user.get("balance", 0)
    cost = get_action_cost(action)
    if cost <= 0:
        return True, "", user.get("balance", 0)
    if user.get("balance", 0) < cost:
        return False, f"Недостаточно кредитов (нужно {cost})", user.get("balance", 0)

    users = users_loader()
    new_bal = 0
    for u in users:
        if u.get("id") == user_id:
            u["balance"] = max(0, int(u.get("balance", 0)) - cost)
            u["balance_updated_at"] = datetime.now().isoformat()
            new_bal = u["balance"]
            break
    users_saver(users)
    return True, "", new_bal


def add_balance(user_id: str, amount: int, *, users_loader, users_saver) -> int:
    if amount <= 0:
        raise ValueError("Сумма должна быть положительной")
    users = users_loader()
    new_bal = 0
    for u in users:
        if u.get("id") == user_id:
            normalize_user_billing(u)
            if is_unlimited(u):
                return u.get("balance", 999_999_999)
            u["balance"] = int(u.get("balance", 0)) + amount
            u["balance_updated_at"] = datetime.now().isoformat()
            new_bal = u["balance"]
            break
    users_saver(users)
    return new_bal


def set_subscription_tier(user_id: str, tier: str, *, users_loader, users_saver) -> None:
    if tier not in SUBSCRIPTION_PLANS:
        raise ValueError("Неизвестный тариф")
    if tier == "owner":
        raise ValueError("Тариф Owner назначается только через роль owner")
    users = users_loader()
    for u in users:
        if u.get("id") == user_id:
            if u.get("role") == "owner":
                u["subscription_tier"] = "owner"
            else:
                u["subscription_tier"] = tier
                plan = SUBSCRIPTION_PLANS[tier]
                u["balance"] = max(int(u.get("balance", 0)), plan.get("signup_bonus", 0))
            u["subscription_updated_at"] = datetime.now().isoformat()
            break
    users_saver(users)


def access_denied_message(view_or_feature: str, user: dict | None) -> str:
    if view_or_feature in VIEW_MIN_TIER:
        need = VIEW_MIN_TIER[view_or_feature]
    else:
        need = FEATURE_MIN_TIER.get(view_or_feature, "pro")
    plan = SUBSCRIPTION_PLANS.get(need, SUBSCRIPTION_PLANS["pro"])
    cur = SUBSCRIPTION_PLANS.get(effective_tier(user or {}), SUBSCRIPTION_PLANS["free"])
    return (
        f"Доступ ограничен. Нужен тариф **{plan['emoji']} {plan['name_ru']}** или выше. "
        f"Ваш тариф: {cur['emoji']} {cur['name_ru']}."
    )
