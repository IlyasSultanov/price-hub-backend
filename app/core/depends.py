import uuid
from typing import Annotated

from fastapi import Depends, Form, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Supplier
from ..models.db import db
from ..repositories import (
    RepositoriesFeeds,
    RepositoriesMappingProfiles,
    RepositoriesSuppliers,
)
from ..service.auth import UserManager, user_manager_dependency
from ..service.crud import CrudFeeds, CrudMappingProfiles, CrudSuppliers
from .config import settings


async def get_session(db: AsyncSession = Depends(db.get_db)) -> AsyncSession:  # noqa: B008
    return db


async def suppliers_repositories(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RepositoriesSuppliers:
    return RepositoriesSuppliers(session)


async def get_service_suppliers(
    repository: RepositoriesSuppliers = Depends(suppliers_repositories),  # noqa: B008
) -> CrudSuppliers:
    return CrudSuppliers(repository)


def get_s3(request: Request):
    return request.app.state.s3


async def feeds_repositories(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RepositoriesFeeds:
    return RepositoriesFeeds(session)


async def get_service_feeds(
    repository: RepositoriesFeeds = Depends(feeds_repositories),  # noqa: B008
    s3=Depends(get_s3),  # noqa: B008
) -> CrudFeeds:
    return CrudFeeds(repository, s3, bucket=settings.minio_config.bucket)


async def get_feed_supplier(
    supplier_id: Annotated[uuid.UUID, Form()],
    repository: RepositoriesSuppliers = Depends(suppliers_repositories),  # noqa: B008
) -> Supplier:
    supplier = await repository.get_by_id(supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail=f"supplier {supplier_id} not found")
    return supplier


async def mapping_profiles_repositories(
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> RepositoriesMappingProfiles:
    return RepositoriesMappingProfiles(session)


async def get_service_mapping_profiles(
    repository: RepositoriesMappingProfiles = Depends(  # noqa: B008
        mapping_profiles_repositories
    ),
) -> CrudMappingProfiles:
    return CrudMappingProfiles(repository)


async def get_user_manager(
    user_manager: UserManager = Depends(user_manager_dependency),  # noqa: B008
) -> UserManager:
    return user_manager
