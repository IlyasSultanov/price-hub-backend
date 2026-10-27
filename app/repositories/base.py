import uuid
from collections.abc import Sequence
from typing import Any, Dict

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.db import Base

# TODO Check how it's work in new 3.12 python or 3.14 python Generic type


class BaseRepository[T: Base, CreateT: BaseModel, UpdateT: BaseModel]:
    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model

    async def get_all(
        self, skip: int = 0, limit: int = 100, filters: Dict[str, Any] | None = None
    ) -> Sequence[T]:
        smtp = select(self.model)
        if filters:
            for key, value in filters.items():
                smtp = smtp.filter(getattr(self.model, key) == value)
        smtp = smtp.offset(skip).limit(limit)
        result = await self.session.execute(smtp)
        return result.scalars().all()

    async def get_by_id(self, id: uuid.UUID) -> T:
        smtp = select(self.model).where(
            self.model.id == id, self.model.deleted_at.is_(None)
        )
        result = await self.session.execute(smtp)
        return result.scalar_one_or_none()

    async def create(self, data: CreateT | Dict[str, Any]) -> T:
        obj_data = data.model_dump() if hasattr(data, "model_dump") else data

        entity = self.model(**obj_data)
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: uuid.UUID, data: UpdateT | Dict[str, Any]) -> T | None:
        obj_data = (
            data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data
        )

        entity = await self.get_by_id(id)
        if entity is None:
            return None
        for key, value in obj_data.items():
            setattr(entity, key, value)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity
