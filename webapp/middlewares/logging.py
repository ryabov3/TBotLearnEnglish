# webapp/middlewares/logging.py
"""HTTP middleware для логирования запросов и времени ответа API."""

import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"[API] {request.method} {request.url.path} -> {response.status_code} ({elapsed_ms:.1f} ms)"
        )
        return response
