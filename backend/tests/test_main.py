"""
Tests for main FastAPI application.

Covers: lifespan, health check, root endpoint, CORS, upload size limiting,
rate limiter wiring, OpenAPI docs, and redoc.
"""

from fastapi.testclient import TestClient

from backend.config import get_settings
from backend.main import app

client = TestClient(app)
_VERSION = get_settings().app_version


# ==================== Root & Health Endpoints ====================


def test_root_endpoint():
    """Test root endpoint returns API information."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["version"] == _VERSION
    assert "/docs" in data["docs"]
    assert "/health" in data["health"]


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == _VERSION
    assert "timestamp" in data


def test_health_check_response_model():
    """Test health endpoint returns all HealthResponse fields."""
    response = client.get("/health")
    data = response.json()
    assert set(data.keys()) == {"status", "version", "timestamp"}


# ==================== CORS ====================


def test_cors_headers_allowed_origin():
    """Test CORS headers are present for allowed origin."""
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert "access-control-allow-origin" in response.headers


def test_cors_allows_api_key_header():
    """Test CORS allows the X-API-Key custom header."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Headers": "X-API-Key",
            "Access-Control-Request-Method": "GET",
        },
    )
    allow_headers = response.headers.get("access-control-allow-headers", "")
    assert "x-api-key" in allow_headers.lower()


# ==================== OpenAPI / Docs ====================


def test_openapi_docs():
    """Test that Swagger UI docs are available."""
    response = client.get("/docs")
    assert response.status_code == 200


def test_redoc_docs():
    """Test that ReDoc is available."""
    response = client.get("/redoc")
    assert response.status_code == 200


def test_openapi_schema():
    """Test that the OpenAPI JSON schema endpoint works."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    assert schema["info"]["title"] == "Log Analyzer Toolkit API"


# ==================== Upload Size Limiting ====================


def test_upload_size_limit_rejects_oversized():
    """POST with content-length exceeding limit returns 413."""
    huge_size = 200 * 1024 * 1024  # 200 MB
    response = client.post(
        "/api/v1/analyze",
        headers={"content-length": str(huge_size)},
        content=b"x",
    )
    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()


def test_upload_size_limit_allows_normal():
    """POST with reasonable content-length is not blocked by size middleware."""
    # This will hit the actual route (and may fail for other reasons like missing file),
    # but should NOT be a 413.
    response = client.post(
        "/api/v1/analyze",
        headers={"content-length": "1024"},
        content=b"x" * 1024,
    )
    assert response.status_code != 413


def test_get_requests_bypass_upload_check():
    """GET requests should never be blocked by the upload size middleware."""
    response = client.get("/health")
    assert response.status_code == 200


# ==================== Rate Limiter ====================


def test_rate_limiter_is_wired():
    """The app should have a limiter attached to state."""
    assert hasattr(app.state, "limiter")


# ==================== Request ID Header ====================


def test_request_id_header_present():
    """Responses should include X-Request-ID from the logging middleware."""
    response = client.get("/health")
    assert "x-request-id" in response.headers
