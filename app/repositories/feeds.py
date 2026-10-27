import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Feed
from . import BaseRepository


class RepositoriesFeeds(BaseRepository[Feed, None, None]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Feed)

    async def find_duplicate(
        self, supplier_id: uuid.UUID, sha256: bytes
    ) -> Feed | None:
        today = datetime.now(UTC).date()
        stmt = select(Feed).where(
            Feed.supplier_id == supplier_id,
            Feed.sha256 == sha256,
            Feed.created_date == today,
            Feed.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_fields(
        self, feed_id: uuid.UUID, *, commit: bool = True, **fields: Any
    ) -> None:
        stmt = update(Feed).where(Feed.id == feed_id).values(**fields)
        await self.session.execute(stmt)
        if commit:
            await self.session.commit()
