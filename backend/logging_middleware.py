"""
Structured logging middleware for FastAPI.
Provides JSON-formatted logs for all requests.
"""

import logging
import sys
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Configure JSON logger
logger = logging.getLogger("api")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "api", %(message)s}',
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
handler.setFormatter(formatter)
logger.addHandler(handler)


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured JSON logging.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Request context for logging
        request_context = {
            "req_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        }

        logger.debug(f'"event": "request_received", "context": {request_context}')

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log response
            log_msg = (
                f'"event": "request_completed", '
                f'"req_id": "{request_id}", '
                f'"method": "{request.method}", '
                f'"path": "{request.url.path}", '
                f'"status": {response.status_code}, '
                f'"duration_ms": {duration_ms}'
            )

            if response.status_code >= 500:
                logger.error(log_msg)
            elif response.status_code >= 400:
                logger.warning(log_msg)
            else:
                logger.info(log_msg)

            # Add Request-ID header to response
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f'"event": "request_failed", '
                f'"req_id": "{request_id}", '
                f'"method": "{request.method}", '
                f'"path": "{request.url.path}", '
                f'"error": "{str(e)}", '
                f'"duration_ms": {duration_ms}'
            )
            raise
