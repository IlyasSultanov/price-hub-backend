import uuid

from ...models import Supplier
from ...repositories import RepositoriesSuppliers
from ...schemas import SupplierCreate, SupplierRead


class CrudSuppliers:
    def __init__(self, repositories: RepositoriesSuppliers):
        self.repositories = repositories

    async def create(self, data: SupplierCreate) -> Supplier:
        result = await self.repositories.create(data)
        return result

    async def get_id(self, supplier_id: uuid.UUID) -> Supplier:
        result = await self.repositories.get_by_id(supplier_id)
        return result

    async def get_all(self, skip: int, limit: int) -> list[Supplier]:
        result = await self.repositories.get_all(skip=skip, limit=limit)
        return result
