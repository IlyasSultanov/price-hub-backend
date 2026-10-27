import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import MappingProfile
from ..utils import FeedFormat
from . import BaseRepository


class RepositoriesMappingProfiles(BaseRepository[MappingProfile, None, None]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, model=MappingProfile)

    async def get_active_for_supplier(
        self, supplier_id: uuid.UUID, format: FeedFormat
    ) -> MappingProfile | None:
        stmt = select(MappingProfile).where(
            MappingProfile.supplier_id == supplier_id,
            MappingProfile.format == format,
            MappingProfile.is_active.is_(True),
            MappingProfile.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_version(self, supplier_id: uuid.UUID) -> int:
        stmt = select(MappingProfile.version).where(
            MappingProfile.supplier_id == supplier_id
        )
        result = await self.session.execute(stmt)
        versions = result.scalars().all()
        return (max(versions) if versions else 0) + 1

    async def deactivate_active(self, supplier_id: uuid.UUID) -> None:
        stmt = (
            update(MappingProfile)
            .where(
                MappingProfile.supplier_id == supplier_id,
                MappingProfile.is_active.is_(True),
            )
            .values(is_active=False)
        )
        await self.session.execute(stmt)
