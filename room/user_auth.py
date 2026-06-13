"""Пользователи и сессии — регистрация, вход, первая настройка."""

import hashlib
import json
import os
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "users.json")
SESSIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "sessions.json")
SESSION_COOKIE = "ai_team_session"
SESSION_DAYS = 30

PRIMARY_OWNER_EMAILS = frozenset({
    "takura.anigatsuki@gmail.com",
})

ALL_PRIVILEGES = [
    "admin",
    "manage_users",
    "manage_settings",
    "manage_integrations",
    "manage_telegram",
    "deploy",
    "backup",
    "pipeline",
    "view_link",
    "view_agent_learning",
    "all_views",
    "skip_setup",
    "manage_tickets",
]

PRIVILEGE_LABELS = {
    "admin": "Полный admin-доступ",
    "manage_users": "Управление пользователями",
    "manage_settings": "Настройки платформы",
    "manage_integrations": "Интеграции",
    "manage_telegram": "Telegram-бот",
    "deploy": "Deploy",
    "backup": "Backup",
    "pipeline": "Pipeline",
    "view_link": "View-link",
    "view_agent_learning": "Обучение агентов",
    "all_views": "Все разделы",
    "skip_setup": "Пропуск setup",
    "manage_tickets": "Тикеты поддержки",
}

ROLE_ASSIGNABLE = {
    "owner": ("owner", "admin", "tech_admin", "support", "investor", "member"),
    "admin": ("admin", "tech_admin", "support", "investor", "member"),
    "tech_admin": ("support", "investor", "member"),
}

PROTECTED_ROLES = frozenset({"owner", "admin", "tech_admin"})

ROLE_PRIVILEGES = {
    "owner": ALL_PRIVILEGES,
    "admin": [p for p in ALL_PRIVILEGES if p != "manage_users"],
    "tech_admin": [
        "admin",
        "manage_users",
        "manage_settings",
        "manage_integrations",
        "manage_telegram",
        "deploy",
        "backup",
        "pipeline",
        "view_agent_learning",
        "view_link",
        "all_views",
        "skip_setup",
        "manage_tickets",
    ],
    "support": [
        "view_link",
        "all_views",
        "manage_tickets",
    ],
    "investor": [
        "view_investor_portal",
        "view_link",
    ],
    "member": [],
}

ROLE_LABELS = {
    "owner": "Владелец",
    "admin": "Админ",
    "tech_admin": "Тех. админ",
    "support": "Поддержка",
    "investor": "Инвестор",
    "member": "Пользователь",
}


def _privileges_for_role(role: str) -> list[str]:
    return list(ROLE_PRIVILEGES.get(role or "member", []))


def has_privilege(user: dict | None, privilege: str) -> bool:
    if not user:
        return False
    privs = user.get("privileges") or _privileges_for_role(user.get("role", "member"))
    return privilege in privs or "admin" in privs


def _load(path: str) -> list | dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [] if path.endswith("users.json") else {}


def _save_users(users: list):
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def _save_sessions(sessions: dict):
    os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, ensure_ascii=False)


def _hash_password(password: str, salt: str = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return salt, digest


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split(":", 1)
        _, check = _hash_password(password, salt)
        return secrets.compare_digest(check, digest)
    except Exception:
        return False


def _find_user_by_email(email: str) -> Optional[dict]:
    email = email.strip().lower()
    for u in _load(USERS_FILE):
        if u.get("email") == email:
            return _apply_primary_owner(u)
    return None


def _find_user(user_id: str) -> Optional[dict]:
    for u in _load(USERS_FILE):
        if u.get("id") == user_id:
            return _apply_primary_owner(u)
    return None


def _apply_primary_owner(raw: dict) -> dict:
    """Гарантирует owner-права для основного владельца проекта."""
    if not raw:
        return raw
    email = (raw.get("email") or "").strip().lower()
    if email not in PRIMARY_OWNER_EMAILS:
        return raw
    from room.subscriptions import initial_billing_for_owner

    changed = False
    owner_billing = initial_billing_for_owner()
    if raw.get("role") != "owner":
        raw["role"] = "owner"
        changed = True
    if list(raw.get("privileges") or []) != list(ALL_PRIVILEGES):
        raw["privileges"] = list(ALL_PRIVILEGES)
        changed = True
    for key, val in owner_billing.items():
        if raw.get(key) != val:
            raw[key] = val
            changed = True
    if not raw.get("setup_complete"):
        raw["setup_complete"] = True
        changed = True
    if changed:
        raw["updated_at"] = datetime.now().isoformat()
        users = _load(USERS_FILE)
        for i, u in enumerate(users):
            if u.get("id") == raw.get("id"):
                users[i] = raw
                _save_users(users)
                break
    return raw


def is_primary_owner_email(email: str) -> bool:
    return (email or "").strip().lower() in PRIMARY_OWNER_EMAILS


def _public_user(user: dict) -> dict:
    from room.subscriptions import normalize_user_billing, public_subscription

    user = normalize_user_billing(user)
    role = user.get("role", "member")
    privs = user.get("privileges") or _privileges_for_role(role)
    if role == "owner":
        user["subscription_tier"] = "owner"
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "role": role,
        "role_label": _role_label(role),
        "role_badge": role,
        "privileges": privs,
        "is_owner": role == "owner",
        "is_tech_admin": role == "tech_admin",
        "is_support": role == "support",
        "can_view_agent_learning": can_view_agent_learning(user),
        "can_view_investor_portal": can_view_investor_portal(user),
        "can_manage_tickets": can_manage_tickets(user),
        "can_access_support_panel": can_access_support_panel(user),
        "is_investor": role == "investor",
        "setup_complete": bool(user.get("setup_complete")),
        "default_view": user.get("default_view", "dashboard"),
        "theme": user.get("theme", "dark"),
        "project_goal": user.get("project_goal", ""),
        "created_at": user.get("created_at"),
        "setup_at": user.get("setup_at"),
        "subscription": public_subscription(user),
        "access_level": public_subscription(user)["level"],
    }


def admin_set_user_tier(admin_user: dict, target_user_id: str, tier: str) -> dict:
    if not has_privilege(admin_user, "manage_users") and admin_user.get("role") != "owner":
        raise ValueError("Недостаточно прав")
    from room.subscriptions import set_subscription_tier

    set_subscription_tier(
        target_user_id,
        tier,
        users_loader=lambda: _load(USERS_FILE),
        users_saver=_save_users,
    )
    target = _find_user(target_user_id)
    return _public_user(target) if target else {}


def admin_add_balance(admin_user: dict, target_user_id: str, amount: int) -> dict:
    if not has_privilege(admin_user, "manage_users") and admin_user.get("role") != "owner":
        raise ValueError("Недостаточно прав")
    from room.subscriptions import add_balance

    add_balance(
        target_user_id,
        amount,
        users_loader=lambda: _load(USERS_FILE),
        users_saver=_save_users,
    )
    target = _find_user(target_user_id)
    return _public_user(target) if target else {}


def _role_label(role: str) -> str:
    return ROLE_LABELS.get(role or "member", role)


def can_access_admin(user: dict | None) -> bool:
    if not user:
        return False
    if user.get("is_owner") or user.get("role") == "owner":
        return True
    role = user.get("role", "member")
    if role in ("admin", "tech_admin"):
        return True
    return (
        has_privilege(user, "manage_users")
        or has_privilege(user, "manage_settings")
        or has_privilege(user, "admin")
    )


def can_view_agent_learning(user: dict | None) -> bool:
    """Лента обучения, Design Lab — только owner / admin / tech_admin."""
    if not user:
        return False
    role = user.get("role", "member")
    if role in ("owner", "admin", "tech_admin"):
        return True
    return has_privilege(user, "view_agent_learning")


def can_view_investor_portal(user: dict | None) -> bool:
    if not user:
        return False
    role = user.get("role", "member")
    if role in ("owner", "admin", "tech_admin", "investor"):
        return True
    return has_privilege(user, "view_investor_portal")


def can_manage_tickets(user: dict | None) -> bool:
    """Панель поддержки — support, owner, admin, tech_admin."""
    if not user:
        return False
    if user.get("is_support"):
        return True
    role = user.get("role", "member")
    if role in ("owner", "admin", "tech_admin", "support"):
        return True
    return has_privilege(user, "manage_tickets") or has_privilege(user, "admin")


def can_access_support_panel(user: dict | None) -> bool:
    return can_manage_tickets(user)


def _ensure_role_privileges(raw: dict) -> dict:
    """Синхронизировать privileges с ролью (fix устаревших записей support/tech_admin)."""
    if not raw:
        return raw
    role = raw.get("role", "member")
    expected = _privileges_for_role(role)
    current = raw.get("privileges")
    if role in ("support", "tech_admin") and list(current or []) != list(expected):
        raw["privileges"] = list(expected)
        raw["updated_at"] = datetime.now().isoformat()
        users = _load(USERS_FILE)
        for i, u in enumerate(users):
            if u.get("id") == raw.get("id"):
                users[i] = raw
                _save_users(users)
                break
    return raw


def support_account_summary(user_id: str) -> Optional[dict]:
    """Базовая информация об аккаунте — без паролей, API и биллинга."""
    user = _find_user(user_id)
    if not user:
        return None
    pub = _public_user(user)
    sub = pub.get("subscription") or {}
    return {
        "id": pub["id"],
        "name": pub["name"],
        "email": pub["email"],
        "role_label": pub["role_label"],
        "setup_complete": pub.get("setup_complete"),
        "created_at": pub.get("created_at"),
        "default_view": pub.get("default_view", "dashboard"),
        "subscription_tier": sub.get("tier_name") or sub.get("name") or "—",
        "access_level": pub.get("access_level"),
    }


def register(email: str, password: str, name: str = "") -> tuple[dict, str]:
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Некорректный email")
    if len(password) < 6:
        raise ValueError("Пароль минимум 6 символов")
    if _find_user_by_email(email):
        raise ValueError("Email уже зарегистрирован")

    salt, digest = _hash_password(password)
    from room.subscriptions import initial_billing_for_register

    user = {
        "id": str(uuid.uuid4())[:12],
        "email": email,
        "name": (name or email.split("@")[0]).strip()[:80],
        "password": f"{salt}:{digest}",
        "role": "member",
        "privileges": [],
        "setup_complete": False,
        "default_view": "dashboard",
        "created_at": datetime.now().isoformat(),
        **initial_billing_for_register(),
    }
    users = _load(USERS_FILE)
    users.append(user)
    _save_users(users)
    token = _create_session(user["id"])
    return _public_user(user), token


def login(email: str, password: str) -> tuple[dict, str]:
    user = _find_user_by_email(email)
    if not user or not _verify_password(password, user.get("password", "")):
        raise ValueError("Неверный email или пароль")
    if user.get("disabled"):
        raise ValueError("Аккаунт заблокирован. Обратитесь в поддержку.")
    token = _create_session(user["id"])
    return _public_user(user), token


def _create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    sessions = _load(SESSIONS_FILE)
    if not isinstance(sessions, dict):
        sessions = {}
    sessions[token] = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=SESSION_DAYS)).isoformat(),
    }
    _cleanup_sessions(sessions)
    _save_sessions(sessions)
    return token


def _cleanup_sessions(sessions: dict):
    now = datetime.now()
    expired = []
    for token, meta in sessions.items():
        try:
            if datetime.fromisoformat(meta["expires_at"]) < now:
                expired.append(token)
        except Exception:
            expired.append(token)
    for token in expired:
        sessions.pop(token, None)


def logout(token: str):
    if not token:
        return
    sessions = _load(SESSIONS_FILE)
    if isinstance(sessions, dict) and token in sessions:
        del sessions[token]
        _save_sessions(sessions)


def get_user_from_token(token: str) -> Optional[dict]:
    if not token:
        return None
    sessions = _load(SESSIONS_FILE)
    if not isinstance(sessions, dict):
        return None
    meta = sessions.get(token)
    if not meta:
        return None
    try:
        if datetime.fromisoformat(meta["expires_at"]) < datetime.now():
            logout(token)
            return None
    except Exception:
        return None
    user = _find_user(meta.get("user_id", ""))
    if not user or user.get("disabled"):
        return None
    user = _ensure_role_privileges(user)
    return _public_user(user) if user else None


ALLOWED_DEFAULT_VIEWS = (
    "studio", "dashboard", "chat", "kanban", "design", "sonya-studio",
    "tasks", "projects", "sprint", "profile",
)


def complete_setup(user_id: str, *, name: str = "", goal: str = "",
                   default_view: str = "dashboard", theme: str = "") -> dict:
    users = _load(USERS_FILE)
    updated = None
    for u in users:
        if u.get("id") == user_id:
            if name:
                u["name"] = name.strip()[:80]
            if default_view in ALLOWED_DEFAULT_VIEWS:
                u["default_view"] = default_view
            if theme in ("light", "dark", "auto"):
                u["theme"] = theme
            u["setup_complete"] = True
            u["setup_at"] = datetime.now().isoformat()
            if goal:
                u["project_goal"] = goal.strip()[:500]
            updated = u
            break
    if not updated:
        raise ValueError("Пользователь не найден")
    _save_users(users)
    return _public_user(updated)


def update_profile(
    user_id: str,
    *,
    name: str = None,
    default_view: str = None,
    theme: str = None,
    project_goal: str = None,
) -> dict:
    users = _load(USERS_FILE)
    updated = None
    for u in users:
        if u.get("id") != user_id:
            continue
        if name is not None:
            u["name"] = name.strip()[:80] or u.get("name", "")
        if default_view is not None and default_view in ALLOWED_DEFAULT_VIEWS:
            u["default_view"] = default_view
        if theme is not None and theme in ("light", "dark", "auto"):
            u["theme"] = theme
        if project_goal is not None:
            u["project_goal"] = project_goal.strip()[:500]
        u["updated_at"] = datetime.now().isoformat()
        updated = u
        break
    if not updated:
        raise ValueError("Пользователь не найден")
    _save_users(users)
    return _public_user(updated)


def change_password(user_id: str, current_password: str, new_password: str) -> None:
    if len(new_password) < 6:
        raise ValueError("Новый пароль минимум 6 символов")
    user = _find_user(user_id)
    if not user or not _verify_password(current_password, user.get("password", "")):
        raise ValueError("Неверный текущий пароль")
    salt, digest = _hash_password(new_password)
    users = _load(USERS_FILE)
    for u in users:
        if u.get("id") == user_id:
            u["password"] = f"{salt}:{digest}"
            u["updated_at"] = datetime.now().isoformat()
            break
    _save_users(users)


def charge_user_action(user_id: str, action: str) -> tuple[bool, str]:
    """Проверка и списание кредитов. Owner — без списания."""
    from room.subscriptions import check_balance, deduct_balance, normalize_user_billing

    user = _find_user(user_id)
    if not user:
        return False, "Пользователь не найден"
    normalize_user_billing(user)
    ok, msg = check_balance(user, action)
    if not ok:
        return False, msg
    ok, msg, _ = deduct_balance(
        user_id,
        action,
        users_loader=lambda: _load(USERS_FILE),
        users_saver=_save_users,
        find_user=_find_user,
    )
    return ok, msg


def ensure_owner(email: str, password: str, name: str = "Owner") -> dict:
    """Создать или обновить аккаунт владельца с полными привилегиями."""
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("Некорректный email")
    if len(password) < 6:
        raise ValueError("Пароль минимум 6 символов")

    salt, digest = _hash_password(password)
    pw = f"{salt}:{digest}"
    users = _load(USERS_FILE)
    updated = None

    from room.subscriptions import initial_billing_for_owner
    owner_billing = initial_billing_for_owner()

    for u in users:
        if u.get("email") == email:
            u["password"] = pw
            u["role"] = "owner"
            u["privileges"] = list(ALL_PRIVILEGES)
            u["setup_complete"] = True
            u.update(owner_billing)
            if name:
                u["name"] = name.strip()[:80]
            u["updated_at"] = datetime.now().isoformat()
            updated = u
            break

    if not updated:
        updated = {
            "id": str(uuid.uuid4())[:12],
            "email": email,
            "name": (name or email.split("@")[0]).strip()[:80],
            "password": pw,
            "role": "owner",
            "privileges": list(ALL_PRIVILEGES),
            "setup_complete": True,
            "default_view": "dashboard",
            "created_at": datetime.now().isoformat(),
            **owner_billing,
        }
        users.append(updated)

    _save_users(users)
    return _public_user(updated)


def bootstrap_primary_owner(email: str) -> Optional[dict]:
    """Выдать владельцу максимальные права и тариф Owner (без смены пароля)."""
    email = email.strip().lower()
    if not email:
        return None
    users = _load(USERS_FILE)
    from room.subscriptions import initial_billing_for_owner

    owner_billing = initial_billing_for_owner()
    updated = None
    for u in users:
        if u.get("email") == email:
            u["role"] = "owner"
            u["privileges"] = list(ALL_PRIVILEGES)
            u["setup_complete"] = True
            u.update(owner_billing)
            u["updated_at"] = datetime.now().isoformat()
            updated = u
            break
    if not updated:
        return None
    _save_users(users)
    return _public_user(updated)


def can_manage_users(user: dict | None) -> bool:
    if not user:
        return False
    if user.get("is_owner") or user.get("role") == "owner":
        return True
    if user.get("role") == "tech_admin":
        return True
    return has_privilege(user, "manage_users") or has_privilege(user, "admin")


def is_owner_user(user: dict | None) -> bool:
    return bool(user and (user.get("is_owner") or user.get("role") == "owner"))


def can_assign_role(admin_user: dict, role: str) -> bool:
    role = (role or "").strip().lower()
    if role not in ROLE_PRIVILEGES:
        return False
    admin_role = admin_user.get("role", "member")
    allowed = ROLE_ASSIGNABLE.get(admin_role, ())
    return role in allowed


def can_modify_user(admin_user: dict, target: dict) -> bool:
    if not can_manage_users(admin_user):
        return False
    if target.get("role") == "owner" and not is_owner_user(admin_user):
        return False
    if is_owner_user(admin_user):
        return True
    admin_role = admin_user.get("role", "member")
    target_role = target.get("role", "member")
    if admin_role == "tech_admin" and target_role in PROTECTED_ROLES:
        return False
    return True


def can_set_tier(admin_user: dict) -> bool:
    return is_owner_user(admin_user) or admin_user.get("role") == "admin"


def can_set_custom_privileges(admin_user: dict) -> bool:
    return is_owner_user(admin_user)


def can_reset_password(admin_user: dict) -> bool:
    return is_owner_user(admin_user)


def count_user_sessions(user_id: str) -> int:
    sessions = _load(SESSIONS_FILE)
    if not isinstance(sessions, dict):
        return 0
    now = datetime.now()
    n = 0
    for meta in sessions.values():
        if meta.get("user_id") != user_id:
            continue
        try:
            if datetime.fromisoformat(meta["expires_at"]) >= now:
                n += 1
        except Exception:
            pass
    return n


def revoke_user_sessions(user_id: str) -> int:
    sessions = _load(SESSIONS_FILE)
    if not isinstance(sessions, dict):
        return 0
    removed = [t for t, m in sessions.items() if m.get("user_id") == user_id]
    for t in removed:
        del sessions[t]
    if removed:
        _save_sessions(sessions)
    return len(removed)


def admin_reset_password(admin_user: dict, target_user_id: str, new_password: str) -> dict:
    if not can_reset_password(admin_user):
        raise ValueError("Только владелец может сбрасывать пароли")
    if len(new_password or "") < 6:
        raise ValueError("Пароль минимум 6 символов")
    users = _load(USERS_FILE)
    target = None
    for u in users:
        if u.get("id") == target_user_id:
            target = u
            break
    if not target:
        raise ValueError("Пользователь не найден")
    if target.get("role") == "owner" and not is_owner_user(admin_user):
        raise ValueError("Нельзя сбросить пароль владельца")
    salt, digest = _hash_password(new_password)
    target["password"] = f"{salt}:{digest}"
    target["updated_at"] = datetime.now().isoformat()
    _save_users(users)
    revoke_user_sessions(target_user_id)
    return _public_user(target)


def can_manage_site(user: dict | None) -> bool:
    if not user:
        return False
    if user.get("is_owner") or user.get("role") == "owner":
        return True
    return has_privilege(user, "manage_settings") or has_privilege(user, "admin")


def admin_list_users(admin_user: dict) -> list[dict]:
    if not can_manage_users(admin_user):
        raise ValueError("Недостаточно прав")
    users = _load(USERS_FILE)
    out = []
    for u in users:
        pub = _public_user(u)
        out.append({
            "id": pub["id"],
            "email": pub["email"],
            "name": pub["name"],
            "role": pub["role"],
            "role_label": pub["role_label"],
            "privileges": pub.get("privileges") or _privileges_for_role(pub["role"]),
            "is_owner": pub["is_owner"],
            "setup_complete": pub["setup_complete"],
            "created_at": pub.get("created_at"),
            "updated_at": u.get("updated_at"),
            "setup_at": u.get("setup_at"),
            "default_view": pub.get("default_view"),
            "theme": pub.get("theme"),
            "project_goal": u.get("project_goal", "")[:120],
            "disabled": bool(u.get("disabled")),
            "admin_notes": (u.get("admin_notes") or "")[:500],
            "active_sessions": count_user_sessions(pub["id"]),
            "subscription": pub.get("subscription"),
            "access_level": pub.get("access_level"),
        })
    out.sort(key=lambda x: (0 if x["is_owner"] else 1, x["email"]))
    return out


def admin_get_user(admin_user: dict, target_user_id: str) -> dict:
    if not can_manage_users(admin_user):
        raise ValueError("Недостаточно прав")
    target = _find_user(target_user_id)
    if not target:
        raise ValueError("Пользователь не найден")
    if not can_modify_user(admin_user, target):
        raise ValueError("Недостаточно прав для этого пользователя")
    pub = _public_user(target)
    return {
        **{k: pub[k] for k in ("id", "email", "name", "role", "role_label", "is_owner", "setup_complete", "default_view", "theme", "created_at", "subscription", "access_level")},
        "privileges": pub.get("privileges") or _privileges_for_role(pub["role"]),
        "updated_at": target.get("updated_at"),
        "setup_at": target.get("setup_at"),
        "project_goal": target.get("project_goal", ""),
        "disabled": bool(target.get("disabled")),
        "admin_notes": target.get("admin_notes") or "",
        "active_sessions": count_user_sessions(pub["id"]),
    }


def admin_update_user(
    admin_user: dict,
    target_user_id: str,
    *,
    role: str = None,
    name: str = None,
    tier: str = None,
    balance_delta: int = None,
    set_balance: int = None,
    privileges: list[str] | None = None,
    disabled: bool | None = None,
    admin_notes: str | None = None,
    default_view: str | None = None,
    theme: str | None = None,
) -> dict:
    if not can_manage_users(admin_user):
        raise ValueError("Недостаточно прав")
    users = _load(USERS_FILE)
    target = None
    for u in users:
        if u.get("id") == target_user_id:
            target = u
            break
    if not target:
        raise ValueError("Пользователь не найден")
    if not can_modify_user(admin_user, target):
        raise ValueError("Недостаточно прав для этого пользователя")
    if target.get("role") == "owner" and not is_owner_user(admin_user):
        raise ValueError("Нельзя изменять владельца")
    if name is not None and name.strip():
        target["name"] = name.strip()[:80]
    if role is not None:
        role = role.strip().lower()
        if role not in ROLE_PRIVILEGES:
            raise ValueError("Недопустимая роль")
        if not can_assign_role(admin_user, role):
            raise ValueError("Ваша роль не может назначать эту роль")
        if role == "owner" and not is_owner_user(admin_user):
            raise ValueError("Только владелец может назначать роль owner")
        if target.get("role") == "owner" and role != "owner":
            raise ValueError("Нельзя понизить владельца")
        target["role"] = role
        target["privileges"] = list(ROLE_PRIVILEGES[role])
    if privileges is not None:
        if not can_set_custom_privileges(admin_user):
            raise ValueError("Только владелец может задавать привилегии вручную")
        clean = []
        for p in privileges:
            if p not in ALL_PRIVILEGES:
                raise ValueError(f"Неизвестная привилегия: {p}")
            if p not in clean:
                clean.append(p)
        target["privileges"] = clean
    if disabled is not None:
        if target.get("role") == "owner":
            raise ValueError("Нельзя заблокировать владельца")
        target["disabled"] = bool(disabled)
        if disabled:
            revoke_user_sessions(target_user_id)
    if admin_notes is not None:
        target["admin_notes"] = (admin_notes or "")[:500]
    if default_view is not None:
        dv = default_view.strip().lower()
        if dv and dv in ALLOWED_DEFAULT_VIEWS:
            target["default_view"] = dv
    if theme is not None:
        th = theme.strip().lower()
        if th in ("dark", "light", "auto", ""):
            target["theme"] = th or target.get("theme", "dark")
    if tier is not None and can_set_tier(admin_user):
        from room.subscriptions import set_subscription_tier, SUBSCRIPTION_PLANS
        tier = tier.strip().lower()
        if tier not in SUBSCRIPTION_PLANS:
            raise ValueError("Недопустимый тариф")
        if tier == "owner" and target.get("role") != "owner":
            raise ValueError("Тариф Owner только для роли owner")
        set_subscription_tier(
            target_user_id,
            tier,
            users_loader=lambda: _load(USERS_FILE),
            users_saver=_save_users,
        )
        users = _load(USERS_FILE)
        target = _find_user(target_user_id) or target
    if balance_delta is not None and balance_delta != 0:
        from room.subscriptions import add_balance
        add_balance(
            target_user_id,
            balance_delta,
            users_loader=lambda: _load(USERS_FILE),
            users_saver=_save_users,
        )
        target = _find_user(target_user_id) or target
    if set_balance is not None and is_owner_user(admin_user):
        from room.subscriptions import normalize_user_billing
        normalize_user_billing(target)
        if target.get("role") != "owner":
            target["balance"] = max(0, int(set_balance))
            target["balance_updated_at"] = datetime.now().isoformat()
    target["updated_at"] = datetime.now().isoformat()
    _save_users(users)
    refreshed = _find_user(target_user_id)
    return _public_user(refreshed) if refreshed else {}
