"""
Tests for main FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns API information."""
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["version"] == "0.1.0"
    assert "/docs" in data["docs"]


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


def test_cors_headers():
    """Test CORS headers are present."""
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:5173"}
    )

    assert "access-control-allow-origin" in response.headers


def test_openapi_docs():
    """Test that OpenAPI docs are available."""
    response = client.get("/docs")

    assert response.status_code == 200
