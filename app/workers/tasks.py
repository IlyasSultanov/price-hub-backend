import logging
import uuid

from ..service.feeds import parse_feed
from .brokers import broker

logger = logging.getLogger(__name__)


@broker.task(task_name="parse_feed_task")
async def parse_feed_task(feed_id: str) -> None:
    """Taskiq entrypoint: takes an id, not an object (AS-2)."""
    await parse_feed(uuid.UUID(feed_id))
