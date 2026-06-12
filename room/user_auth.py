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
    "all_views",
    "skip_setup",
]

ROLE_PRIVILEGES = {
    "owner": ALL_PRIVILEGES,
    "admin": [p for p in ALL_PRIVILEGES if p != "manage_users"],
    "member": [],
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
            return u
    return None


def _find_user(user_id: str) -> Optional[dict]:
    for u in _load(USERS_FILE):
        if u.get("id") == user_id:
            return u
    return None


def _public_user(user: dict) -> dict:
    role = user.get("role", "member")
    privs = user.get("privileges") or _privileges_for_role(role)
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name", ""),
        "role": role,
        "privileges": privs,
        "is_owner": role == "owner",
        "setup_complete": bool(user.get("setup_complete")),
        "default_view": user.get("default_view", "dashboard"),
        "created_at": user.get("created_at"),
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
    return _public_user(user) if user else None


def complete_setup(user_id: str, *, name: str = "", goal: str = "",
                   default_view: str = "dashboard", theme: str = "") -> dict:
    users = _load(USERS_FILE)
    updated = None
    for u in users:
        if u.get("id") == user_id:
            if name:
                u["name"] = name.strip()[:80]
            if default_view in ("studio", "dashboard", "chat", "kanban"):
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

    for u in users:
        if u.get("email") == email:
            u["password"] = pw
            u["role"] = "owner"
            u["privileges"] = list(ALL_PRIVILEGES)
            u["setup_complete"] = True
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
        }
        users.append(updated)

    _save_users(users)
    return _public_user(updated)
