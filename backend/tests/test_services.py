"""
Tests for service layer (AnalyzerService and TriageService).
"""

import pytest
import os
import tempfile
from io import BytesIO
from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.db.database import Base
from backend.db import crud
from backend.services.analyzer_service import AnalyzerService
from backend.services.triage_service import TriageService


# Create test database
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture
def test_db():
    """Create test database session."""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_log_content():
    """Sample Apache access log content."""
    return b"""192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326
192.168.1.1 - - [10/Oct/2023:13:55:37 +0000] "GET /style.css HTTP/1.1" 200 1234
192.168.1.2 - - [10/Oct/2023:13:55:38 +0000] "GET /about.html HTTP/1.1" 404 512
192.168.1.1 - - [10/Oct/2023:13:55:39 +0000] "POST /api/data HTTP/1.1" 500 128
192.168.1.3 - - [10/Oct/2023:13:55:40 +0000] "GET /index.html HTTP/1.1" 200 2326
"""


@pytest.fixture
def sample_log_file(sample_log_content):
    """Create a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.log') as f:
        f.write(sample_log_content)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


def create_upload_file(content: bytes, filename: str = "test.log") -> UploadFile:
    """Create a FastAPI UploadFile for testing."""
    file_obj = BytesIO(content)
    return UploadFile(filename=filename, file=file_obj)


# ==================== AnalyzerService Tests ====================

def test_analyzer_service_init():
    """Test AnalyzerService initialization."""
    service = AnalyzerService()
    assert service.analyzer is not None


def test_analyze_file(sample_log_file):
    """Test analyzing a file."""
    service = AnalyzerService()
    result = service.analyze_file(sample_log_file, max_errors=10)

    assert result is not None
    assert result.total_lines == 5
    assert result.parsed_lines >= 4  # At least 4 lines should parse
    assert result.detected_format in ["apache_access", "universal"]  # Could be either


def test_analysis_result_to_dict(sample_log_file):
    """Test converting AnalysisResult to dict."""
    service = AnalyzerService()
    result = service.analyze_file(sample_log_file)

    data = service.analysis_result_to_dict(
        result,
        file_path="/tmp/test.log",
        original_filename="test.log"
    )

    assert data["filename"] == "test.log"
    assert data["detected_format"] == result.detected_format
    assert data["total_lines"] == result.total_lines
    assert data["parsed_lines"] == result.parsed_lines
    assert "level_counts" in data
    assert "top_errors" in data
    assert data["file_path"] == "/tmp/test.log"


@pytest.mark.asyncio
async def test_save_uploaded_file(sample_log_content):
    """Test saving uploaded file."""
    service = AnalyzerService()
    upload_file = create_upload_file(sample_log_content, "test.log")

    file_path = await service.save_uploaded_file(upload_file)

    assert os.path.exists(file_path)
    assert file_path.endswith(".log")

    # Verify content
    with open(file_path, 'rb') as f:
        content = f.read()
        assert content == sample_log_content

    # Cleanup
    os.remove(file_path)


@pytest.mark.asyncio
async def test_analyze_uploaded_file(test_db, sample_log_content):
    """Test complete workflow: upload, analyze, store."""
    service = AnalyzerService()
    upload_file = create_upload_file(sample_log_content, "test_apache.log")

    analysis = await service.analyze_uploaded_file(
        upload_file,
        test_db,
        max_errors=10
    )

    assert analysis.id is not None
    assert analysis.filename == "test_apache.log"
    assert analysis.total_lines == 5
    assert analysis.parsed_lines >= 4
    assert os.path.exists(analysis.file_path)

    # Cleanup
    if os.path.exists(analysis.file_path):
        os.remove(analysis.file_path)


def test_delete_file(sample_log_file):
    """Test deleting a file."""
    service = AnalyzerService()

    # File exists
    assert os.path.exists(sample_log_file)

    # Delete it
    result = service.delete_file(sample_log_file)
    assert result is True
    assert not os.path.exists(sample_log_file)

    # Try deleting again (should return False)
    result = service.delete_file(sample_log_file)
    assert result is False


# ==================== TriageService Tests ====================

@pytest.mark.skip(reason="Requires AI API key and network access")
def test_triage_service_init():
    """Test TriageService initialization."""
    service = TriageService()
    assert service.engine is not None


@pytest.mark.skip(reason="Requires AI API key and network access")
def test_triage_file(sample_log_file):
    """Test running triage on a file."""
    service = TriageService(provider_name="anthropic")
    result = service.triage_file(sample_log_file, max_errors=10)

    assert result is not None
    assert result.summary is not None
    assert result.overall_severity is not None
    assert result.confidence >= 0 and result.confidence <= 1.0
    assert result.provider_used in ["anthropic", "gemini", "ollama"]


@pytest.mark.skip(reason="Requires AI API key and network access")
@pytest.mark.asyncio
async def test_run_triage_on_analysis(test_db, sample_log_content):
    """Test running triage on an existing analysis."""
    # First create an analysis
    analyzer_service = AnalyzerService()
    upload_file = create_upload_file(sample_log_content, "test.log")
    analysis = await analyzer_service.analyze_uploaded_file(upload_file, test_db)

    # Run triage
    triage_service = TriageService(provider_name="anthropic")
    triage = triage_service.run_triage_on_analysis(
        test_db,
        analysis.id
    )

    assert triage.id is not None
    assert triage.analysis_id == analysis.id
    assert triage.summary is not None
    assert triage.overall_severity is not None
    assert triage.provider_used is not None

    # Cleanup
    if os.path.exists(analysis.file_path):
        os.remove(analysis.file_path)


def test_triage_service_analysis_not_found(test_db):
    """Test triage fails when analysis doesn't exist."""
    service = TriageService()

    with pytest.raises(ValueError, match="Analysis .* not found"):
        service.run_triage_on_analysis(test_db, "non-existent-id")


# ==================== Integration Tests ====================

@pytest.mark.asyncio
async def test_full_workflow_without_triage(test_db, sample_log_content):
    """Test full workflow: upload, analyze, retrieve."""
    # Upload and analyze
    service = AnalyzerService()
    upload_file = create_upload_file(sample_log_content, "integration_test.log")

    analysis = await service.analyze_uploaded_file(upload_file, test_db)

    # Retrieve from database
    retrieved = crud.get_analysis(test_db, analysis.id)

    assert retrieved is not None
    assert retrieved.id == analysis.id
    assert retrieved.filename == "integration_test.log"
    assert retrieved.total_lines == 5

    # Cleanup
    service.delete_file(analysis.file_path)


@pytest.mark.asyncio
async def test_error_handling_invalid_file(test_db):
    """Test error handling with invalid log file."""
    service = AnalyzerService()

    # Create invalid file (empty)
    upload_file = create_upload_file(b"", "empty.log")

    analysis = await service.analyze_uploaded_file(upload_file, test_db)

    # Should still create analysis even with empty file
    assert analysis is not None
    assert analysis.total_lines == 0

    # Cleanup
    if os.path.exists(analysis.file_path):
        os.remove(analysis.file_path)
