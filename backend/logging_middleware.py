"""
Structured logging middleware for FastAPI.

Uses the centralized JSONFormatter from logging_config to produce valid
JSON log lines for every HTTP request.
"""

import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that logs every request/response as structured JSON."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            response = await call_next(request)

            duration_ms = round((time.time() - start_time) * 1000, 2)

            extra = {
                "event": "request_completed",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
            }

            msg = f"{request.method} {request.url.path} {response.status_code} {duration_ms}ms"

            if response.status_code >= 500:
                logger.error(msg, extra=extra)
            elif response.status_code >= 400:
                logger.warning(msg, extra=extra)
            else:
                logger.info(msg, extra=extra)

            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"{request.method} {request.url.path} FAILED {duration_ms}ms",
                extra={
                    "event": "request_failed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )
            raise
