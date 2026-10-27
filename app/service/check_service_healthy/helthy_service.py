import logging
from dataclasses import dataclass

import aio_pika

from typing import Dict

from sqlalchemy import text

from redis.asyncio import Redis

from ...models.db import database_connection
from ...core import settings

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    ok: bool
    details: str | None = None


class HealthCheck:
    async def check_db(self) -> CheckResult:
        try:
            async with database_connection.async_factory() as session:
                await session.execute(text("SELECT 1"))
            return CheckResult(ok=True)
        except Exception as e:
            logger.warning("PostgreSQL healthcheck failed", exc_info=True)
            return CheckResult(ok=False, details=str(e))

    async def check_rabbitmq(self) -> CheckResult:
        connection = None
        try:
            connection = await aio_pika.connect_robust(
                url=settings.rabbit_config.url, timeout=settings.rabbit_config.timeout
            )

            async with connection.channel():
                return CheckResult(ok=True)
        except Exception as e:
            logger.warning("RabbitMQ healthcheck failed", exc_info=True)
            return CheckResult(ok=False, details=str(e))
        finally:
            await connection.close()

    async def check_redis(self) -> CheckResult:
        try:
            async with Redis(
                host=settings.redis_config.host,
                port=settings.redis_config.port,
                password=settings.redis_config.password,
                db=settings.redis_config.db,
                socket_connect_timeout=settings.redis_config.socket_connect_timeout,
                socket_timeout=settings.redis_config.socket_timeout,
            ) as async_redis:
                await async_redis.ping()
            return CheckResult(ok=True)
        except Exception as e:
            logger.warning("Redis healthcheck failed", exc_info=True)
            return CheckResult(ok=False, details=str(e))

    async def check_all(self) -> Dict:
        db = await self.check_db()
        redis = await self.check_redis()
        rabbitmq = await self.check_rabbitmq()

        checks = {"db": db, "redis": redis, "rabbitmq": rabbitmq}
        healthy = all(c.ok for c in checks.values())
        return {
            "healthy": healthy,
            "details": {
                name: (c.details if not c.ok else "healthy")
                for name, c in checks.items()
            },
        }


health = HealthCheck()
