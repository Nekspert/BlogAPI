import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import db_manager
from .v1.posts import router as post_router
from ..core.config import config
from ..core.redis import redis_manager
from ..models.base import Base
from ..services.cache import Cache
from ..services.error_handlers import register_errors_handlers


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info('Starting application lifespan')

    await redis_manager.connect()
    Cache.init(
            backend=redis_manager,
            prefix=config.cache.prefix
    )
    await db_manager.connect()
    await db_manager.async_create_all(Base)
    yield
    await db_manager.close()
    await redis_manager.close()

    logger.info('Application lifespan stopped')


def create_app() -> FastAPI:
    logger.info('Creating FastAPI application')
    app = FastAPI(
            title=config.api.name,
            lifespan=lifespan,
    )

    logger.info('Registering error handlers')
    register_errors_handlers(app)

    logger.info('Registering routers')
    app.include_router(post_router, prefix=config.api.v1_prefix)

    return app


main_app = create_app()
