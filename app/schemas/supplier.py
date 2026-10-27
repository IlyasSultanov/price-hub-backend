from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ..utils import SupplierStatus


class SupplierSchemas(BaseModel):
    id: UUID
    name: str
    slug: str
    status: SupplierStatus
    currency: str = Field(max_length=3, json_schema_extra={"example": "RUB"})
    rating: Decimal
    quota_mb: int

    model_config = ConfigDict(
        from_attributes=True,
    )


class SupplierCreate(BaseModel):
    name: str
    slug: str
    status: SupplierStatus
    currency: str
    rating: Decimal
    quota_mb: int
    model_config = ConfigDict(
        from_attributes=True,
    )


class SupplierRead(SupplierSchemas):
    pass
