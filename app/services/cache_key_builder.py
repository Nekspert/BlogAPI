import hashlib
from typing import Any, Callable

from fastapi.requests import Request
from fastapi.responses import Response


class CacheKeyBuilder:
    @staticmethod
    def build(
            func: Callable[..., Any],
            namespace: str = '',
            *,
            request: Request | None = None,
            response: Response | None = None,
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
    ) -> str:
        safe_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in {"session", "request", "response"}
        }
        cache_key = hashlib.md5(
                f'{func.__module__}:{func.__name__}:{args}:{safe_kwargs}'.encode()
        ).hexdigest()
        return f'{namespace}:{cache_key}'
