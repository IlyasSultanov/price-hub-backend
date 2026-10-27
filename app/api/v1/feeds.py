import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.core.depends import get_feed_supplier, get_service_feeds
from app.core.security import Principal, require_roles
from app.models import Supplier
from app.schemas import FeedRead, FeedUploadResponse
from app.service.crud import CrudFeeds
from app.service.crud.feeds import EmptyFeedFile, FeedTooLarge
from app.utils import UserRole
from app.utils.file_signature import UnsupportedFeedFormat

router = APIRouter(prefix="/feeds", tags=["Feeds"])

_can_manage_feeds = require_roles(
    UserRole.SUPPLIER_MANAGER, UserRole.CATALOG_ADMIN, UserRole.SYSTEM_ADMIN
)


@router.post("", response_model=FeedUploadResponse)
async def upload_feed(
    response: Response,
    file: Annotated[UploadFile, File()],
    supplier: Annotated[Supplier, Depends(get_feed_supplier)],
    service: Annotated[CrudFeeds, Depends(get_service_feeds)],
    principal: Annotated[Principal, Depends(_can_manage_feeds)],
) -> FeedUploadResponse:
    try:
        result = await service.upload_feed(supplier, file, principal)
    except EmptyFeedFile as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except UnsupportedFeedFormat as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except FeedTooLarge as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    if result.duplicate:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_202_ACCEPTED
        response.headers["Location"] = f"/api/v1/feeds/{result.feed.id}"

    return FeedUploadResponse(
        feed=FeedRead.model_validate(result.feed), duplicate=result.duplicate
    )


@router.get("/{feed_id}", response_model=FeedRead)
async def get_feed(
    feed_id: uuid.UUID,
    service: Annotated[CrudFeeds, Depends(get_service_feeds)],
    principal: Annotated[Principal, Depends(_can_manage_feeds)],
) -> FeedRead:
    feed = await service.get_by_id(feed_id, principal)
    if feed is None:
        raise HTTPException(status_code=404, detail=f"feed {feed_id} not found")
    return FeedRead.model_validate(feed)
