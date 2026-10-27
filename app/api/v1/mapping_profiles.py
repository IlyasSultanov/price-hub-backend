from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.depends import get_service_mapping_profiles
from app.core.security import Principal, require_roles
from app.schemas import MappingProfileCreate, MappingProfileRead
from app.service.crud import CrudMappingProfiles
from app.utils import UserRole

router = APIRouter(prefix="/mapping-profiles", tags=["Mapping Profiles"])

_can_manage_profiles = require_roles(
    UserRole.SUPPLIER_MANAGER, UserRole.CATALOG_ADMIN, UserRole.SYSTEM_ADMIN
)


@router.post("", response_model=MappingProfileRead, status_code=status.HTTP_201_CREATED)
async def create_mapping_profile(
    data: MappingProfileCreate,
    service: Annotated[CrudMappingProfiles, Depends(get_service_mapping_profiles)],
    principal: Annotated[Principal, Depends(_can_manage_profiles)],
) -> MappingProfileRead:
    profile = await service.create(data, principal)
    return MappingProfileRead.model_validate(profile)
