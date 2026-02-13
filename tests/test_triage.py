"""
Unit tests for the triage module.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from log_analyzer.ai_providers.base import (
    AIResponse,
    Severity,
    TriageResult,
)
from log_analyzer.triage import (
    TriageEngine,
    build_triage_prompt,
    parse_triage_response,
    quick_triage,
)

# =============================================================================
# Mock AnalysisResult for testing
# =============================================================================

class MockLogEntry:
    """Mock log entry for testing."""
    def __init__(self, level="ERROR", message="Test error", timestamp=None):
        self.level = level
        self.message = message
        self.timestamp = timestamp or datetime.now()


class MockAnalysisResult:
    """Mock AnalysisResult for testing."""
    def __init__(
        self,
        filepath="/var/log/test.log",
        total_lines=1000,
        parsed_lines=950,
        detected_format="syslog",
        level_counts=None,
        errors=None,
        warnings=None,
        top_errors=None,
        time_span=None,
        earliest_timestamp=None,
        latest_timestamp=None,
    ):
        self.filepath = filepath
        self.total_lines = total_lines
        self.parsed_lines = parsed_lines
        self.detected_format = detected_format
        self.level_counts = level_counts or {"ERROR": 50, "WARNING": 100, "INFO": 800}
        self.errors = errors or [MockLogEntry() for _ in range(5)]
        self.warnings = warnings or [MockLogEntry(level="WARNING") for _ in range(10)]
        self.top_errors = top_errors or [("Connection refused", 25), ("Timeout error", 15)]
        self.time_span = time_span
        self.earliest_timestamp = earliest_timestamp
        self.latest_timestamp = latest_timestamp


# =============================================================================
# Test build_triage_prompt
# =============================================================================

class TestBuildTriagePrompt:
    """Tests for prompt building."""

    def test_basic_prompt(self):
        """Test building a basic prompt."""
        result = MockAnalysisResult()

        prompt = build_triage_prompt(result)

        assert "/var/log/test.log" in prompt
        assert "syslog" in prompt
        assert "1,000" in prompt  # Total lines formatted
        assert "950" in prompt  # Parsed lines

    def test_includes_severity_breakdown(self):
        """Test that severity breakdown is included."""
        result = MockAnalysisResult(
            level_counts={"ERROR": 100, "WARNING": 200, "INFO": 700}
        )

        prompt = build_triage_prompt(result)

        assert "ERROR" in prompt
        assert "WARNING" in prompt
        assert "INFO" in prompt

    def test_includes_top_errors(self):
        """Test that top errors are included."""
        result = MockAnalysisResult(
            top_errors=[("Database connection failed", 50), ("Auth timeout", 30)]
        )

        prompt = build_triage_prompt(result)

        assert "Database connection failed" in prompt
        assert "[50x]" in prompt

    def test_truncates_long_error_messages(self):
        """Test that long error messages are truncated."""
        long_message = "A" * 200
        result = MockAnalysisResult(
            top_errors=[(long_message, 10)]
        )

        prompt = build_triage_prompt(result)

        # Should be truncated with ...
        assert "..." in prompt
        assert long_message not in prompt  # Full message should not appear

    def test_handles_no_errors(self):
        """Test handling when no errors exist."""
        result = MockAnalysisResult(
            errors=[],
            warnings=[],
            top_errors=[],
            level_counts={"INFO": 1000}
        )

        prompt = build_triage_prompt(result)

        # Should handle gracefully (may show default sample or "No" messages)
        assert "Log File Information" in prompt

    def test_includes_time_range(self):
        """Test that time range is included."""
        result = MockAnalysisResult(
            time_span=timedelta(hours=24)
        )

        prompt = build_triage_prompt(result)

        assert "Time Range" in prompt


# =============================================================================
# Test parse_triage_response
# =============================================================================

class TestParseTriageResponse:
    """Tests for response parsing."""

    def test_parse_valid_json(self):
        """Test parsing a valid JSON response."""
        json_content = '''
        {
            "summary": "System is experiencing database issues",
            "overall_severity": "HIGH",
            "confidence": 0.85,
            "issues": [
                {
                    "title": "Database Connection Failures",
                    "severity": "HIGH",
                    "confidence": 0.9,
                    "description": "Multiple connection failures detected",
                    "affected_components": ["database", "api"],
                    "recommendation": "Check database server status"
                }
            ]
        }
        '''

        response = AIResponse(
            content=json_content,
            model="test-model",
            provider="test",
            latency_ms=100,
        )
        result = MockAnalysisResult()

        triage_result = parse_triage_response(response, result)

        assert triage_result.summary == "System is experiencing database issues"
        assert triage_result.overall_severity == Severity.HIGH
        assert triage_result.confidence == 0.85
        assert len(triage_result.issues) == 1
        assert triage_result.issues[0].title == "Database Connection Failures"

    def test_parse_json_in_code_block(self):
        """Test parsing JSON wrapped in markdown code block."""
        json_content = '''
        Here is the analysis:

        ```json
        {
            "summary": "All systems operational",
            "overall_severity": "HEALTHY",
            "confidence": 0.95,
            "issues": []
        }
        ```
        '''

        response = AIResponse(
            content=json_content,
            model="test-model",
            provider="test",
            latency_ms=50,
        )
        result = MockAnalysisResult()

        triage_result = parse_triage_response(response, result)

        assert triage_result.summary == "All systems operational"
        assert triage_result.overall_severity == Severity.HEALTHY

    def test_parse_invalid_json_fallback(self):
        """Test fallback when JSON is invalid."""
        response = AIResponse(
            content="This is not valid JSON at all",
            model="test-model",
            provider="test",
            latency_ms=100,
        )
        result = MockAnalysisResult(errors=[MockLogEntry() for _ in range(5)])

        triage_result = parse_triage_response(response, result)

        # Should return fallback result
        assert "parsing failed" in triage_result.summary.lower()
        assert triage_result.confidence == 0.3
        assert triage_result.overall_severity == Severity.MEDIUM

    def test_parse_handles_missing_fields(self):
        """Test parsing handles missing optional fields."""
        json_content = '''
        {
            "summary": "Minimal response"
        }
        '''

        response = AIResponse(
            content=json_content,
            model="test-model",
            provider="test",
            latency_ms=100,
        )
        result = MockAnalysisResult()

        triage_result = parse_triage_response(response, result)

        assert triage_result.summary == "Minimal response"
        assert triage_result.overall_severity == Severity.MEDIUM  # Default
        assert triage_result.confidence == 0.5  # Default
        assert len(triage_result.issues) == 0


# =============================================================================
# Test TriageEngine
# =============================================================================

class TestTriageEngine:
    """Tests for TriageEngine class."""

    def test_initialization(self):
        """Test basic initialization."""
        engine = TriageEngine()

        assert engine._provider is None
        assert engine._provider_name is None

    def test_initialization_with_provider_name(self):
        """Test initialization with provider name."""
        engine = TriageEngine(provider_name="ollama")

        assert engine._provider_name == "ollama"

    @patch('log_analyzer.triage.get_provider')
    @patch('log_analyzer.triage.LogAnalyzer')
    def test_triage_calls_provider(self, mock_analyzer_class, mock_get_provider):
        """Test that triage uses the AI provider."""
        # Setup mocks
        mock_provider = MagicMock()
        mock_provider.name = "test"
        mock_provider.sanitize_log_content.return_value = "sanitized"
        mock_provider.analyze.return_value = AIResponse(
            content='{"summary": "Test", "overall_severity": "LOW", "confidence": 0.5, "issues": []}',
            model="test",
            provider="test",
            latency_ms=100,
        )
        mock_get_provider.return_value = mock_provider

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = MockAnalysisResult()
        mock_analyzer_class.return_value = mock_analyzer

        engine = TriageEngine()
        result = engine.triage("/var/log/test.log")

        # Verify provider was called
        mock_provider.analyze.assert_called_once()
        assert result.summary == "Test"

    def test_triage_from_result(self):
        """Test triage from existing analysis result."""
        mock_provider = MagicMock()
        mock_provider.sanitize_log_content.return_value = "sanitized"
        mock_provider.analyze.return_value = AIResponse(
            content='{"summary": "From result", "overall_severity": "MEDIUM", "confidence": 0.7, "issues": []}',
            model="test",
            provider="test",
            latency_ms=50,
        )

        engine = TriageEngine(provider=mock_provider)
        analysis_result = MockAnalysisResult()

        result = engine.triage_from_result(analysis_result)

        assert result.summary == "From result"
        mock_provider.analyze.assert_called_once()


# =============================================================================
# Test quick_triage convenience function
# =============================================================================

class TestQuickTriage:
    """Tests for quick_triage function."""

    @patch('log_analyzer.triage.TriageEngine')
    def test_quick_triage_creates_engine(self, mock_engine_class):
        """Test that quick_triage creates and uses engine."""
        mock_engine = MagicMock()
        mock_engine.triage.return_value = TriageResult(
            summary="Quick result",
            overall_severity=Severity.LOW,
            confidence=0.8,
            issues=[],
            analyzed_lines=100,
            error_count=5,
            warning_count=10,
        )
        mock_engine_class.return_value = mock_engine

        result = quick_triage("/var/log/test.log", provider="ollama")

        mock_engine_class.assert_called_once_with(provider_name="ollama")
        mock_engine.triage.assert_called_once_with("/var/log/test.log")
        assert result.summary == "Quick result"
