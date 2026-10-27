from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import FeedsError
from . import BaseRepository


class RepositoriesFeedsErrors(BaseRepository[FeedsError, None, None]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, model=FeedsError)

    async def bulk_insert(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        await self.session.execute(FeedsError.__table__.insert(), rows)
