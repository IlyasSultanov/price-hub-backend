import uuid

from uuid_utils import uuid7


def generate_uuid() -> uuid.UUID:
    return uuid.UUID(bytes=uuid7().bytes)
