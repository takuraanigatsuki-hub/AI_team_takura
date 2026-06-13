"""JWT и хеширование паролей."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from api.config import get_settings


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return salt, digest


def encode_password(password: str, salt: str | None = None) -> str:
    salt, digest = hash_password(password, salt)
    return f"{salt}:{digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split(":", 1)
        _, check = hash_password(password, salt)
        return secrets.compare_digest(check, digest)
    except Exception:
        return False


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings["jwt_expire_minutes"])
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings["jwt_secret"], algorithm=settings["jwt_algorithm"])


def decode_access_token(token: str) -> str | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings["jwt_secret"],
            algorithms=[settings["jwt_algorithm"]],
        )
        subject = payload.get("sub")
        return subject if isinstance(subject, str) and subject else None
    except JWTError:
        return None
