import uuid
from datetime import datetime

from sqlalchemy import ARRAY, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from ..utils import KeyTier
from .db import BaseClasses


class ApiKey(BaseClasses):
    key_hash: Mapped[bytes] = mapped_column(nullable=False, unique=True)
    prefix: Mapped[str] = mapped_column(nullable=False)
    tier: Mapped[str] = mapped_column(
        SAEnum(
            KeyTier,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=KeyTier.FREE,
        server_default=KeyTier.FREE.value,
        nullable=False,
    )
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    supplier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("suppliers.id"))
