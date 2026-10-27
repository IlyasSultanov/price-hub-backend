from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ...core import settings


class DBHelper:
    def __init__(
        self, url: str, echo: bool = False, max_overflow: int = 50, pool_size: int = 20
    ) -> None:
        self.connect = {
            "server_settings": {"application_name": "price-hub"},
            "command_timeout": 60,
            "timeout": 60,
        }

        self.async_engine: AsyncEngine = create_async_engine(
            url=url,
            echo=echo,
            max_overflow=max_overflow,
            pool_size=pool_size,
            connect_args=self.connect,
        )

        self.async_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            autocommit=False,
            expire_on_commit=False,
        )

    async def dispose(self) -> None:
        await self.async_engine.dispose()

    async def get_db(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.async_factory() as session:
            yield session


db = DBHelper(
    settings.pg_config.url,
)
