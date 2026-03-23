from fastapi.requests import Request


class CachePolicy:
    @staticmethod
    def is_uncacheable(request: Request | None, is_enabled: bool) -> bool:
        if not is_enabled:
            return True
        if request is None:
            return False
        if request.method != 'GET':
            return True
        return request.headers.get('Cache-Control') == 'no-store'
