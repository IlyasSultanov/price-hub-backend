import hashlib
import logging
import uuid
from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy.exc import IntegrityError

from ...core.security import Principal, ensure_supplier_access
from ...models import Feed, Supplier
from ...repositories import RepositoriesFeeds
from ...utils import FeedStatus, SourceType, generate_uuid, sniff_format

logger = logging.getLogger(__name__)

MAX_FEED_FILE_SIZE = 1024 * 1024 * 1024  # 1 GiB ceiling, FR-1.1
UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024  # above S3's 5 MiB minimum multipart part size


class EmptyFeedFile(ValueError):
    pass


class FeedTooLarge(ValueError):
    pass


@dataclass
class FeedUploadResult:
    feed: Feed
    duplicate: bool


class CrudFeeds:
    def __init__(self, repository: RepositoriesFeeds, s3, bucket: str):
        self.repository = repository
        self.s3 = s3
        self.bucket = bucket

    async def get_by_id(self, feed_id: uuid.UUID, principal: Principal) -> Feed | None:
        feed = await self.repository.get_by_id(feed_id)
        if feed is not None:
            ensure_supplier_access(principal, feed.supplier_id)
        return feed

    async def upload_feed(
        self, supplier: Supplier, file: UploadFile, principal: Principal
    ) -> FeedUploadResult:
        ensure_supplier_access(principal, supplier.id)

        first_chunk = await file.read(UPLOAD_CHUNK_SIZE)
        if not first_chunk:
            raise EmptyFeedFile("uploaded file is empty")

        sniff_format(first_chunk, file.filename or "")

        max_size = min(MAX_FEED_FILE_SIZE, supplier.quota_mb * 1024 * 1024)
        feed_id = generate_uuid()
        key = f"feeds/{supplier.id}/{feed_id}/{file.filename}"

        total_size, sha256 = await self._stream_to_s3(key, file, first_chunk, max_size)

        existing = await self.repository.find_duplicate(supplier.id, sha256)
        if existing is not None:
            await self._delete_object(key)
            return FeedUploadResult(feed=existing, duplicate=True)

        feed_data = {
            "id": feed_id,
            "supplier_id": supplier.id,
            "source_type": SourceType.UPLOAD,
            "status": FeedStatus.UPLOADED,
            "file_key": key,
            "original_filename": file.filename,
            "file_size": total_size,
            "sha256": sha256,
        }
        try:
            created = await self.repository.create(feed_data)
        except IntegrityError:
            await self.repository.session.rollback()
            await self._delete_object(key)
            existing = await self.repository.find_duplicate(supplier.id, sha256)
            if existing is None:
                raise
            return FeedUploadResult(feed=existing, duplicate=True)

        await self._enqueue_parsing(created.id)
        return FeedUploadResult(feed=created, duplicate=False)

    async def _enqueue_parsing(self, feed_id: uuid.UUID) -> None:
        from ...workers import parse_feed_task

        try:
            await parse_feed_task.kiq(str(feed_id))
        except Exception:
            # Upload already succeeded and the feed is durably `uploaded` in
            # the DB; failing to enqueue just leaves it there for a manual
            # or scheduled retry instead of failing the HTTP request.
            logger.exception("failed to enqueue parsing for feed %s", feed_id)

    async def _stream_to_s3(
        self, key: str, file: UploadFile, first_chunk: bytes, max_size: int
    ) -> tuple[int, bytes]:
        digest = hashlib.sha256()
        total_size = 0
        buffer = bytearray()
        parts: list[dict] = []
        part_number = 1

        create = await self.s3.create_multipart_upload(Bucket=self.bucket, Key=key)
        upload_id = create["UploadId"]

        async def flush(data: bytes) -> None:
            nonlocal part_number
            resp = await self.s3.upload_part(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                PartNumber=part_number,
                Body=data,
            )
            parts.append({"ETag": resp["ETag"], "PartNumber": part_number})
            part_number += 1

        try:
            chunk = first_chunk
            while chunk:
                digest.update(chunk)
                total_size += len(chunk)
                if total_size > max_size:
                    raise FeedTooLarge(f"file exceeds maximum size of {max_size} bytes")

                buffer.extend(chunk)
                if len(buffer) >= UPLOAD_CHUNK_SIZE:
                    await flush(bytes(buffer))
                    buffer.clear()

                chunk = await file.read(UPLOAD_CHUNK_SIZE)

            if buffer:
                await flush(bytes(buffer))

            await self.s3.complete_multipart_upload(
                Bucket=self.bucket,
                Key=key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
            )
        except Exception:
            await self.s3.abort_multipart_upload(
                Bucket=self.bucket, Key=key, UploadId=upload_id
            )
            raise

        return total_size, digest.digest()

    async def _delete_object(self, key: str) -> None:
        await self.s3.delete_object(Bucket=self.bucket, Key=key)
