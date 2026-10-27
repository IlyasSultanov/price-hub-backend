from decimal import Decimal
from sqlalchemy import Enum as SAEnum, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Numeric, text, CheckConstraint

from .db import BaseClasses
from ..utils import SupplierStatus


class Supplier(BaseClasses):
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        SAEnum(
            SupplierStatus,
            native_enum=False,
            create_constraint=True,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        default=SupplierStatus.ACTIVE,
        server_default=SupplierStatus.ACTIVE.value,
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    rating: Mapped[Decimal] = mapped_column(
        Numeric(3, 2), nullable=False, default=Decimal("0.00"), server_default=text("0")
    )
    quota_mb: Mapped[int] = mapped_column(Integer, nullable=False, default=500)

    __table_args__ = (
        CheckConstraint(
            "rating >= 0 AND rating <= 5",
            name="ck_supplier_rating_range",
        ),
    )
