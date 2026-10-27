import uuid

from sqlalchemy import Boolean, ForeignKey, Index, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..utils import FeedFormat
from .db import BaseClasses


class MappingProfile(BaseClasses):
    version: Mapped[int] = mapped_column(nullable=False)
    format: Mapped[FeedFormat] = mapped_column(
        SAEnum(
            FeedFormat,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE")
    )
    column_map: Mapped[dict[str, str]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    transforms: Mapped[dict[str, list[str]]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    reader_opts: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    rules: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    __table_args__ = (
        Index(
            "idx_mapping_profiles_supplier_id_version",
            "supplier_id",
            "version",
            unique=True,
        ),
        Index(
            "idx_mapping_profiles_supplier_id_is_active",
            "supplier_id",
            unique=True,
            postgresql_where=(is_active == True),
        ),
    )
