from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Supplier
from . import BaseRepository


class RepositoriesSuppliers(BaseRepository[Supplier, None, None]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Supplier)
