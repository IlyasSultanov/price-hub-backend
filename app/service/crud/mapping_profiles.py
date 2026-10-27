from ...core.security import Principal, ensure_supplier_access
from ...models import MappingProfile
from ...repositories import RepositoriesMappingProfiles
from ...schemas import MappingProfileCreate


class CrudMappingProfiles:
    def __init__(self, repository: RepositoriesMappingProfiles):
        self.repository = repository

    async def create(
        self, data: MappingProfileCreate, principal: Principal
    ) -> MappingProfile:
        ensure_supplier_access(principal, data.supplier_id)

        next_version = await self.repository.get_next_version(data.supplier_id)
        await self.repository.deactivate_active(data.supplier_id)

        profile_data = {
            "supplier_id": data.supplier_id,
            "format": data.format,
            "version": next_version,
            "column_map": data.column_map,
            "transforms": data.transforms,
            "reader_opts": data.reader_opts.model_dump(),
            "rules": data.rules.model_dump(),
            "is_active": True,
        }
        return await self.repository.create(profile_data)
