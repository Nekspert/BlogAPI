import logging
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


LOG_DEFAULT_FORMAT = (
    '[%(asctime)s] #%(levelname)-8s %(filename)s:%(lineno)d - %(name)s - %(message)s'
)
BASE_DIR = Path(__file__).resolve().parent.parent


class SettingsBase(BaseSettings):
    model_config = SettingsConfigDict(
            env_file=BASE_DIR / '.env',
            env_file_encoding='utf-8',
            extra='ignore',
            case_sensitive=False,
    )


class LoggingConfig(BaseModel):
    log_level: Literal['debug', 'info', 'warning', 'error', 'critical'] = 'info'
    log_format: str = LOG_DEFAULT_FORMAT

    @property
    def log_level_value(self) -> int:
        return logging.getLevelNamesMapping()[self.log_level.upper()]


class DatabaseBase(SettingsBase):
    host: str
    port: int
    user: str
    password: str
    db: str

    echo: bool = False
    echo_pool: bool = False
    pool_size: int = 5
    max_overflow: int = 10

    def _build_url(self, driver: str) -> str:
        return (
            f'postgresql+{driver}://'
            f"{quote(self.user, safe='')}:{quote(self.password, safe='')}"
            f"@{self.host}:{self.port}/{quote(self.db, safe='')}"
        )

    @property
    def database_url_psycopg(self) -> str:
        return self._build_url('psycopg')

    @property
    def database_url_asyncpg(self) -> str:
        return self._build_url('asyncpg')


class DatabaseConfig(DatabaseBase):
    model_config = SettingsBase.model_config | SettingsConfigDict(env_prefix='POSTGRES_')


class TestDatabaseConfig(DatabaseBase):
    model_config = SettingsBase.model_config | SettingsConfigDict(env_prefix='POSTGRES_TEST_')


class RedisDB(BaseModel):
    cache: int = 0
    test_cache: int = 1


class RedisConfig(SettingsBase):
    model_config = SettingsBase.model_config | SettingsConfigDict(env_prefix='REDIS_')

    host: str
    port: int
    password: str | None = None
    db: RedisDB = RedisDB()

    @property
    def redis_url(self) -> str:
        if self.password:
            return f"redis://:{quote(self.password, safe='')}@{self.host}:{self.port}/{self.db.cache}"
        return f'redis://{self.host}:{self.port}/{self.db.cache}'

    @property
    def redis_test_url(self) -> str:
        if self.password:
            return f"redis://:{quote(self.password, safe='')}@{self.host}:{self.port}/{self.db.test_cache}"
        return f'redis://{self.host}:{self.port}/{self.db.test_cache}'


class CacheNamespace(BaseModel):
    blog_posts: str = 'blog-posts'


class CacheConfig(BaseModel):
    prefix: str = 'fastapi-cache'
    namespace: CacheNamespace = CacheNamespace()


class RunConfig(SettingsBase):
    model_config = SettingsBase.model_config | SettingsConfigDict(env_prefix='RUN_')

    host: str = '127.0.0.1'
    port: int = 8000


class ApiConfig(SettingsBase):
    model_config = SettingsBase.model_config | SettingsConfigDict(env_prefix='API_')

    name: str = 'Blog API'
    debug: bool = False
    v1_prefix: str = '/api/v1'


class Config(BaseModel):
    run: RunConfig = RunConfig()
    api: ApiConfig = ApiConfig()
    logging: LoggingConfig = LoggingConfig()
    db: DatabaseConfig = DatabaseConfig()
    test_db: TestDatabaseConfig = TestDatabaseConfig()
    redis: RedisConfig = RedisConfig()
    cache: CacheConfig = CacheConfig()


config = Config()
