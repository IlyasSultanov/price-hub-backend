import uuid
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Offer
from . import BaseRepository

_UPDATABLE_COLUMNS = (
    "feed_id",
    "barcode",
    "brand",
    "title",
    "title_normalized",
    "price",
    "currency",
    "stock",
)


class RepositoriesOffers(BaseRepository[Offer, None, None]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, model=Offer)

    async def upsert_batch(
        self,
        rows: list[dict[str, Any]],
        *,
        feed_id: uuid.UUID,
        on_duplicate_sku: str = "last_wins",
    ) -> set[int]:
        """Upsert a batch of offer rows, keyed by (supplier_id, external_sku).

        Returns the set of indices into `rows` that were NOT written because
        an earlier row already claims that sku — either earlier in this same
        batch, or in an earlier batch of this same feed. Always empty under
        `last_wins` (every row wins, including over itself: the last
        occurrence of a repeated sku is what ends up persisted).

        A single `INSERT ... ON CONFLICT DO UPDATE` can't target the same
        conflicting row twice (Postgres raises CardinalityViolationError), so
        same-sku rows within the batch are collapsed to one before the SQL
        call: last occurrence under `last_wins`, first occurrence otherwise.
        """
        if not rows:
            return set()

        kept_row_by_sku: dict[str, dict[str, Any]] = {}
        kept_index_by_sku: dict[str, int] = {}
        rejected_indices: set[int] = set()

        for i, row in enumerate(rows):
            sku = row["external_sku"]
            if sku not in kept_row_by_sku:
                kept_row_by_sku[sku] = row
                kept_index_by_sku[sku] = i
            elif on_duplicate_sku == "last_wins":
                kept_row_by_sku[sku] = row
                kept_index_by_sku[sku] = i
            else:
                rejected_indices.add(i)

        stmt = pg_insert(Offer.__table__).values(list(kept_row_by_sku.values()))

        if on_duplicate_sku == "last_wins":
            where_clause = None
        else:
            # first_wins / reject_row: only let the *first* row from this
            # feed claim the sku; a conflicting row already written by this
            # same feed (an earlier batch) is left alone.
            where_clause = Offer.__table__.c.feed_id.is_distinct_from(feed_id)

        update_stmt = stmt.on_conflict_do_update(
            constraint="uq_supplier_external_sku",
            set_={col: getattr(stmt.excluded, col) for col in _UPDATABLE_COLUMNS},
            where=where_clause,
        ).returning(Offer.__table__.c.external_sku)

        result = await self.session.execute(update_stmt)
        accepted_skus = {row[0] for row in result.fetchall()}

        if on_duplicate_sku != "last_wins":
            for sku, idx in kept_index_by_sku.items():
                if sku not in accepted_skus:
                    rejected_indices.add(idx)

        return rejected_indices
