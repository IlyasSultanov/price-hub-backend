from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from ..utils import FeedStatus, SourceType


class FeedRead(BaseModel):
    id: UUID
    supplier_id: UUID
    status: FeedStatus
    source_type: SourceType
    original_filename: str | None
    file_size: int
    sha256: str
    rows_total: int
    rows_ok: int
    rows_failed: int
    matched_count: int
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("sha256", mode="before")
    @classmethod
    def _hex_encode(cls, v: object) -> object:
        return v.hex() if isinstance(v, (bytes, bytearray)) else v


class FeedUploadResponse(BaseModel):
    feed: FeedRead
    duplicate: bool

    model_config = ConfigDict(from_attributes=True)
