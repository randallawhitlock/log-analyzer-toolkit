"""
FastAPI application for Log Analyzer Toolkit.

Main entry point for the REST API backend.
"""

from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.database import init_db
from backend.api.schemas import HealthResponse

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


# Startup event to initialize database
@app.on_event("startup")
async def startup_event():
    """Initialize database on application startup."""
    init_db()
    print("✓ Database initialized")


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


# Import and include routers (will be added in next step)
# from backend.api import routes
# app.include_router(routes.router)
