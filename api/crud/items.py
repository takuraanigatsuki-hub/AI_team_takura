"""CRUD для items."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import Item
from api.schemas import ItemCreate, ItemUpdate


async def create_item(db: AsyncSession, owner_id: str, data: ItemCreate) -> Item:
    item = Item(
        owner_id=owner_id,
        title=data.title.strip(),
        description=data.description.strip(),
        status=data.status,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def list_items(
    db: AsyncSession,
    owner_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Item], int]:
    count_result = await db.execute(
        select(func.count()).select_from(Item).where(Item.owner_id == owner_id)
    )
    total = int(count_result.scalar_one())
    result = await db.execute(
        select(Item)
        .where(Item.owner_id == owner_id)
        .order_by(Item.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all()), total


async def get_item(db: AsyncSession, owner_id: str, item_id: str) -> Item | None:
    result = await db.execute(
        select(Item).where(Item.id == item_id, Item.owner_id == owner_id)
    )
    return result.scalar_one_or_none()


async def update_item(
    db: AsyncSession,
    item: Item,
    data: ItemUpdate,
) -> Item:
    if data.title is not None:
        item.title = data.title.strip()
    if data.description is not None:
        item.description = data.description.strip()
    if data.status is not None:
        item.status = data.status
    await db.flush()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item: Item) -> None:
    await db.delete(item)
    await db.flush()
