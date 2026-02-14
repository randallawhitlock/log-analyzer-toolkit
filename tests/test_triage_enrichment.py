
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock
from log_analyzer.analyzer import AnalysisResult
from log_analyzer.triage import build_triage_prompt
from log_analyzer.ai_providers.base import Severity, TriageIssue

class TestTriageEnrichment:
    def test_build_triage_prompt_full_enrichment(self):
        """Test that build_triage_prompt includes all new fields when data is available."""
        # Create a rich AnalysisResult
        result = MagicMock(spec=AnalysisResult)
        result.filepath = "/var/log/app.log"
        result.detected_format = "nginx_access"
        result.total_lines = 1000
        result.parsed_lines = 1000
        result.time_span = timedelta(hours=1)
        result.level_counts = {"ERROR": 10, "WARNING": 50, "INFO": 940}
        
        # Top errors
        result.top_errors = [("Connection refused", 5), ("Timeout", 5)]
        
        # Warnings (list of objects with message/timestamp attributes)
        WarningEntry = MagicMock()
        WarningEntry.message = "Disk usage high"
        WarningEntry.timestamp = datetime(2023, 1, 1, 12, 0, 0)
        WarningEntry.level = "WARNING"
        WarningEntry.source = "system"
        
        # Create 50 warnings
        result.warnings = [WarningEntry] * 50
        
        # Errors
        ErrorEntry = MagicMock()
        ErrorEntry.message = "Connection error"
        ErrorEntry.timestamp = datetime(2023, 1, 1, 12, 0, 1)
        ErrorEntry.level = "ERROR"
        ErrorEntry.source = "db_pool"
        result.errors = [ErrorEntry] * 10
        
        # Top sources
        result.top_sources = [("db_pool", 5), ("api_gateway", 5)]
        
        # Status codes
        result.status_codes = {200: 900, 404: 50, 500: 50}
        
        # Analytics mock
        result.analytics = MagicMock()
        result.analytics.error_rate_trend = "increasing"
        result.analytics.temporal_distribution = {"12:00": 100, "12:05": 50}
        result.analytics.hourly_distribution = {12: 1000}
        
        # Timestamps
        result.earliest_timestamp = None
        result.latest_timestamp = None

        # Build prompt
        prompt = build_triage_prompt(result)
        
        # Verify content
        assert "## Top Warnings" in prompt
        assert "Disk usage high" in prompt
        assert "## Error Sources" in prompt
        assert "db_pool: 5 entries" in prompt
        assert "## HTTP Status Codes" in prompt
        assert "HTTP 500: 50" in prompt
        assert "## Temporal Patterns" in prompt
        assert "Error rate trend: increasing" in prompt
        assert "Peak hour 12:00" in prompt
        assert "## Sample Warning Entries" in prompt
        assert "WARNING (system): Disk usage high" in prompt

    def test_build_triage_prompt_minimal(self):
        """Test graceful degradation when optional data is missing."""
        result = MagicMock(spec=AnalysisResult)
        result.filepath = "test.log"
        result.detected_format = "unknown"
        result.total_lines = 0
        result.parsed_lines = 0
        result.level_counts = {}
        result.top_errors = []
        result.warnings = []
        result.errors = []
        result.top_sources = []
        result.status_codes = {}
        result.analytics = None
        result.time_span = None
        result.earliest_timestamp = None
        result.latest_timestamp = None
        
        prompt = build_triage_prompt(result)
        
        assert "No severity levels detected" in prompt
        assert "No errors detected" in prompt
        assert "No warnings detected" in prompt
        assert "No source data available" in prompt
        assert "No HTTP status code data" in prompt
        assert "No temporal data available" in prompt
