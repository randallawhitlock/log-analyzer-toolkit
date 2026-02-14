"""
Comprehensive unit tests for triage module.
"""

import json
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from log_analyzer.analyzer import AnalysisResult
from log_analyzer.ai_providers.base import AIResponse
from log_analyzer.parsers import LogEntry
from log_analyzer.triage import (
    TriageEngine,
    TriageResult,
    TriageIssue,
    Severity,
    build_triage_prompt,
    parse_triage_response,
    quick_triage,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def analysis_result():
    return AnalysisResult(
        filepath="/var/log/test.log",
        detected_format="syslog",
        total_lines=1000,
        parsed_lines=950,
        failed_lines=50,
        level_counts={"ERROR": 30, "WARNING": 50, "INFO": 870},
        earliest_timestamp=datetime(2020, 1, 1, 0, 0, 0),
        latest_timestamp=datetime(2020, 1, 1, 23, 59, 59),
        errors=[
            LogEntry(timestamp=datetime(2020, 1, 1, 12, 0), level="ERROR",
                     message="Connection refused to database"),
            LogEntry(timestamp=datetime(2020, 1, 1, 12, 5), level="ERROR",
                     message="Timeout waiting for response"),
        ],
        warnings=[],
        top_errors=[("Connection refused", 15), ("Timeout", 10)],
        top_sources=[("app-server", 500)],
    )


@pytest.fixture
def mock_ai_response():
    data = {
        "summary": "Database connectivity issues detected",
        "overall_severity": "HIGH",
        "confidence": 0.92,
        "issues": [
            {
                "title": "Database Connection Failures",
                "severity": "HIGH",
                "confidence": 0.95,
                "description": "Multiple connection refused errors",
                "affected_components": ["database", "api-server"],
                "sample_logs": ["Connection refused to database"],
                "recommendation": "Check database server status",
            }
        ],
    }
    return AIResponse(
        content=json.dumps(data),
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        latency_ms=1500,
        usage={"input": 500, "output": 200},
    )


# ---------------------------------------------------------------------------
# build_triage_prompt
# ---------------------------------------------------------------------------

class TestBuildTriagePrompt:
    def test_basic_prompt(self, analysis_result):
        prompt = build_triage_prompt(analysis_result)
        assert isinstance(prompt, str)
        assert "/var/log/test.log" in prompt
        assert "syslog" in prompt
        assert "1,000" in prompt
        assert "ERROR" in prompt

    def test_prompt_includes_top_errors(self, analysis_result):
        prompt = build_triage_prompt(analysis_result)
        assert "Connection refused" in prompt

    def test_prompt_includes_sample_errors(self, analysis_result):
        prompt = build_triage_prompt(analysis_result)
        assert "Connection refused to database" in prompt

    def test_prompt_with_no_errors(self, analysis_result):
        analysis_result.errors = []
        analysis_result.top_errors = []
        analysis_result.level_counts = {"INFO": 950}
        prompt = build_triage_prompt(analysis_result)
        assert "No errors detected" in prompt

    def test_prompt_without_timestamps(self, analysis_result):
        analysis_result.earliest_timestamp = None
        analysis_result.latest_timestamp = None
        prompt = build_triage_prompt(analysis_result)
        assert "Unknown" in prompt


# ---------------------------------------------------------------------------
# parse_triage_response
# ---------------------------------------------------------------------------

class TestParseTriageResponse:
    def test_valid_json_response(self, mock_ai_response, analysis_result):
        result = parse_triage_response(mock_ai_response, analysis_result)
        assert isinstance(result, TriageResult)
        assert result.summary == "Database connectivity issues detected"
        assert result.overall_severity == Severity.HIGH
        assert result.confidence == pytest.approx(0.92)
        assert len(result.issues) == 1
        assert result.issues[0].title == "Database Connection Failures"

    def test_json_in_code_block(self, analysis_result):
        data = {"summary": "test", "overall_severity": "LOW", "confidence": 0.5, "issues": []}
        content = f"```json\n{json.dumps(data)}\n```"
        response = AIResponse(content=content, provider="test", model="m",
                              latency_ms=100, usage={})
        result = parse_triage_response(response, analysis_result)
        assert result.summary == "test"
        assert result.overall_severity == Severity.LOW

    def test_invalid_json_returns_fallback(self, analysis_result):
        response = AIResponse(content="This is not JSON at all",
                              provider="test", model="m",
                              latency_ms=100, usage={})
        result = parse_triage_response(response, analysis_result)
        assert isinstance(result, TriageResult)
        assert "parsing failed" in result.summary
        assert result.confidence == pytest.approx(0.3)
        assert result.overall_severity == Severity.MEDIUM

    def test_malformed_issue_skipped(self, analysis_result):
        data = {
            "summary": "test",
            "overall_severity": "MEDIUM",
            "confidence": 0.5,
            "issues": [
                {"title": "Good issue", "severity": "HIGH", "confidence": 0.8},
                {"severity": "INVALID_SEVERITY_VALUE", "confidence": "not-a-number"},
            ],
        }
        response = AIResponse(content=json.dumps(data), provider="test", model="m",
                              latency_ms=100, usage={})
        result = parse_triage_response(response, analysis_result)
        # Should not crash - malformed entries are skipped or handled
        assert isinstance(result, TriageResult)
        # At least the good issue should parse
        assert len(result.issues) >= 1

    def test_unknown_severity_defaults_to_medium(self, analysis_result):
        data = {
            "summary": "test", "overall_severity": "UNKNOWN_LEVEL",
            "confidence": 0.5, "issues": [],
        }
        response = AIResponse(content=json.dumps(data), provider="test", model="m",
                              latency_ms=100, usage={})
        result = parse_triage_response(response, analysis_result)
        assert result.overall_severity == Severity.MEDIUM

    def test_response_with_thinking_block(self, analysis_result):
        """Response that has <thinking> block before JSON."""
        data = {"summary": "ok", "overall_severity": "LOW", "confidence": 0.7, "issues": []}
        content = f"<thinking>Let me analyze...</thinking>\n{json.dumps(data)}"
        response = AIResponse(content=content, provider="test", model="m",
                              latency_ms=100, usage={})
        result = parse_triage_response(response, analysis_result)
        assert result.summary == "ok"


# ---------------------------------------------------------------------------
# TriageEngine
# ---------------------------------------------------------------------------

class TestTriageEngine:
    def test_init_with_provider(self):
        mock_provider = MagicMock()
        engine = TriageEngine(provider=mock_provider)
        assert engine._provider is mock_provider

    def test_init_with_provider_name(self):
        engine = TriageEngine(provider_name="ollama")
        assert engine._provider_name == "ollama"
        assert engine._provider is None

    def test_get_provider_returns_cached(self):
        mock_provider = MagicMock()
        mock_provider.name = "test"
        engine = TriageEngine(provider=mock_provider)
        assert engine._get_provider() is mock_provider

    @patch('log_analyzer.triage.get_provider')
    def test_get_provider_auto_detects(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider.name = "anthropic"
        mock_provider.get_model.return_value = "model"
        mock_get_provider.return_value = mock_provider

        engine = TriageEngine()
        provider = engine._get_provider()
        assert provider is mock_provider
        mock_get_provider.assert_called_once_with(None)

    @patch('log_analyzer.triage.get_provider')
    def test_triage_from_result(self, mock_get_provider, analysis_result, mock_ai_response):
        mock_provider = MagicMock()
        mock_provider.name = "test"
        mock_provider.get_model.return_value = "m"
        mock_provider.analyze.return_value = mock_ai_response
        mock_provider.sanitize_log_content.side_effect = lambda x: x
        mock_get_provider.return_value = mock_provider

        engine = TriageEngine()
        result = engine.triage_from_result(analysis_result)
        assert isinstance(result, TriageResult)
        assert result.summary == "Database connectivity issues detected"
        mock_provider.analyze.assert_called_once()

    @patch('log_analyzer.triage.get_provider')
    def test_triage_full_pipeline(self, mock_get_provider, mock_ai_response):
        """Test triage() which reads a file, analyzes it, and runs AI."""
        mock_provider = MagicMock()
        mock_provider.name = "test"
        mock_provider.get_model.return_value = "m"
        mock_provider.analyze.return_value = mock_ai_response
        mock_provider.sanitize_log_content.side_effect = lambda x: x
        mock_get_provider.return_value = mock_provider

        engine = TriageEngine()
        # Mock the internal analyzer
        mock_analysis = AnalysisResult(
            filepath="test.log", detected_format="json",
            total_lines=10, parsed_lines=10, failed_lines=0,
            level_counts={"ERROR": 2}, errors=[], warnings=[],
            top_errors=[], top_sources=[],
        )
        engine._analyzer = MagicMock()
        engine._analyzer.analyze.return_value = mock_analysis

        result = engine.triage("test.log")
        assert isinstance(result, TriageResult)
        engine._analyzer.analyze.assert_called_once()


# ---------------------------------------------------------------------------
# quick_triage
# ---------------------------------------------------------------------------

class TestQuickTriage:
    @patch('log_analyzer.triage.TriageEngine')
    def test_quick_triage(self, mock_engine_cls):
        mock_engine = mock_engine_cls.return_value
        mock_result = MagicMock(spec=TriageResult)
        mock_engine.triage.return_value = mock_result

        result = quick_triage("/var/log/app.log", provider="ollama")
        assert result is mock_result
        mock_engine_cls.assert_called_once_with(provider_name="ollama")
        mock_engine.triage.assert_called_once_with("/var/log/app.log")

    @patch('log_analyzer.triage.TriageEngine')
    def test_quick_triage_auto_detect(self, mock_engine_cls):
        mock_engine = mock_engine_cls.return_value
        mock_engine.triage.return_value = MagicMock(spec=TriageResult)

        quick_triage("/var/log/app.log")
        mock_engine_cls.assert_called_once_with(provider_name=None)
