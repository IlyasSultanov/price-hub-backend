import asyncio
import logging
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

from ...core import settings
from ...models.db import db
from ...parsers import drain_batch, iter_csv_rows
from ...repositories import (
    RepositoriesFeeds,
    RepositoriesFeedsErrors,
    RepositoriesMappingProfiles,
    RepositoriesOffers,
    RepositoriesSuppliers,
)
from ...schemas.mapping_profiles import ReaderOpts, Rules
from ...utils import Currency, FeedFormat, FeedStatus
from .row_mapper import RowMapper

logger = logging.getLogger(__name__)

BATCH_SIZE = 5000
MAX_STORED_ERRORS = 10_000


class PermanentParseError(Exception):
    """Config/data problem that a retry can't fix (bad file, no profile)."""


async def _consume_header(
    rows_iter: Iterator[list[str]], reader_opts: ReaderOpts
) -> dict[str, int]:
    rows_skipped = 0
    while True:
        batch = await asyncio.to_thread(drain_batch, rows_iter, 1)
        if not batch:
            raise PermanentParseError("file is empty or has no header row")
        row = batch[0]
        if reader_opts.skip_blank_lines and not any(
            cell.strip() for cell in row if cell
        ):
            continue
        if rows_skipped < reader_opts.header_row:
            rows_skipped += 1
            continue
        return {name.strip(): idx for idx, name in enumerate(row)}


async def parse_feed(feed_id: uuid.UUID) -> None:
    """Stream a feed's CSV out of S3, map it through its active mapping
    profile, and write the resulting offers + a capped error report to the
    DB in bounded batches (FR-2.2/2.3/2.6/2.8/2.9).

    Deliberately stops short of matching/pricing/publishing (Этап 4): a feed
    that finishes here lands on COMPLETED/PARTIALLY_COMPLETED/FAILED.
    """
    async with db.async_factory() as session:
        feeds_repo = RepositoriesFeeds(session)
        suppliers_repo = RepositoriesSuppliers(session)
        profiles_repo = RepositoriesMappingProfiles(session)
        offers_repo = RepositoriesOffers(session)
        errors_repo = RepositoriesFeedsErrors(session)

        feed = await feeds_repo.get_by_id(feed_id)
        if feed is None:
            logger.warning("parse_feed: feed %s not found", feed_id)
            return
        if feed.status not in (FeedStatus.UPLOADED, FeedStatus.QUEUED):
            logger.info(
                "parse_feed: feed %s already in status %s, skipping",
                feed_id,
                feed.status,
            )
            return

        supplier = await suppliers_repo.get_by_id(feed.supplier_id)
        if supplier is None:
            await feeds_repo.set_fields(
                feed_id, status=FeedStatus.FAILED, finished_at=datetime.now(UTC)
            )
            return

        try:
            profile = await profiles_repo.get_active_for_supplier(
                feed.supplier_id, FeedFormat.CSV
            )
            if profile is None:
                raise PermanentParseError(
                    "no active CSV mapping profile configured for this supplier"
                )

            reader_opts = ReaderOpts(**profile.reader_opts)
            rules = Rules(**profile.rules)
            mapper = RowMapper(
                profile.column_map,
                profile.transforms,
                rules,
                Currency(supplier.currency),
            )

            await feeds_repo.set_fields(
                feed_id,
                status=FeedStatus.PARSING,
                started_at=datetime.now(UTC),
                profile_id=profile.id,
                profile_version=profile.version,
            )

            bucket = settings.minio_config.bucket
            rows_iter = iter_csv_rows(bucket, feed.file_key, reader_opts)
            header_index = await _consume_header(rows_iter, reader_opts)

            cancelled = await _process_rows(
                feed_id=feed.id,
                supplier_id=feed.supplier_id,
                rows_iter=rows_iter,
                header_index=header_index,
                reader_opts=reader_opts,
                mapper=mapper,
                on_duplicate_sku=rules.on_duplicate_sku or "last_wins",
                feeds_repo=feeds_repo,
                offers_repo=offers_repo,
                errors_repo=errors_repo,
            )

            if cancelled:
                await feeds_repo.set_fields(
                    feed_id, status=FeedStatus.CANCELLED, finished_at=datetime.now(UTC)
                )
                return

            fresh = await feeds_repo.get_by_id(feed_id)
            if fresh.rows_failed == 0:
                final_status = FeedStatus.COMPLETED
            elif fresh.rows_ok > 0:
                final_status = FeedStatus.PARTIALLY_COMPLETED
            else:
                final_status = FeedStatus.FAILED
            await feeds_repo.set_fields(
                feed_id, status=final_status, finished_at=datetime.now(UTC)
            )

        except PermanentParseError as exc:
            logger.warning("feed %s failed permanently: %s", feed_id, exc)
            await feeds_repo.set_fields(
                feed_id,
                status=FeedStatus.FAILED,
                finished_at=datetime.now(UTC),
                error_summary={"permanent_error": 1},
            )
        except Exception:
            logger.exception("feed %s parsing crashed", feed_id)
            await feeds_repo.set_fields(
                feed_id, status=FeedStatus.FAILED, finished_at=datetime.now(UTC)
            )
            raise


async def _process_rows(
    *,
    feed_id: uuid.UUID,
    supplier_id: uuid.UUID,
    rows_iter: Iterator[list[str]],
    header_index: dict[str, int],
    reader_opts: ReaderOpts,
    mapper: RowMapper,
    on_duplicate_sku: str,
    feeds_repo: RepositoriesFeeds,
    offers_repo: RepositoriesOffers,
    errors_repo: RepositoriesFeedsErrors,
) -> bool:
    """Drains `rows_iter` in bounded batches, persisting as it goes.
    Returns True if the feed's cancel flag was observed mid-stream."""
    row_number = 0
    rows_total = rows_ok = rows_failed = 0
    error_summary: dict[str, int] = {}
    stored_errors = 0

    while True:
        raw_batch = await asyncio.to_thread(drain_batch, rows_iter, BATCH_SIZE)
        if not raw_batch:
            break

        fresh = await feeds_repo.get_by_id(feed_id)
        if fresh is not None and fresh.cancel_requested:
            return True

        offers_batch: list[dict[str, Any]] = []
        offers_row_numbers: list[int] = []
        error_rows: list[dict[str, Any]] = []

        for raw_row in raw_batch:
            row_number += 1
            if reader_opts.skip_blank_lines and not any(
                cell.strip() for cell in raw_row if cell
            ):
                continue

            outcome = mapper.map_row(header_index, raw_row)
            if outcome.offer is None and not outcome.error_rows:
                continue  # filtered row (service row / skip regex), not counted

            rows_total += 1
            for err in outcome.error_rows:
                error_rows.append({**err, "row_number": row_number})

            if outcome.offer is not None:
                offer = dict(outcome.offer)
                offer["supplier_id"] = supplier_id
                offer["feed_id"] = feed_id
                offers_batch.append(offer)
                offers_row_numbers.append(row_number)
                rows_ok += 1
            else:
                rows_failed += 1

        if offers_batch:
            rejected_indices = await offers_repo.upsert_batch(
                offers_batch, feed_id=feed_id, on_duplicate_sku=on_duplicate_sku
            )
            if on_duplicate_sku == "reject_row":
                for idx in rejected_indices:
                    rows_ok -= 1
                    rows_failed += 1
                    error_rows.append(
                        {
                            "field": "external_sku",
                            "code": "duplicate_sku",
                            "raw_value": offers_batch[idx]["external_sku"],
                            "row_number": offers_row_numbers[idx],
                        }
                    )

        for err in error_rows:
            error_summary[err["code"]] = error_summary.get(err["code"], 0) + 1

        if error_rows and stored_errors < MAX_STORED_ERRORS:
            to_store = error_rows[: MAX_STORED_ERRORS - stored_errors]
            await errors_repo.bulk_insert(
                [
                    {
                        "feed_id": feed_id,
                        "row_number": e["row_number"] or 0,
                        "field": e["field"],
                        "code": e["code"],
                        "raw_value": e.get("raw_value"),
                    }
                    for e in to_store
                ]
            )
            stored_errors += len(to_store)

        await feeds_repo.set_fields(
            feed_id,
            rows_total=rows_total,
            rows_ok=rows_ok,
            rows_failed=rows_failed,
            error_summary=error_summary,
            last_offset=row_number,
        )

    return False
