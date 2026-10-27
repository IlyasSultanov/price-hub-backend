import enum
import uuid
from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..utils import FeedStatus, SourceType
from .db import BaseClasses


def _enum_col(e: type[enum.Enum], default):
    return mapped_column(
        SAEnum(
            e,
            native_enum=False,
            create_constraint=True,
            length=24,
            values_callable=lambda x: [m.value for m in x],
        ),
        nullable=False,
        default=default,
        server_default=default.value,
    )


class Feed(BaseClasses):
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("mapping_profiles.id", ondelete="SET NULL"),
        nullable=True,
    )
    profile_version: Mapped[int | None] = mapped_column(nullable=True)

    status: Mapped[FeedStatus] = _enum_col(FeedStatus, FeedStatus.UPLOADED)
    source_type: Mapped[SourceType] = _enum_col(SourceType, SourceType.UPLOAD)

    file_key: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)

    rows_total: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    rows_ok: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    rows_failed: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    matched_count: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )

    error_summary: Mapped[dict[str, int]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    last_offset: Mapped[int] = mapped_column(
        nullable=False, default=0, server_default="0"
    )
    cancel_requested: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_date: Mapped[date] = mapped_column(
        Computed("(created_at AT TIME ZONE 'UTC')::date", persisted=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("supplier_id", "sha256", "created_date", name="uq_feed_dedup"),
        sa.CheckConstraint(
            "rows_ok + rows_failed <= rows_total", name="ck_feed_row_counts"
        ),
        Index("ix_feed_supplier_created", "supplier_id", sa.desc("created_at")),
    )
