"""
Tests for database models and CRUD operations.
"""


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db import crud
from backend.db.database import Base

# Create test database (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def test_db():
    """
    Create test database and session for each test.

    Yields:
        Session: Test database session
    """
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_create_analysis(test_db):
    """Test creating an analysis record."""
    analysis_data = {
        "filename": "test.log",
        "detected_format": "apache_access",
        "total_lines": 1000,
        "parsed_lines": 950,
        "failed_lines": 50,
        "parse_success_rate": 95.0,
        "error_rate": 2.5,
        "level_counts": {"ERROR": 25, "WARNING": 10, "INFO": 915},
        "top_errors": [["Connection timeout", 15], ["Database error", 10]],
        "top_sources": [["192.168.1.1", 500], ["192.168.1.2", 450]],
        "status_codes": {200: 900, 404: 50, 500: 50},
        "file_path": "/tmp/test.log"
    }

    analysis = crud.create_analysis(test_db, analysis_data)

    assert analysis.id is not None
    assert analysis.filename == "test.log"
    assert analysis.detected_format == "apache_access"
    assert analysis.total_lines == 1000
    assert analysis.parsed_lines == 950
    assert analysis.parse_success_rate == 95.0
    assert analysis.error_rate == 2.5
    assert analysis.level_counts == {"ERROR": 25, "WARNING": 10, "INFO": 915}
    assert len(analysis.top_errors) == 2
    assert analysis.created_at is not None


def test_get_analysis(test_db):
    """Test retrieving an analysis by ID."""
    # Create analysis
    analysis_data = {
        "filename": "test.log",
        "detected_format": "nginx_access",
        "total_lines": 500,
        "parsed_lines": 500,
        "failed_lines": 0,
        "parse_success_rate": 100.0,
        "error_rate": 0.0,
        "level_counts": {"INFO": 500},
        "top_errors": [],
        "top_sources": [],
        "status_codes": {},
        "file_path": "/tmp/test.log"
    }
    created = crud.create_analysis(test_db, analysis_data)

    # Retrieve it
    retrieved = crud.get_analysis(test_db, created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.filename == "test.log"
    assert retrieved.detected_format == "nginx_access"


def test_get_analysis_not_found(test_db):
    """Test retrieving a non-existent analysis."""
    result = crud.get_analysis(test_db, "non-existent-id")
    assert result is None


def test_get_analyses_pagination(test_db):
    """Test listing analyses with pagination."""
    # Create multiple analyses
    for i in range(10):
        analysis_data = {
            "filename": f"test{i}.log",
            "detected_format": "json",
            "total_lines": 100,
            "parsed_lines": 100,
            "failed_lines": 0,
            "parse_success_rate": 100.0,
            "error_rate": 0.0,
            "level_counts": {},
            "top_errors": [],
            "top_sources": [],
            "status_codes": {},
            "file_path": f"/tmp/test{i}.log"
        }
        crud.create_analysis(test_db, analysis_data)

    # Test pagination
    page1 = crud.get_analyses(test_db, skip=0, limit=5)
    page2 = crud.get_analyses(test_db, skip=5, limit=5)

    assert len(page1) == 5
    assert len(page2) == 5
    assert page1[0].id != page2[0].id  # Different records


def test_get_analyses_with_format_filter(test_db):
    """Test filtering analyses by format."""
    # Create analyses with different formats
    for format_name in ["apache_access", "nginx_access", "json"]:
        for i in range(3):
            analysis_data = {
                "filename": f"{format_name}_{i}.log",
                "detected_format": format_name,
                "total_lines": 100,
                "parsed_lines": 100,
                "failed_lines": 0,
                "parse_success_rate": 100.0,
                "error_rate": 0.0,
                "level_counts": {},
                "top_errors": [],
                "top_sources": [],
                "status_codes": {},
                "file_path": f"/tmp/{format_name}_{i}.log"
            }
            crud.create_analysis(test_db, analysis_data)

    # Filter by format
    json_analyses = crud.get_analyses(test_db, format_filter="json")

    assert len(json_analyses) == 3
    assert all(a.detected_format == "json" for a in json_analyses)


def test_get_analyses_count(test_db):
    """Test counting analyses."""
    # Create 5 analyses
    for i in range(5):
        analysis_data = {
            "filename": f"test{i}.log",
            "detected_format": "apache_access",
            "total_lines": 100,
            "parsed_lines": 100,
            "failed_lines": 0,
            "parse_success_rate": 100.0,
            "error_rate": 0.0,
            "level_counts": {},
            "top_errors": [],
            "top_sources": [],
            "status_codes": {},
            "file_path": f"/tmp/test{i}.log"
        }
        crud.create_analysis(test_db, analysis_data)

    count = crud.get_analyses_count(test_db)
    assert count == 5


def test_delete_analysis(test_db):
    """Test deleting an analysis."""
    # Create analysis
    analysis_data = {
        "filename": "test.log",
        "detected_format": "json",
        "total_lines": 100,
        "parsed_lines": 100,
        "failed_lines": 0,
        "parse_success_rate": 100.0,
        "error_rate": 0.0,
        "level_counts": {},
        "top_errors": [],
        "top_sources": [],
        "status_codes": {},
        "file_path": "/tmp/test.log"
    }
    analysis = crud.create_analysis(test_db, analysis_data)

    # Delete it
    result = crud.delete_analysis(test_db, analysis.id)
    assert result is True

    # Verify it's gone
    retrieved = crud.get_analysis(test_db, analysis.id)
    assert retrieved is None


def test_delete_analysis_not_found(test_db):
    """Test deleting a non-existent analysis."""
    result = crud.delete_analysis(test_db, "non-existent-id")
    assert result is False


def test_create_triage(test_db):
    """Test creating a triage record."""
    # First create an analysis
    analysis_data = {
        "filename": "test.log",
        "detected_format": "apache_access",
        "total_lines": 1000,
        "parsed_lines": 1000,
        "failed_lines": 0,
        "parse_success_rate": 100.0,
        "error_rate": 5.0,
        "level_counts": {"ERROR": 50, "INFO": 950},
        "top_errors": [],
        "top_sources": [],
        "status_codes": {},
        "file_path": "/tmp/test.log"
    }
    analysis = crud.create_analysis(test_db, analysis_data)

    # Create triage
    triage_data = {
        "analysis_id": analysis.id,
        "summary": "System experiencing database connection issues",
        "overall_severity": "HIGH",
        "confidence": 0.85,
        "issues": [
            {
                "title": "Database Connection Pool Exhaustion",
                "severity": "HIGH",
                "confidence": 0.9,
                "description": "Multiple connection timeout errors",
                "affected_components": ["database", "connection_pool"],
                "recommendation": "Increase pool size"
            }
        ],
        "provider_used": "anthropic",
        "analysis_time_ms": 1200.5
    }

    triage = crud.create_triage(test_db, triage_data)

    assert triage.id is not None
    assert triage.analysis_id == analysis.id
    assert triage.summary == "System experiencing database connection issues"
    assert triage.overall_severity == "HIGH"
    assert triage.confidence == 0.85
    assert len(triage.issues) == 1
    assert triage.provider_used == "anthropic"
    assert triage.analysis_time_ms == 1200.5


def test_get_triage(test_db):
    """Test retrieving a triage by ID."""
    # Create analysis and triage
    analysis_data = {
        "filename": "test.log",
        "detected_format": "json",
        "total_lines": 100,
        "parsed_lines": 100,
        "failed_lines": 0,
        "parse_success_rate": 100.0,
        "error_rate": 0.0,
        "level_counts": {},
        "top_errors": [],
        "top_sources": [],
        "status_codes": {},
        "file_path": "/tmp/test.log"
    }
    analysis = crud.create_analysis(test_db, analysis_data)

    triage_data = {
        "analysis_id": analysis.id,
        "summary": "System healthy",
        "overall_severity": "HEALTHY",
        "confidence": 0.95,
        "issues": [],
        "provider_used": "gemini",
        "analysis_time_ms": 800.0
    }
    created = crud.create_triage(test_db, triage_data)

    # Retrieve it
    retrieved = crud.get_triage(test_db, created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.summary == "System healthy"
    assert retrieved.overall_severity == "HEALTHY"


def test_get_triages_by_analysis(test_db):
    """Test retrieving all triages for an analysis."""
    # Create analysis
    analysis_data = {
        "filename": "test.log",
        "detected_format": "json",
        "total_lines": 100,
        "parsed_lines": 100,
        "failed_lines": 0,
        "parse_success_rate": 100.0,
        "error_rate": 0.0,
        "level_counts": {},
        "top_errors": [],
        "top_sources": [],
        "status_codes": {},
        "file_path": "/tmp/test.log"
    }
    analysis = crud.create_analysis(test_db, analysis_data)

    # Create multiple triages
    for i in range(3):
        triage_data = {
            "analysis_id": analysis.id,
            "summary": f"Triage {i}",
            "overall_severity": "MEDIUM",
            "confidence": 0.8,
            "issues": [],
            "provider_used": "anthropic",
            "analysis_time_ms": 1000.0
        }
        crud.create_triage(test_db, triage_data)

    # Retrieve all triages for this analysis
    triages = crud.get_triages_by_analysis(test_db, analysis.id)

    assert len(triages) == 3
    assert all(t.analysis_id == analysis.id for t in triages)


def test_cascade_delete_triages(test_db):
    """Test that deleting an analysis also deletes its triages."""
    # Create analysis
    analysis_data = {
        "filename": "test.log",
        "detected_format": "json",
        "total_lines": 100,
        "parsed_lines": 100,
        "failed_lines": 0,
        "parse_success_rate": 100.0,
        "error_rate": 0.0,
        "level_counts": {},
        "top_errors": [],
        "top_sources": [],
        "status_codes": {},
        "file_path": "/tmp/test.log"
    }
    analysis = crud.create_analysis(test_db, analysis_data)

    # Create triage
    triage_data = {
        "analysis_id": analysis.id,
        "summary": "Test",
        "overall_severity": "LOW",
        "confidence": 0.9,
        "issues": [],
        "provider_used": "anthropic",
        "analysis_time_ms": 1000.0
    }
    triage = crud.create_triage(test_db, triage_data)

    # Delete analysis
    crud.delete_analysis(test_db, analysis.id)

    # Verify triage is also deleted
    retrieved_triage = crud.get_triage(test_db, triage.id)
    assert retrieved_triage is None
