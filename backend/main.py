"""
FastAPI application for Log Analyzer Toolkit.

Main entry point for the REST API backend.
"""

# Load .env BEFORE any other imports to ensure env vars are available
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env_path, override=True)

import logging  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from datetime import datetime, timezone  # noqa: E402

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from slowapi import _rate_limit_exceeded_handler  # noqa: E402
from slowapi.errors import RateLimitExceeded  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.types import ASGIApp  # noqa: E402

from backend.api.schemas import HealthResponse  # noqa: E402
from backend.config import settings  # noqa: E402
from backend.constants import MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB  # noqa: E402
from backend.db.database import init_db  # noqa: E402
from backend.logging_config import setup_logging  # noqa: E402
from backend.logging_middleware import StructuredLoggingMiddleware  # noqa: E402
from backend.rate_limit import limiter  # noqa: E402

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on application startup."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")
    yield


# Create FastAPI app
app = FastAPI(
    title="Log Analyzer Toolkit API",
    description="REST API for analyzing and troubleshooting log files",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)


class LimitUploadSize(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_upload_size: int) -> None:
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and "content-length" in request.headers:
            content_length = int(request.headers["content-length"])
            if content_length > self.max_upload_size:
                return JSONResponse(
                    status_code=413, content={"detail": f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB}MB"}
                )
        return await call_next(request)


# Enforce upload size limit
app.add_middleware(LimitUploadSize, max_upload_size=MAX_UPLOAD_SIZE_BYTES)

# Add structured logging
app.add_middleware(StructuredLoggingMiddleware)


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        HealthResponse: Current health status and version
    """
    return HealthResponse(status="healthy", version=settings.app_version, timestamp=datetime.now(timezone.utc))


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.

    Returns:
        dict: API information
    """
    return {
        "message": "Log Analyzer Toolkit API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


# Import and include routers
from backend.api import routes  # noqa: E402

app.include_router(routes.router)
