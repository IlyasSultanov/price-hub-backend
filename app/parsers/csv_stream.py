import csv
import io
from collections.abc import Iterator
from typing import Protocol

from ..aws import get_sync_s3_client


class _ReaderOpts(Protocol):
    encoding: str
    delimiter: str
    quotechar: str


def iter_csv_rows(
    bucket: str, key: str, reader_opts: _ReaderOpts
) -> Iterator[list[str]]:
    """Stream CSV rows straight from S3 without buffering the file.

    A plain sync generator over a real file-like object (`TextIOWrapper`
    around the object's `StreamingBody`), so `csv.reader` handles quoted
    multi-line values the same way it would for a local file. Must only be
    driven from a worker thread (via `asyncio.to_thread`), never awaited
    directly on the event loop — the underlying reads are blocking.
    """
    client = get_sync_s3_client()
    response = client.get_object(Bucket=bucket, Key=key)
    body = response["Body"]
    text_stream = io.TextIOWrapper(
        body, encoding=reader_opts.encoding, errors="replace", newline=""
    )
    yield from csv.reader(
        text_stream, delimiter=reader_opts.delimiter, quotechar=reader_opts.quotechar
    )


def drain_batch(iterator: Iterator[list[str]], n: int) -> list[list[str]]:
    """Pull up to `n` rows synchronously. Call via `asyncio.to_thread` so a
    whole batch's wait time (network + CSV parsing) happens off the event
    loop in one hop, instead of once per row."""
    batch = []
    for _ in range(n):
        try:
            batch.append(next(iterator))
        except StopIteration:
            break
    return batch
