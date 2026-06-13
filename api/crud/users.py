"""CRUD для пользователей."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import User
from api.schemas import UserCreate
from api.security import encode_password


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email.strip().lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(
        email=data.email.strip().lower(),
        name=(data.name or data.email.split("@")[0]).strip()[:120],
        hashed_password=encode_password(data.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
