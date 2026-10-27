import uuid
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..utils import Currency
from .db import BaseClasses


class Offer(BaseClasses):
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False
    )
    feed_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("feeds.id", ondelete="CASCADE"), nullable=False
    )
    external_sku: Mapped[str] = mapped_column(String(255), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    title_normalized: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        SAEnum(
            Currency,
            native_enum=False,
            create_constraint=True,
            length=3,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    stock: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Matching (Этап 4) is not implemented yet; kept nullable and without a FK
    # until the `products` table and matching pipeline exist.
    product_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    match_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    match_strategy: Mapped[str | None] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        sa.UniqueConstraint(
            "supplier_id", "external_sku", name="uq_supplier_external_sku"
        ),
        Index("ix_offers_feed_id", "feed_id"),
        Index("ix_offers_supplier_barcode", "supplier_id", "barcode"),
    )
