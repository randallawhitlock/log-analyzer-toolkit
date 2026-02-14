"""
Tests for CLI display functions and additional command paths.

These tests exercise the internal display helpers and edge cases
in CLI commands to improve cli.py coverage.
"""

from click.testing import CliRunner
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest

from log_analyzer.cli import (
    cli, _display_analysis, _display_analytics,
    _display_hourly_chart, _display_temporal_table,
)
from log_analyzer.analyzer import AnalysisResult
from log_analyzer.parsers import LogEntry
from log_analyzer.stats_models import AnalyticsData


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# _display_analysis
# ---------------------------------------------------------------------------

class TestDisplayAnalysis:
    def test_basic_display(self, capsys):
        """Display analysis with minimal data."""
        result = AnalysisResult(
            filepath="/var/log/test.log",
            detected_format="syslog",
            total_lines=100,
            parsed_lines=90,
            failed_lines=10,
            level_counts={"INFO": 80, "ERROR": 10},
        )
        _display_analysis(result)

    def test_display_with_timestamps(self, capsys):
        """Display analysis with timestamps."""
        result = AnalysisResult(
            filepath="test.log",
            detected_format="json",
            total_lines=50,
            parsed_lines=50,
            failed_lines=0,
            level_counts={"INFO": 45, "WARNING": 5},
            earliest_timestamp=datetime(2020, 1, 1, 0, 0),
            latest_timestamp=datetime(2020, 1, 2, 0, 0),
        )
        _display_analysis(result)

    def test_display_with_status_codes(self, capsys):
        """Display analysis with HTTP status codes."""
        result = AnalysisResult(
            filepath="access.log",
            detected_format="nginx_access",
            total_lines=200,
            parsed_lines=200,
            failed_lines=0,
            level_counts={},
            status_codes={200: 150, 301: 20, 404: 20, 500: 10},
        )
        _display_analysis(result)

    def test_display_with_top_errors(self, capsys):
        """Display analysis with top error messages."""
        result = AnalysisResult(
            filepath="app.log",
            detected_format="universal",
            total_lines=100,
            parsed_lines=100,
            failed_lines=0,
            level_counts={"ERROR": 30, "INFO": 70},
            top_errors=[
                ("Connection refused", 15),
                ("Timeout waiting for response", 10),
                ("Null pointer exception", 5),
            ],
        )
        _display_analysis(result)

    def test_display_with_top_sources(self, capsys):
        """Display analysis with top sources."""
        result = AnalysisResult(
            filepath="app.log",
            detected_format="universal",
            total_lines=100,
            parsed_lines=100,
            failed_lines=0,
            level_counts={"INFO": 100},
            top_sources=[("api-server", 60), ("worker", 40)],
        )
        _display_analysis(result)

    def test_display_with_analytics(self, capsys):
        """Display analysis with analytics data."""
        result = AnalysisResult(
            filepath="app.log",
            detected_format="universal",
            total_lines=100,
            parsed_lines=100,
            failed_lines=0,
            level_counts={"INFO": 100},
            analytics=AnalyticsData(
                temporal_distribution={"2020-01-01T12:00": 50, "2020-01-01T13:00": 50},
                hourly_distribution={12: 50, 13: 50},
            ),
        )
        _display_analysis(result)

    def test_display_all_severity_levels(self, capsys):
        """Display analysis with all severity levels."""
        result = AnalysisResult(
            filepath="app.log",
            detected_format="universal",
            total_lines=100,
            parsed_lines=100,
            failed_lines=0,
            level_counts={
                "CRITICAL": 2, "ERROR": 8, "WARNING": 20,
                "INFO": 60, "DEBUG": 10,
            },
        )
        _display_analysis(result)


# ---------------------------------------------------------------------------
# _display_analytics helpers
# ---------------------------------------------------------------------------

class TestDisplayAnalyticsHelpers:
    def test_display_hourly_chart(self, capsys):
        dist = {0: 10, 6: 50, 12: 100, 18: 75, 23: 20}
        from rich.console import Console
        console = Console(file=StringIO())
        _display_hourly_chart(dist, console)

    def test_display_hourly_chart_empty(self, capsys):
        from rich.console import Console
        console = Console(file=StringIO())
        _display_hourly_chart({}, console)

    def test_display_temporal_table(self, capsys):
        from rich.console import Console
        console = Console(file=StringIO())
        dist = {
            "2020-01-01T12:00": 50,
            "2020-01-01T13:00": 100,
            "2020-01-01T14:00": 75,
        }
        _display_temporal_table(dist, console)

    def test_display_analytics(self, capsys):
        from rich.console import Console
        console = Console(file=StringIO())
        analytics = AnalyticsData(
            temporal_distribution={"2020-01-01T12:00": 50},
            hourly_distribution={12: 50},
        )
        _display_analytics(analytics, console)


# ---------------------------------------------------------------------------
# CLI errors command edge cases
# ---------------------------------------------------------------------------

class TestCLIErrorsEdgeCases:
    @patch('log_analyzer.cli.LogAnalyzer')
    def test_errors_with_warning_level(self, mock_analyzer_cls, runner):
        entries = [
            LogEntry(timestamp=datetime(2020, 1, 1, 12, 0), level="WARNING", message="Disk full"),
            LogEntry(timestamp=None, level="INFO", message="All good"),
        ]
        mock_analyzer_cls.return_value.parse_file.return_value = iter(entries)

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("dummy\n")
            result = runner.invoke(cli, ["errors", "test.log", "--level", "WARNING"])
            assert result.exit_code == 0
            assert "Disk full" in result.output

    @patch('log_analyzer.cli.LogAnalyzer')
    def test_errors_with_all_levels(self, mock_analyzer_cls, runner):
        entries = [
            LogEntry(timestamp=None, level="CRITICAL", message="System crash"),
            LogEntry(timestamp=None, level="ERROR", message="Error!"),
            LogEntry(timestamp=None, level="WARNING", message="Warning!"),
        ]
        mock_analyzer_cls.return_value.parse_file.return_value = iter(entries)

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("dummy\n")
            result = runner.invoke(cli, ["errors", "test.log", "--level", "WARNING"])
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI detect command edge cases
# ---------------------------------------------------------------------------

class TestCLIDetectEdgeCases:
    @patch('log_analyzer.cli.LogAnalyzer')
    def test_detect_file_not_found(self, mock_analyzer_cls, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["detect", "nonexistent.log"])
            assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CLI configure command
# ---------------------------------------------------------------------------

class TestCLIConfigureEdgeCases:
    def test_configure_no_args(self, runner):
        result = runner.invoke(cli, ["configure"])
        assert result.exit_code == 0

    def test_configure_help(self, runner):
        result = runner.invoke(cli, ["configure", "--help"])
        assert result.exit_code == 0
        assert "Configure AI providers" in result.output
