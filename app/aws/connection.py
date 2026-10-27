import boto3
from aioboto3 import Session
from botocore.config import Config

from ..core import settings


BOTO_CONFIG = Config(
    signature_version="s3v4",
    s3={"addressing_style": "path"},
    max_pool_connections=10,
    retries={"max_attempts": 10, "mode": "standard"},
    connect_timeout=10,
    read_timeout=10,
)

_session = Session()


def get_s3_client():
    return _session.client(
        "s3",
        endpoint_url=settings.minio_config.minio_url,
        aws_access_key_id=settings.minio_config.access_key,
        aws_secret_access_key=settings.minio_config.secret_key,
        region_name=settings.minio_config.region,
        config=BOTO_CONFIG,
    )


def get_sync_s3_client():
    """Plain (blocking) boto3 client for worker tasks that stream-parse an
    object with a sync, file-like reader (`csv.reader`, `io.TextIOWrapper`).
    Meant to be driven from a thread (`asyncio.to_thread`), never awaited
    directly from the event loop."""
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_config.minio_url,
        aws_access_key_id=settings.minio_config.access_key,
        aws_secret_access_key=settings.minio_config.secret_key,
        region_name=settings.minio_config.region,
        config=BOTO_CONFIG,
    )
