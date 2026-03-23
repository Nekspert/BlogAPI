import logging
from functools import wraps
from inspect import isawaitable, iscoroutinefunction, Parameter
from typing import Awaitable, Callable, cast, ParamSpec, TypeVar, Union

from fastapi.concurrency import run_in_threadpool
from fastapi.dependencies.utils import get_typed_signature
from fastapi.requests import Request
from fastapi.responses import Response
from starlette.status import HTTP_304_NOT_MODIFIED

from app.core.redis import RedisManager
from app.services.cache_key_builder import CacheKeyBuilder
from app.services.cache_policy import CachePolicy
from app.services.coder import JsonCoder
from app.services.signarute import SignatureHelper


logger = logging.getLogger(__name__)
P = ParamSpec('P')
R = TypeVar('R')


class Cache:
    _backend: RedisManager | None = None
    _prefix: str | None = None
    _expire: int | None = None
    _init: bool | None = False
    _cache_status_header: str | None = None
    _enable: bool | None = True

    @classmethod
    def init(cls,
             backend: RedisManager,
             prefix: str = '',
             expire: int | int = None,
             cache_status_header: str = 'X-Cache',
             enable: bool = True,
             ) -> None:
        if cls._init:
            return

        cls._init = True
        cls._backend = backend
        cls._prefix = prefix
        cls._expire = expire
        cls._cache_status_header = cache_status_header
        cls._enable = enable

    @classmethod
    def reset(cls) -> None:
        cls._init = False
        cls._backend = None
        cls._prefix = None
        cls._expire = None
        cls._cache_status_header = None
        cls._enable = True

    @classmethod
    def get_backend(cls) -> RedisManager:
        return cls._backend

    @classmethod
    def get_prefix(cls) -> str:
        return cls._prefix

    @classmethod
    def get_expire(cls) -> int | None:
        return cls._expire

    @classmethod
    def get_cache_status_header(cls) -> str:
        return cls._cache_status_header

    @classmethod
    def get_enable(cls) -> bool:
        return cls._enable

    @classmethod
    async def clear(cls,
                    namespace: str | None = None,
                    key: str | None = None
                    ) -> int:
        namespace = cls._prefix + (':' + namespace if namespace else "")
        return await cls._backend.clear(namespace, key)

    @classmethod
    def cache(cls,
              expire: int | None = None,
              coder: JsonCoder | None = None,
              key_builder: CacheKeyBuilder | None = None,
              namespace: str = "",
              injected_dependency_namespace: str = '__fastapi_cache',
              ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[Union[R, Response]]]]:

        injected_request = Parameter(
                name=f'{injected_dependency_namespace}_request',
                annotation=Request,
                kind=Parameter.KEYWORD_ONLY,
        )
        injected_response = Parameter(
                name=f'{injected_dependency_namespace}_response',
                annotation=Response,
                kind=Parameter.KEYWORD_ONLY,
        )

        def wrapper(
                func: Callable[P, Awaitable[R]]
        ) -> Callable[P, Awaitable[Union[R, Response]]]:

            wrapped_signature = get_typed_signature(func)
            to_inject: list[Parameter] = []
            request_param = SignatureHelper.locate_param(wrapped_signature, injected_request, to_inject)
            response_param = SignatureHelper.locate_param(wrapped_signature, injected_response, to_inject)

            @wraps(func)
            async def inner(*args: P.args, **kwargs: P.kwargs) -> Union[R, Response]:
                nonlocal coder
                nonlocal expire
                nonlocal key_builder

                async def ensure_async_func(*args: P.args, **kwargs: P.kwargs) -> R:
                    kwargs.pop(injected_request.name, None)
                    kwargs.pop(injected_response.name, None)

                    if iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return await run_in_threadpool(func, *args, **kwargs)

                copy_kwargs = kwargs.copy()
                request: Request | None = copy_kwargs.pop(request_param.name, None)
                response: Response | None = copy_kwargs.pop(response_param.name, None)

                if CachePolicy.is_uncacheable(request, cls.get_enable()):
                    return await ensure_async_func(*args, **kwargs)

                prefix = cls.get_prefix()
                coder = coder or JsonCoder
                expire = expire or cls.get_expire()
                key_builder = key_builder or CacheKeyBuilder
                backend = cls.get_backend()
                cache_status_header = cls.get_cache_status_header()

                cache_key = key_builder.build(
                        func,
                        f'{prefix}:{namespace}',
                        request=request,
                        response=response,
                        args=args,
                        kwargs=copy_kwargs,
                )
                if isawaitable(cache_key):
                    cache_key = await cache_key
                assert isinstance(cache_key, str)

                try:
                    ttl, cached = await backend.get_with_ttl(cache_key)
                except Exception:
                    logger.warning(
                            f"Error retrieving cache key '{cache_key}' from backend:",
                            exc_info=True,
                    )
                    ttl, cached = 0, None

                if cached is None or (
                        request is not None and request.headers.get('Cache-Control') == 'no-cache'):
                    result = await ensure_async_func(*args, **kwargs)
                    to_cache = coder.encode(result)

                    try:
                        await backend.set(cache_key, to_cache, expire)
                    except Exception:
                        logger.warning(
                                f"Error setting cache key '{cache_key}' in backend:",
                                exc_info=True,
                        )

                    if response:
                        response.headers.update(
                                {
                                    'Cache-Control': f'max-age={expire}',
                                    'ETag': f'W/{hash(to_cache)}',
                                    cache_status_header: 'MISS',
                                }
                        )

                else:
                    if response:
                        etag = f'W/{hash(cached)}'
                        response.headers.update(
                                {
                                    'Cache-Control': f'max-age={ttl}',
                                    'ETag': etag,
                                    cache_status_header: 'HIT',
                                }
                        )

                        if_none_match = request and request.headers.get('if-none-match')
                        if if_none_match == etag:
                            response.status_code = HTTP_304_NOT_MODIFIED
                            return response

                    result = cast(R, coder.decode(cached))

                return result

            inner.__signature__ = SignatureHelper.augment(wrapped_signature, *to_inject)

            return inner

        return wrapper
