import logging
from typing import Any

from redis.asyncio import Redis

from app.core.config import config


logger = logging.getLogger(__name__)


class RedisManager:
    def __init__(self, url: str):
        logger.debug(f'Инициализация Redis: {url}')

        self._url = url
        self.redis: Redis | None = None

    async def connect(self):
        if not self.redis:
            self.redis = Redis.from_url(
                    self._url,
                    encoding='utf-8',
                    decode_responses=True
            )
        info = await self.redis.info()
        version = info.get('redis_version', 'unknown')

        logger.info(f'Connected to Redis version: {version}')

    async def get_with_ttl(self, key: str) -> tuple[int, Any | None]:
        ttl = await self.redis.ttl(key)
        value = await self.redis.get(key)
        return ttl, value

    async def get(self, key: str) -> Any | None:
        return await self.redis.get(key)

    async def set(self, key: str, value: bytes, expire: int | None = None):
        await self.redis.set(key, value, ex=expire)

    async def clear(self, namespace: str | None = None, key: str | None = None) -> int:
        if namespace:
            pattern = f'{namespace}:*'
            deleted = 0
            batch: list[str] = []

            async for found_key in self.redis.scan_iter(match=pattern, count=100):
                batch.append(found_key)

                if len(batch) >= 500:
                    deleted += await self.redis.delete(*batch)
                    batch.clear()
            if batch:
                deleted += await self.redis.delete(*batch)

            return deleted

        if key:
            return await self.redis.delete(key)

        return 0

    async def close(self) -> None:
        if self.redis is not None:
            await self.redis.aclose()
            self.redis = None
            logger.info('Async Redis connection closed')


redis_manager = RedisManager(url=config.redis.redis_url)
