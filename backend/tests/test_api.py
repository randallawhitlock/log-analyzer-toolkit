"""
Tests for API endpoints.
"""

import atexit
import tempfile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base, get_db
from backend.main import app

# Create test database (file-based for thread safety with FastAPI)
TEST_DB_FILE = tempfile.NamedTemporaryFile(delete=False, suffix=".db")  # noqa: SIM115
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_FILE.name}"

# Clean up test database on exit
def cleanup_test_db():
    import os
    if os.path.exists(TEST_DB_FILE.name):
        os.remove(TEST_DB_FILE.name)

atexit.register(cleanup_test_db)


@pytest.fixture
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_db(test_engine):
    """Create test database session."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(test_engine):
    """Create test client with database override."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    
    # Patch SessionLocal for background tasks that bypass dependency_overrides
    import backend.db.database as db_module
    original_session_local = db_module.SessionLocal
    db_module.SessionLocal = TestSessionLocal
    
    client = TestClient(app)
    yield client
    
    db_module.SessionLocal = original_session_local
    app.dependency_overrides.clear()


@pytest.fixture
def sample_log_file():
    """Create sample log file content."""
    return BytesIO(b"""192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326
192.168.1.1 - - [10/Oct/2023:13:55:37 +0000] "GET /style.css HTTP/1.1" 200 1234
192.168.1.2 - - [10/Oct/2023:13:55:38 +0000] "GET /about.html HTTP/1.1" 404 512
192.168.1.1 - - [10/Oct/2023:13:55:39 +0000] "POST /api/data HTTP/1.1" 500 128
192.168.1.3 - - [10/Oct/2023:13:55:40 +0000] "GET /index.html HTTP/1.1" 200 2326
""")


# ==================== Health and Root Endpoints ====================

def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "version" in response.json()


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


# ==================== Analysis Endpoints ====================

def test_analyze_log_file(client, sample_log_file):
    """Test uploading and analyzing a log file."""
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.log", sample_log_file, "text/plain")}
    )

    assert response.status_code == 202
    data = response.json()

    # Check response structure
    assert "id" in data
    assert data["filename"] == "test.log"
    assert data["total_lines"] == 0
    assert data["detected_format"] == "pending"
    assert "created_at" in data

    # Wait for processing to complete
    import time
    analysis_id = data["id"]
    for _ in range(10):
        resp = client.get(f"/api/v1/analysis/{analysis_id}")
        data = resp.json()
        if data["detected_format"] != "pending":
            break
        time.sleep(0.1)

    assert data["total_lines"] == 5
    assert data["parsed_lines"] >= 4
    assert "level_counts" in data

    # Cleanup
    analysis_id = data["id"]
    cleanup_response = client.delete(f"/api/v1/analysis/{analysis_id}")
    assert cleanup_response.status_code == 200


def test_analyze_with_parameters(client, sample_log_file):
    """Test analyze endpoint with custom parameters."""
    response = client.post(
        "/api/v1/analyze?max_errors=50",
        files={"file": ("test.log", sample_log_file, "text/plain")}
    )

    assert response.status_code == 202
    data = response.json()
    assert data["total_lines"] == 0

    # Cleanup
    cleanup_response = client.delete(f"/api/v1/analysis/{data['id']}")
    assert cleanup_response.status_code == 200


def test_list_analyses_empty(client):
    """Test listing analyses when none exist."""
    response = client.get("/api/v1/analyses")

    assert response.status_code == 200
    data = response.json()
    assert data["analyses"] == []
    assert data["total"] == 0
    assert data["page"] == 1


def test_list_analyses_with_results(client, sample_log_file):
    """Test listing analyses with pagination."""
    # Create a few analyses
    analysis_ids = []
    for i in range(3):
        sample_log_file.seek(0)  # Reset file pointer
        response = client.post(
            "/api/v1/analyze",
            files={"file": (f"test{i}.log", sample_log_file, "text/plain")}
        )
        assert response.status_code == 202
        analysis_ids.append(response.json()["id"])

    # List analyses
    response = client.get("/api/v1/analyses")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["analyses"]) == 3

    # Test pagination
    response = client.get("/api/v1/analyses?skip=1&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["analyses"]) == 1
    assert data["total"] == 3

    # Cleanup
    for aid in analysis_ids:
        client.delete(f"/api/v1/analysis/{aid}")


def test_get_analysis(client, sample_log_file):
    """Test retrieving a specific analysis."""
    # Create analysis
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.log", sample_log_file, "text/plain")}
    )
    analysis_id = response.json()["id"]

    # Get analysis
    response = client.get(f"/api/v1/analysis/{analysis_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == analysis_id
    assert data["filename"] == "test.log"

    # Cleanup
    client.delete(f"/api/v1/analysis/{analysis_id}")


def test_get_analysis_not_found(client):
    """Test getting non-existent analysis."""
    response = client.get("/api/v1/analysis/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_delete_analysis(client, sample_log_file):
    """Test deleting an analysis."""
    # Create analysis
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.log", sample_log_file, "text/plain")}
    )
    analysis_id = response.json()["id"]

    # Delete it
    response = client.delete(f"/api/v1/analysis/{analysis_id}")
    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]

    # Verify it's gone
    response = client.get(f"/api/v1/analysis/{analysis_id}")
    assert response.status_code == 404


def test_delete_analysis_not_found(client):
    """Test deleting non-existent analysis."""
    response = client.delete("/api/v1/analysis/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ==================== Triage Endpoints ====================

@pytest.mark.skip(reason="Requires AI API key")
def test_run_triage(client, sample_log_file):
    """Test running AI triage on an analysis."""
    # Create analysis
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.log", sample_log_file, "text/plain")}
    )
    analysis_id = response.json()["id"]

    # Run triage
    response = client.post(
        "/api/v1/triage",
        json={"analysis_id": analysis_id, "provider": "anthropic"}
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["analysis_id"] == analysis_id
    assert "summary" in data
    assert "overall_severity" in data
    assert "provider_used" in data

    # Cleanup
    client.delete(f"/api/v1/analysis/{analysis_id}")


def test_run_triage_analysis_not_found(client, monkeypatch):
    """Test triage with non-existent analysis."""
    from unittest.mock import Mock

    from backend.services.triage_service import TriageService

    # Mock the TriageService to avoid AI provider requirement
    mock_service = Mock()
    mock_service.run_triage_on_analysis.side_effect = ValueError("Analysis 00000000-0000-0000-0000-000000000000 not found")

    def mock_init(self, provider_name=None):
        return None

    monkeypatch.setattr(TriageService, "__init__", mock_init)
    monkeypatch.setattr(TriageService, "run_triage_on_analysis", lambda self, *args, **kwargs: mock_service.run_triage_on_analysis(*args, **kwargs))

    response = client.post(
        "/api/v1/triage",
        json={"analysis_id": "00000000-0000-0000-0000-000000000000"}
    )
    assert response.status_code == 404


@pytest.mark.skip(reason="Requires AI API key")
def test_get_triage(client, sample_log_file):
    """Test retrieving a triage result."""
    # Create analysis and triage
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.log", sample_log_file, "text/plain")}
    )
    analysis_id = response.json()["id"]

    response = client.post(
        "/api/v1/triage",
        json={"analysis_id": analysis_id}
    )
    triage_id = response.json()["id"]

    # Get triage
    response = client.get(f"/api/v1/triage/{triage_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == triage_id

    # Cleanup
    client.delete(f"/api/v1/analysis/{analysis_id}")


def test_get_triage_not_found(client):
    """Test getting non-existent triage."""
    response = client.get("/api/v1/triage/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_get_triages_for_analysis_not_found(client):
    """Test getting triages for non-existent analysis."""
    response = client.get("/api/v1/analysis/00000000-0000-0000-0000-000000000000/triages")
    assert response.status_code == 404


def test_get_triages_for_analysis_empty(client, sample_log_file):
    """Test getting triages when none exist."""
    # Create analysis
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.log", sample_log_file, "text/plain")}
    )
    analysis_id = response.json()["id"]

    # Get triages (should be empty)
    response = client.get(f"/api/v1/analysis/{analysis_id}/triages")
    assert response.status_code == 200
    assert response.json() == []

    # Cleanup
    client.delete(f"/api/v1/analysis/{analysis_id}")


# ==================== Utility Endpoints ====================

def test_list_formats(client):
    """Test listing supported log formats."""
    response = client.get("/api/v1/formats")

    assert response.status_code == 200
    data = response.json()
    assert "formats" in data
    assert "total" in data
    assert len(data["formats"]) > 0

    # Check format structure
    format_item = data["formats"][0]
    assert "name" in format_item
    assert "description" in format_item


# ==================== Error Handling Tests ====================

def test_analyze_invalid_file_type(client):
    """Test uploading invalid file."""
    invalid_file = BytesIO(b"\x00\x01\x02\x03")  # Binary garbage

    response = client.post(
        "/api/v1/analyze",
        files={"file": ("binary.dat", invalid_file, "application/octet-stream")}
    )

    # Should still process (might detect as 'universal' format or fail gracefully)
    assert response.status_code in [202, 400, 500]

    # Cleanup if created
    if response.status_code == 202:
        client.delete(f"/api/v1/analysis/{response.json()['id']}")


def test_analyze_empty_file(client):
    """Test uploading empty file."""
    empty_file = BytesIO(b"")

    response = client.post(
        "/api/v1/analyze",
        files={"file": ("empty.log", empty_file, "text/plain")}
    )

    # Should handle empty file
    assert response.status_code == 202
    data = response.json()
    assert data["total_lines"] == 0

    # Cleanup
    client.delete(f"/api/v1/analysis/{data['id']}")


def test_invalid_pagination_parameters(client):
    """Test invalid pagination parameters."""
    # Negative skip
    response = client.get("/api/v1/analyses?skip=-1")
    assert response.status_code == 422  # Validation error

    # Limit too high
    response = client.get("/api/v1/analyses?limit=1000")
    assert response.status_code == 422


def test_invalid_max_errors(client, sample_log_file):
    """Test invalid max_errors parameter."""
    # Too high
    response = client.post(
        "/api/v1/analyze?max_errors=10000",
        files={"file": ("test.log", sample_log_file, "text/plain")}
    )
    assert response.status_code == 422

    # Too low
    response = client.post(
        "/api/v1/analyze?max_errors=0",
        files={"file": ("test.log", sample_log_file, "text/plain")}
    )
    assert response.status_code == 422
