import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from .db import BaseClasses


class FeedsError(BaseClasses):
    feed_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feeds.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(nullable=False)
    field: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
