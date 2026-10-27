import logging

from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

from ..core.config import settings

broker = AioPikaBroker(
    url=settings.rabbit_config.url,
).with_result_backend(RedisAsyncResultBackend(settings.redis_config.url))

logger = logging.getLogger(__name__)


async def start_broker():
    try:
        await broker.startup()
    except Exception as e:
        logger.warning("Error starting broker %s", str(e))
        pass


async def stop_broker():
    try:
        await broker.shutdown()
    except Exception as e:
        logger.warning("Error stopping broker %s", str(e))
        pass
