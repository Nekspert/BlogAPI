import logging
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, Engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import config
from app.models.base import Base


logger = logging.getLogger(__name__)


class AsyncDatabaseManager:
    def __init__(
            self,
            async_url: str,
            echo: bool = False,
            echo_pool: bool = False,
            pool_size: int = 5,
            max_overflow: int = 10,
    ):
        logger.debug(f'Initialize PostgreSQL async manager')

        self.async_url = async_url
        self.echo = echo
        self.echo_pool = echo_pool
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.async_engine: AsyncEngine | None = None
        self.async_session_maker: async_sessionmaker[AsyncSession] | None = None

    async def connect(self):
        if not self.async_engine:
            self.async_engine: AsyncEngine = create_async_engine(
                    url=self.async_url,
                    echo=self.echo,
                    echo_pool=self.echo_pool,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_pre_ping=True,
            )
        if not self.async_session_maker:
            self.async_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
                    bind=self.async_engine,
                    autoflush=False,
                    expire_on_commit=False,
            )

        await self.log_db_version()

    async def log_db_version(self):
        try:
            async with self.async_engine.connect() as conn:
                result = await conn.execute(text('SELECT version();'))
                logger.info(f'Connected to Async PostgreSQL version: {result.scalar()}')
        except Exception as e:
            logger.exception(f'Failed to connect to Async PostgreSQL: {e}')
            raise

    async def async_create_all(self, base: Base):
        async with self.async_engine.begin() as conn:
            await conn.run_sync(base.metadata.create_all)

    async def session_getter(self) -> AsyncGenerator[AsyncSession, None]:
        if self.async_session_maker:
            async with self.async_session_maker() as session:
                yield session

    async def close(self) -> None:
        await self.async_engine.dispose()
        logger.info('Async PostgreSQL connection pool closed')


class SyncDatabaseManager:
    def __init__(
            self,
            async_url: str,
            echo: bool = False,
            echo_pool: bool = False,
            pool_size: int = 5,
            max_overflow: int = 10,
    ):
        logger.debug(f'Initialize PostgreSQL async manager')

        self.async_url = async_url
        self.echo = echo
        self.echo_pool = echo_pool
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.sync_engine: Engine | None = None
        self.sync_session_maker: sessionmaker[Session] | None = None

    async def connect(self):
        if not self.sync_engine:
            self.sync_engine: Engine = create_engine(
                    url=self.async_url,
                    echo=self.echo,
                    echo_pool=self.echo_pool,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_pre_ping=True,
            )
        if not self.sync_session_maker:
            self.sync_session_maker: sessionmaker[Session] = sessionmaker(
                    bind=self.sync_engine,
                    autoflush=False,
                    auto_commit=False,
                    expire_on_commit=False,
            )

        self.log_db_version()

    def sync_create_all(self, base: Base):
        with self.sync_engine.begin() as conn:
            conn.run_sync(base.metadata.create_all)

    def session_getter(self) -> Generator[Session, None, None]:
        if self.sync_session_maker:
            with self.sync_session_maker() as session:
                yield session

    def log_db_version(self) -> None:
        try:
            with self.sync_engine.connect() as conn:
                result = conn.execute(text('SELECT version();'))
                logger.info(f'Connected to Sync PostgreSQL version: {result.scalar()}')
        except Exception as e:
            logger.exception(f'Failed to connect to Sync PostgreSQL: {e}')
            raise

    def close(self) -> None:
        self.sync_engine.dispose()
        logger.info('Sync PostgreSQL connection pool closed')


db_manager = AsyncDatabaseManager(
        async_url=config.db.database_url_asyncpg,
        echo=config.db.echo,
        echo_pool=config.db.echo_pool,
        pool_size=config.db.pool_size,
        max_overflow=config.db.max_overflow,
)
