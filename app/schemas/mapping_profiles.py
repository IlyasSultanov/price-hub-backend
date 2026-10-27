import codecs
import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..parsers import TRANSFORMS
from ..utils import FeedFormat

ALLOWED_FIELDS = frozenset(
    {
        "external_sku",
        "barcode",
        "mfr_article",
        "brand",
        "title",
        "description",
        "category_raw",
        "price",
        "old_price",
        "currency",
        "stock",
        "available",
    }
)

REQUIRED_FIELDS = frozenset({"external_sku", "title", "price"})


class ReaderOpts(BaseModel):
    encoding: str = "utf-8"
    delimiter: str = ","
    quotechar: str = '"'
    header_row: int = 0
    skip_blank_lines: bool = True

    @field_validator("encoding")
    @classmethod
    def validate_encoding(cls, v: str) -> str:
        try:
            return codecs.lookup(v).name
        except LookupError as exc:
            raise ValueError(f"unknown encoding: {v}") from exc

    model_config = ConfigDict(extra="forbid")


class Rules(BaseModel):
    on_negative_stock: Literal["reject_row", "set_zero", "keep"] | None = None
    on_duplicate_sku: Literal["last_wins", "first_wins", "reject_row"] | None = None
    service_row_heuristic: Literal["only_first_column_filled"] | None = None
    stock_text_map: dict[str, int] = {}
    skip_row_if_title_matches: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("skip_row_if_title_matches")
    @classmethod
    def _valid_regex(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                re.compile(v)
            except re.error as exc:
                raise ValueError(f"invalid regex: {exc}") from exc
        return v


class MappingProfileCreate(BaseModel):
    format: FeedFormat
    supplier_id: uuid.UUID
    column_map: dict[str, str]
    transforms: dict[str, list[str]] = Field(default_factory=dict)
    reader_opts: ReaderOpts = Field(default_factory=ReaderOpts)
    rules: Rules = Field(default_factory=Rules)

    @field_validator("column_map")
    @classmethod
    def validate_column_map(cls, v: dict[str, str]) -> dict[str, str]:
        if unknown := set(v) - ALLOWED_FIELDS:
            raise ValueError(f"unknown fields in column_map: {sorted(unknown)}")
        if missing := REQUIRED_FIELDS - set(v):
            raise ValueError(f"missing fields in column_map: {sorted(missing)}")
        if empty := [field for field, col in v.items() if not col.strip()]:
            raise ValueError(f"empty values in column_map for fields: {sorted(empty)}")
        return v

    @field_validator("transforms")
    @classmethod
    def validate_transforms(cls, v: dict[str, list[str]]) -> dict[str, list[str]]:
        if unknown := set(v) - ALLOWED_FIELDS:
            raise ValueError(f"unknown fields in transforms: {sorted(unknown)}")
        for k, val in v.items():
            if bad := [t for t in val if t not in TRANSFORMS]:
                raise ValueError(f"unknown transforms for field {k}: {sorted(bad)}")
        return v

    model_config = ConfigDict(
        extra="forbid",
    )


class MappingProfileRead(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID
    format: FeedFormat
    version: int
    column_map: dict[str, str]
    transforms: dict[str, list[str]]
    reader_opts: ReaderOpts
    rules: Rules
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
