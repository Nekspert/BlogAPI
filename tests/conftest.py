from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.main import main_app
from app.core.config import config
from app.core.database import AsyncDatabaseManager, db_manager
from app.core.redis import RedisManager
from app.models.base import Base
from app.services.cache import Cache


test_db_manager = AsyncDatabaseManager(
        async_url=config.test_db.database_url_asyncpg,
        echo=config.test_db.echo,
        echo_pool=config.test_db.echo_pool,
        pool_size=config.test_db.pool_size,
        max_overflow=config.test_db.max_overflow,
)

redis_manager = RedisManager(url=config.redis.redis_test_url)


@pytest.fixture(scope="session", autouse=True)
async def setup_test_environment():
    main_app.dependency_overrides[db_manager.session_getter] = test_db_manager.session_getter

    await redis_manager.connect()
    Cache.init(
            backend=redis_manager,
            prefix=config.cache.prefix
    )

    await test_db_manager.connect()

    yield

    await test_db_manager.close()
    await redis_manager.close()


@pytest.fixture(autouse=True)
async def clear_db_and_cache():
    async with test_db_manager.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    await Cache.clear(namespace=config.cache.namespace.blog_posts)
    yield


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in test_db_manager.session_getter():
        yield session


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
            transport=ASGITransport(app=main_app),
            base_url="http://testserver"
    ) as client:
        yield client
