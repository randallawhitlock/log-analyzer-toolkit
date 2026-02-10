"""
FastAPI application for Log Analyzer Toolkit.

Main entry point for the REST API backend.
"""

import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from backend.db.database import init_db
from backend.api.schemas import HealthResponse
from backend.logging_middleware import StructuredLoggingMiddleware
from backend.constants import MAX_UPLOAD_SIZE_BYTES, MAX_UPLOAD_SIZE_MB


logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Log Analyzer Toolkit API",
    description="REST API for analyzing and troubleshooting log files",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
        "http://localhost:8080",  # Another common port
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


class LimitUploadSize(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_upload_size: int) -> None:
        super().__init__(app)
        self.max_upload_size = max_upload_size

    async def dispatch(self, request: Request, call_next):
        if request.method == 'POST':
            if 'content-length' in request.headers:
                content_length = int(request.headers['content-length'])
                if content_length > self.max_upload_size:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": f"File too large. Maximum size is {MAX_UPLOAD_SIZE_MB}MB"}
                    )
        return await call_next(request)

# Enforce upload size limit
app.add_middleware(LimitUploadSize, max_upload_size=MAX_UPLOAD_SIZE_BYTES)

# Add structured logging
app.add_middleware(StructuredLoggingMiddleware)


# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully")


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns:
        HealthResponse: Current health status and version
    """
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.utcnow()
    )


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
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health"
    }


# Import and include routers
from backend.api import routes
app.include_router(routes.router)
