"""
Comprehensive unit tests for ReportGenerator.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from log_analyzer.analyzer import AnalysisResult
from log_analyzer.parsers import LogEntry
from log_analyzer.report import ReportGenerator
from log_analyzer.stats_models import AnalyticsData

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def basic_result():
    return AnalysisResult(
        filepath="test.log",
        detected_format="standard",
        total_lines=100,
        parsed_lines=100,
        failed_lines=0,
        level_counts={"INFO": 90, "ERROR": 10},
        errors=[],
        warnings=[],
    )


@pytest.fixture
def full_result():
    """AnalysisResult with all optional fields populated."""
    return AnalysisResult(
        filepath="/var/log/app.log",
        detected_format="json",
        total_lines=1000,
        parsed_lines=950,
        failed_lines=50,
        level_counts={"CRITICAL": 5, "ERROR": 30, "WARNING": 50, "INFO": 800, "DEBUG": 65},
        earliest_timestamp=datetime(2020, 1, 1, 0, 0, 0),
        latest_timestamp=datetime(2020, 1, 1, 23, 59, 59),
        errors=[
            LogEntry(timestamp=datetime(2020, 1, 1, 12, 0), level="ERROR",
                     message="Connection refused"),
        ],
        warnings=[],
        top_errors=[("Connection refused", 15), ("Timeout", 10)],
        top_sources=[("api-server", 500), ("worker", 300)],
        status_codes={200: 600, 301: 50, 404: 100, 500: 30},
        analytics=AnalyticsData(
            temporal_distribution={"2020-01-01T12:00": 100, "2020-01-01T13:00": 200},
            hourly_distribution={12: 100, 13: 200},
        ),
    )


# ---------------------------------------------------------------------------
# Markdown Report
# ---------------------------------------------------------------------------

class TestMarkdownReport:
    def test_basic_report(self, basic_result):
        report = ReportGenerator(basic_result).to_markdown()
        assert "# Log Analysis Report" in report
        assert "test.log" in report
        assert "100" in report
        assert "ERROR" in report

    def test_with_timestamps(self, full_result):
        report = ReportGenerator(full_result).to_markdown()
        assert "First Entry" in report
        assert "Last Entry" in report
        assert "Time Span" in report

    def test_with_status_codes(self, full_result):
        report = ReportGenerator(full_result).to_markdown()
        assert "HTTP Status Codes" in report
        assert "200" in report
        assert "404" in report
        assert "500" in report

    def test_with_top_errors(self, full_result):
        report = ReportGenerator(full_result).to_markdown()
        assert "Top Error Messages" in report
        assert "Connection refused" in report

    def test_with_top_sources(self, full_result):
        report = ReportGenerator(full_result).to_markdown()
        assert "Top Sources" in report
        assert "api-server" in report

    def test_with_analytics(self, full_result):
        report = ReportGenerator(full_result).to_markdown()
        assert "Analytics" in report
        assert "Hourly Distribution" in report

    def test_empty_result(self):
        result = AnalysisResult(
            filepath="empty.log", detected_format="unknown",
            total_lines=0, parsed_lines=0, failed_lines=0,
        )
        report = ReportGenerator(result).to_markdown()
        assert "# Log Analysis Report" in report
        assert "empty.log" in report


# ---------------------------------------------------------------------------
# HTML Report
# ---------------------------------------------------------------------------

class TestHTMLReport:
    def test_basic_html(self, basic_result):
        report = ReportGenerator(basic_result).to_html()
        assert "<html" in report.lower()
        assert "test.log" in report

    def test_html_with_chart_js(self, full_result):
        report = ReportGenerator(full_result).to_html()
        assert "chart.js" in report.lower() or "Chart" in report

    def test_html_with_full_data(self, full_result):
        report = ReportGenerator(full_result).to_html()
        assert "CRITICAL" in report
        assert "ERROR" in report
        assert "Connection refused" in report

    def test_html_contains_severity(self, full_result):
        report = ReportGenerator(full_result).to_html()
        assert "ERROR" in report
        assert "CRITICAL" in report


# ---------------------------------------------------------------------------
# CSV Report
# ---------------------------------------------------------------------------

class TestCSVReport:
    def test_basic_csv(self, basic_result):
        report = ReportGenerator(basic_result).to_csv()
        assert "File,test.log" in report
        assert "Total Lines,100" in report

    def test_csv_severity_breakdown(self, full_result):
        report = ReportGenerator(full_result).to_csv()
        assert "Level,Count,Percentage" in report
        assert "ERROR" in report

    def test_csv_with_status_codes(self, full_result):
        report = ReportGenerator(full_result).to_csv()
        assert "200" in report

    def test_csv_with_top_errors(self, full_result):
        report = ReportGenerator(full_result).to_csv()
        assert "Connection refused" in report


# ---------------------------------------------------------------------------
# JSON Report
# ---------------------------------------------------------------------------

class TestJSONReport:
    def test_basic_json(self, basic_result):
        report = ReportGenerator(basic_result).to_json()
        data = json.loads(report)
        assert data["metadata"]["total_lines"] == 100
        assert data["metadata"]["filepath"] == "test.log"

    def test_json_with_full_data(self, full_result):
        report = ReportGenerator(full_result).to_json()
        data = json.loads(report)
        assert data["metadata"]["total_lines"] == 1000
        assert "severity" in data

    def test_json_is_valid(self, full_result):
        report = ReportGenerator(full_result).to_json()
        # Should not raise
        json.loads(report)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

class TestSave:
    def test_save_markdown(self, basic_result):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "report.md")
            ReportGenerator(basic_result).save(path, format="markdown")
            content = Path(path).read_text()
            assert "# Log Analysis Report" in content

    def test_save_html(self, basic_result):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "report.html")
            ReportGenerator(basic_result).save(path, format="html")
            content = Path(path).read_text()
            assert "<html" in content.lower()

    def test_save_json(self, basic_result):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "report.json")
            ReportGenerator(basic_result).save(path, format="json")
            content = Path(path).read_text()
            json.loads(content)  # Should not raise

    def test_save_csv(self, basic_result):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "report.csv")
            ReportGenerator(basic_result).save(path, format="csv")
            content = Path(path).read_text()
            assert "File,test.log" in content

    def test_save_default_format(self, basic_result):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "report.md")
            ReportGenerator(basic_result).save(path)
            content = Path(path).read_text()
            assert "# Log Analysis Report" in content
