"""
Comprehensive unit tests for CLI commands.
"""

from click.testing import CliRunner
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime
import json
import pytest

from log_analyzer.cli import cli
from log_analyzer.analyzer import AnalysisResult


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


def _make_result(**overrides):
    """Create a mock AnalysisResult with sensible defaults."""
    defaults = dict(
        filepath="test.log",
        detected_format="universal",
        total_lines=100,
        parsed_lines=95,
        failed_lines=5,
        level_counts={"ERROR": 10, "WARNING": 20, "INFO": 65},
        earliest_timestamp=datetime(2020, 1, 1, 0, 0, 0),
        latest_timestamp=datetime(2020, 1, 1, 23, 59, 59),
        errors=[],
        warnings=[],
        top_sources=[("src1", 50), ("src2", 30)],
        top_errors=[("connection timeout", 8), ("null ptr", 2)],
        status_codes={200: 60, 404: 20, 500: 15},
        analytics=None,
    )
    defaults.update(overrides)
    return AnalysisResult(**defaults)


# ---------------------------------------------------------------------------
# Help & top-level
# ---------------------------------------------------------------------------

class TestCLIHelp:
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Log Analyzer Toolkit" in result.output

    def test_analyze_help(self, runner):
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "Analyze a log file" in result.output

    def test_triage_help(self, runner):
        result = runner.invoke(cli, ["triage", "--help"])
        assert result.exit_code == 0
        assert "AI-powered intelligent log triage" in result.output


# ---------------------------------------------------------------------------
# analyze command
# ---------------------------------------------------------------------------

class TestAnalyzeCommand:
    @patch('log_analyzer.cli.LogAnalyzer')
    @patch('log_analyzer.reader.LogReader')
    def test_analyze_basic(self, mock_reader_cls, mock_analyzer_cls, runner):
        """Basic analyze runs and displays results."""
        mock_reader = mock_reader_cls.return_value
        mock_reader.count_lines.return_value = 10

        mock_analyzer = mock_analyzer_cls.return_value
        mock_analyzer.analyze.return_value = _make_result()

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("line\n" * 10)
            result = runner.invoke(cli, ["analyze", "test.log", "--no-threading"])
            assert result.exit_code == 0

    @patch('log_analyzer.cli.LogAnalyzer')
    @patch('log_analyzer.reader.LogReader')
    def test_analyze_with_report(self, mock_reader_cls, mock_analyzer_cls, runner):
        """Analyze with --report and --output saves a file."""
        mock_reader = mock_reader_cls.return_value
        mock_reader.count_lines.return_value = 5

        mock_analyzer = mock_analyzer_cls.return_value
        mock_analyzer.analyze.return_value = _make_result()

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("line\n" * 5)
            result = runner.invoke(cli, [
                "analyze", "test.log", "--report", "json",
                "--output", "report.json", "--no-threading",
            ])
            assert result.exit_code == 0
            assert "Report saved" in result.output

    @patch('log_analyzer.cli.LogAnalyzer')
    @patch('log_analyzer.reader.LogReader')
    def test_analyze_file_not_found(self, mock_reader_cls, mock_analyzer_cls, runner):
        """Analyze nonexistent file returns error."""
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["analyze", "nope.log"])
            assert result.exit_code != 0

    @patch('log_analyzer.cli.LogAnalyzer')
    @patch('log_analyzer.reader.LogReader')
    def test_analyze_value_error(self, mock_reader_cls, mock_analyzer_cls, runner):
        """ValueError during analysis prints error."""
        mock_reader = mock_reader_cls.return_value
        mock_reader.count_lines.return_value = 1

        mock_analyzer = mock_analyzer_cls.return_value
        mock_analyzer.analyze.side_effect = ValueError("bad format")

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("hello")
            result = runner.invoke(cli, ["analyze", "test.log", "--no-threading"])
            assert result.exit_code != 0

    @patch('log_analyzer.cli.LogAnalyzer')
    @patch('log_analyzer.reader.LogReader')
    def test_analyze_with_format(self, mock_reader_cls, mock_analyzer_cls, runner):
        """Analyze with --format option."""
        mock_reader = mock_reader_cls.return_value
        mock_reader.count_lines.return_value = 5

        mock_analyzer = mock_analyzer_cls.return_value
        mock_analyzer.analyze.return_value = _make_result(detected_format="json")

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("line\n" * 5)
            result = runner.invoke(cli, [
                "analyze", "test.log", "--format", "json", "--no-threading",
            ])
            assert result.exit_code == 0

    @patch('log_analyzer.cli.LogAnalyzer')
    @patch('log_analyzer.reader.LogReader')
    def test_analyze_markdown_report(self, mock_reader_cls, mock_analyzer_cls, runner):
        """Analyze generating markdown report."""
        mock_reader = mock_reader_cls.return_value
        mock_reader.count_lines.return_value = 5

        mock_analyzer = mock_analyzer_cls.return_value
        mock_analyzer.analyze.return_value = _make_result()

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("line\n" * 5)
            result = runner.invoke(cli, [
                "analyze", "test.log", "--report", "markdown",
                "--output", "report.md", "--no-threading",
            ])
            assert result.exit_code == 0

    @patch('log_analyzer.cli.LogAnalyzer')
    @patch('log_analyzer.reader.LogReader')
    def test_analyze_html_report(self, mock_reader_cls, mock_analyzer_cls, runner):
        """Analyze generating HTML report."""
        mock_reader = mock_reader_cls.return_value
        mock_reader.count_lines.return_value = 5

        mock_analyzer = mock_analyzer_cls.return_value
        mock_analyzer.analyze.return_value = _make_result()

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("line\n" * 5)
            result = runner.invoke(cli, [
                "analyze", "test.log", "--report", "html",
                "--output", "report.html", "--no-threading",
            ])
            assert result.exit_code == 0

    @patch('log_analyzer.cli.LogAnalyzer')
    @patch('log_analyzer.reader.LogReader')
    def test_analyze_csv_report(self, mock_reader_cls, mock_analyzer_cls, runner):
        """Analyze generating CSV report."""
        mock_reader = mock_reader_cls.return_value
        mock_reader.count_lines.return_value = 5

        mock_analyzer = mock_analyzer_cls.return_value
        mock_analyzer.analyze.return_value = _make_result()

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("line\n" * 5)
            result = runner.invoke(cli, [
                "analyze", "test.log", "--report", "csv",
                "--output", "report.csv", "--no-threading",
            ])
            assert result.exit_code == 0

    @patch('log_analyzer.cli.LogAnalyzer')
    @patch('log_analyzer.reader.LogReader')
    def test_analyze_report_to_console(self, mock_reader_cls, mock_analyzer_cls, runner):
        """Analyze with --report but no --output prints to console."""
        mock_reader = mock_reader_cls.return_value
        mock_reader.count_lines.return_value = 5

        mock_analyzer = mock_analyzer_cls.return_value
        mock_analyzer.analyze.return_value = _make_result()

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("line\n" * 5)
            result = runner.invoke(cli, [
                "analyze", "test.log", "--report", "json", "--no-threading",
            ])
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# detect command
# ---------------------------------------------------------------------------

class TestDetectCommand:
    @patch('log_analyzer.cli.LogAnalyzer')
    def test_detect_success(self, mock_analyzer_cls, runner):
        mock_parser = MagicMock()
        mock_parser.name = "json"
        mock_analyzer_cls.return_value.detect_format.return_value = mock_parser

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write('{"level": "info"}\n')
            result = runner.invoke(cli, ["detect", "test.log"])
            assert result.exit_code == 0
            assert "json" in result.output

    @patch('log_analyzer.cli.LogAnalyzer')
    def test_detect_unknown(self, mock_analyzer_cls, runner):
        mock_analyzer_cls.return_value.detect_format.return_value = None

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("random stuff\n")
            result = runner.invoke(cli, ["detect", "test.log"])
            assert result.exit_code != 0


# ---------------------------------------------------------------------------
# errors command
# ---------------------------------------------------------------------------

class TestErrorsCommand:
    @patch('log_analyzer.cli.LogAnalyzer')
    def test_errors_shows_entries(self, mock_analyzer_cls, runner):
        from log_analyzer.parsers import LogEntry
        entries = [
            LogEntry(timestamp=datetime(2020, 1, 1, 12, 0), level="ERROR", message="Crash"),
            LogEntry(timestamp=datetime(2020, 1, 1, 12, 1), level="WARNING", message="Slow"),
            LogEntry(timestamp=None, level="INFO", message="OK"),
        ]
        mock_analyzer_cls.return_value.parse_file.return_value = iter(entries)

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("dummy\n")
            result = runner.invoke(cli, ["errors", "test.log", "--level", "ERROR"])
            assert result.exit_code == 0
            assert "Crash" in result.output

    @patch('log_analyzer.cli.LogAnalyzer')
    def test_errors_no_matches(self, mock_analyzer_cls, runner):
        from log_analyzer.parsers import LogEntry
        entries = [
            LogEntry(timestamp=None, level="INFO", message="all good"),
        ]
        mock_analyzer_cls.return_value.parse_file.return_value = iter(entries)

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("dummy\n")
            result = runner.invoke(cli, ["errors", "test.log", "--level", "CRITICAL"])
            assert result.exit_code == 0
            assert "No entries" in result.output

    @patch('log_analyzer.cli.LogAnalyzer')
    def test_errors_with_limit(self, mock_analyzer_cls, runner):
        from log_analyzer.parsers import LogEntry
        entries = [
            LogEntry(timestamp=datetime(2020, 1, 1, 12, i), level="ERROR", message=f"Error {i}")
            for i in range(30)
        ]
        mock_analyzer_cls.return_value.parse_file.return_value = iter(entries)

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("dummy\n")
            result = runner.invoke(cli, ["errors", "test.log", "--limit", "5"])
            assert result.exit_code == 0
            assert "showing first 5" in result.output


# ---------------------------------------------------------------------------
# formats command
# ---------------------------------------------------------------------------

class TestFormatsCommand:
    def test_formats_lists(self, runner):
        result = runner.invoke(cli, ["formats"])
        assert result.exit_code == 0
        assert "Supported Log Formats" in result.output


# ---------------------------------------------------------------------------
# configure command
# ---------------------------------------------------------------------------

class TestConfigureCommand:
    @patch('log_analyzer.cli.get_provider_status', create=True)
    def test_configure_show(self, mock_status, runner):
        mock_status.return_value = {
            "anthropic": {"enabled": True, "model": "claude-sonnet-4-5-20250929",
                          "configured": False, "api_key_display": "(not set)"},
            "gemini": {"enabled": True, "model": "gemini-2.5-flash",
                       "configured": False, "api_key_display": "(not set)"},
            "ollama": {"enabled": True, "model": "llama3",
                       "configured": False, "api_key_display": "N/A",
                       "server_available": False},
        }
        result = runner.invoke(cli, ["configure", "--show"])
        assert result.exit_code == 0
        assert "Provider" in result.output or "Configuration" in result.output


# ---------------------------------------------------------------------------
# triage command
# ---------------------------------------------------------------------------

class TestTriageCommand:
    @patch('log_analyzer.triage.TriageEngine', create=True)
    def test_triage_success(self, mock_engine_cls, runner):
        """Test triage command with --json to validate the full pipeline."""
        mock_engine = mock_engine_cls.return_value

        mock_provider = MagicMock()
        mock_provider.name = "anthropic"
        mock_provider.get_model.return_value = "claude-sonnet-4-5-20250929"
        mock_engine._get_provider.return_value = mock_provider

        triage_result = MagicMock()
        triage_result.summary = "Analysis complete"
        triage_result.overall_severity = MagicMock()
        triage_result.overall_severity.value = "high"
        triage_result.confidence = 0.85
        triage_result.issues = []
        triage_result.analyzed_lines = 100
        triage_result.error_count = 5
        triage_result.warning_count = 10
        triage_result.analysis_time_ms = 1500.0
        triage_result.to_dict.return_value = {"summary": "Analysis complete", "issues": []}
        mock_engine.triage.return_value = triage_result

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("error log content\n")
            result = runner.invoke(cli, ["triage", "test.log", "--json"])
            assert result.exit_code == 0
            assert "Analysis complete" in result.output

    @patch('log_analyzer.triage.TriageEngine', create=True)
    def test_triage_json_output(self, mock_engine_cls, runner):
        mock_engine = mock_engine_cls.return_value

        mock_provider = MagicMock()
        mock_provider.name = "anthropic"
        mock_provider.get_model.return_value = "claude"
        mock_engine._get_provider.return_value = mock_provider

        triage_result = MagicMock()
        triage_result.summary = "test"
        triage_result.overall_severity = MagicMock()
        triage_result.overall_severity.value = "low"
        triage_result.confidence = 0.5
        triage_result.issues = []
        triage_result.to_dict.return_value = {"summary": "test"}
        mock_engine.triage.return_value = triage_result

        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write("test\n")
            result = runner.invoke(cli, ["triage", "test.log", "--json"])
            assert result.exit_code == 0
            assert "summary" in result.output

    def test_triage_file_not_found(self, runner):
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["triage", "nonexistent.log"])
            assert result.exit_code != 0
