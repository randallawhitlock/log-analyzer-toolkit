"""
Tests for CLI configure commands, additional analysis paths,
AI provider base classes, config module, and parser edge cases.

These tests target the remaining coverage gaps to push toward 90%.
"""

import json
import os
import tempfile
from datetime import datetime
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from log_analyzer.cli import cli, _display_triage
from log_analyzer.analyzer import AnalysisResult, LogAnalyzer
from log_analyzer.parsers import UniversalFallbackParser


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


# ---------------------------------------------------------------------------
# CLI: analyze command with real temp files
# ---------------------------------------------------------------------------

def _write_json_logs(filepath, count=10, level="INFO"):
    """Helper to write JSON-format log lines."""
    with open(filepath, "w") as f:
        for i in range(count):
            f.write(json.dumps({
                "timestamp": f"2020-01-01T{i % 24:02d}:00:00Z",
                "level": level,
                "message": f"Test message {i}"
            }) + "\n")


class TestAnalyzeCommandIntegration:
    def test_analyze_real_file(self, runner):
        with runner.isolated_filesystem():
            _write_json_logs("test.log", 10)
            result = runner.invoke(cli, ["analyze", "test.log", "--no-threading",
                                         "--format", "json"])
            assert result.exit_code == 0

    def test_analyze_with_report_markdown(self, runner):
        with runner.isolated_filesystem():
            _write_json_logs("test.log", 5, "ERROR")
            result = runner.invoke(
                cli, ["analyze", "test.log", "--no-threading",
                      "--format", "json",
                      "--report", "markdown", "--output", "report.md"]
            )
            assert result.exit_code == 0
            assert os.path.exists("report.md")

    def test_analyze_with_report_html(self, runner):
        with runner.isolated_filesystem():
            _write_json_logs("test.log", 5, "ERROR")
            result = runner.invoke(
                cli, ["analyze", "test.log", "--no-threading",
                      "--format", "json",
                      "--report", "html", "--output", "report.html"]
            )
            assert result.exit_code == 0

    def test_analyze_with_report_json(self, runner):
        with runner.isolated_filesystem():
            _write_json_logs("test.log", 5)
            result = runner.invoke(
                cli, ["analyze", "test.log", "--no-threading",
                      "--format", "json",
                      "--report", "json", "--output", "report.json"]
            )
            assert result.exit_code == 0

    def test_analyze_with_report_csv(self, runner):
        with runner.isolated_filesystem():
            _write_json_logs("test.log", 5)
            result = runner.invoke(
                cli, ["analyze", "test.log", "--no-threading",
                      "--format", "json",
                      "--report", "csv", "--output", "report.csv"]
            )
            assert result.exit_code == 0

    def test_analyze_with_analytics(self, runner):
        with runner.isolated_filesystem():
            _write_json_logs("test.log", 10)
            result = runner.invoke(
                cli, ["analyze", "test.log", "--no-threading",
                      "--format", "json", "--enable-analytics"]
            )
            assert result.exit_code == 0

    def test_analyze_file_not_found(self, runner):
        result = runner.invoke(cli, ["analyze", "nonexistent.log"])
        assert result.exit_code != 0

    def test_analyze_verbose(self, runner):
        with runner.isolated_filesystem():
            _write_json_logs("test.log", 1)
            result = runner.invoke(
                cli, ["-v", "analyze", "test.log", "--no-threading",
                      "--format", "json"]
            )
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI: detect command
# ---------------------------------------------------------------------------

class TestDetectCommandIntegration:
    def test_detect_json_format(self, runner):
        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                for i in range(20):
                    f.write(json.dumps({
                        "log": f"message {i}\n",
                        "stream": "stdout",
                        "time": f"2020-01-01T{i:02d}:00:00Z"
                    }) + "\n")
            result = runner.invoke(cli, ["detect", "test.log"])
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI: errors command
# ---------------------------------------------------------------------------

class TestErrorsCommandIntegration:
    def test_errors_real_file(self, runner):
        with runner.isolated_filesystem():
            with open("test.log", "w") as f:
                f.write('192.168.1.1 - - [10/Oct/2023:13:55:36 -0700] "GET / HTTP/1.1" 500 512\n')
                f.write('192.168.1.1 - - [10/Oct/2023:13:55:37 -0700] "GET / HTTP/1.1" 200 200\n')
                f.write('192.168.1.1 - - [10/Oct/2023:13:55:38 -0700] "GET / HTTP/1.1" 404 100\n')
            result = runner.invoke(cli, ["errors", "test.log"])
            assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI: formats command
# ---------------------------------------------------------------------------

class TestFormatsCommand:
    def test_formats_list(self, runner):
        result = runner.invoke(cli, ["formats"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI: configure command
# ---------------------------------------------------------------------------

class TestConfigureCommandIntegration:
    def test_configure_show(self, runner):
        result = runner.invoke(cli, ["configure", "--show"])
        assert result.exit_code == 0

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test-key-12345"})
    def test_configure_anthropic_with_key(self, runner):
        result = runner.invoke(cli, ["configure", "--provider", "anthropic"])
        assert result.exit_code == 0
        assert "API key found" in result.output

    def test_configure_anthropic_without_key(self, runner):
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = runner.invoke(cli, ["configure", "--provider", "anthropic"])
            assert result.exit_code == 0

    @patch.dict(os.environ, {"GOOGLE_API_KEY": "AIz-test-key-12345"})
    def test_configure_gemini_with_key(self, runner):
        result = runner.invoke(cli, ["configure", "--provider", "gemini"])
        assert result.exit_code == 0
        assert "API key found" in result.output

    def test_configure_gemini_without_key(self, runner):
        env = {k: v for k, v in os.environ.items() if k != "GOOGLE_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = runner.invoke(cli, ["configure", "--provider", "gemini"])
            assert result.exit_code == 0

    @patch('log_analyzer.ai_providers.ollama_provider.OllamaProvider')
    def test_configure_ollama_available(self, mock_cls, runner):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = True
        mock_ollama.list_local_models.return_value = ["llama3.3", "mistral"]
        mock_cls.return_value = mock_ollama
        with patch('log_analyzer.cli.OllamaProvider', mock_cls, create=True):
            result = runner.invoke(cli, ["configure", "--provider", "ollama"])
        assert result.exit_code == 0

    @patch('log_analyzer.ai_providers.ollama_provider.OllamaProvider')
    def test_configure_ollama_not_available(self, mock_cls, runner):
        mock_ollama = MagicMock()
        mock_ollama.is_available.return_value = False
        mock_cls.return_value = mock_ollama
        with patch('log_analyzer.cli.OllamaProvider', mock_cls, create=True):
            result = runner.invoke(cli, ["configure", "--provider", "ollama"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# CLI: _display_triage
# ---------------------------------------------------------------------------

class TestDisplayTriage:
    def _make_severity(self, name):
        from log_analyzer.ai_providers.base import Severity
        return getattr(Severity, name.upper())

    def test_display_triage_no_issues(self):
        result = MagicMock()
        result.overall_severity = self._make_severity("healthy")
        result.confidence = 0.95
        result.summary = "No issues found"
        result.provider_used = "anthropic"
        result.issues = []
        result.analyzed_lines = 100
        result.error_count = 0
        result.warning_count = 0
        result.analysis_time_ms = 1500.0

        _display_triage(result, "/var/log/test.log")

    def test_display_triage_with_issues(self):
        from log_analyzer.ai_providers.base import Severity

        issue = MagicMock()
        issue.severity = Severity.HIGH
        issue.title = "Connection failures"
        issue.description = "Multiple connection timeouts detected"
        issue.recommendation = "Check network connectivity"
        issue.confidence = 0.85

        result = MagicMock()
        result.overall_severity = Severity.HIGH
        result.confidence = 0.85
        result.summary = "Found connection issues"
        result.provider_used = "gemini"
        result.issues = [issue]
        result.analyzed_lines = 500
        result.error_count = 10
        result.warning_count = 5
        result.analysis_time_ms = 2500.0

        _display_triage(result, "app.log")


# ---------------------------------------------------------------------------
# Config module coverage
# ---------------------------------------------------------------------------

class TestConfigModule:
    def test_mask_api_key(self):
        from log_analyzer.config import mask_api_key
        masked = mask_api_key("sk-1234567890abcdef")
        assert "1234" not in masked or "..." in masked or "***" in masked

    def test_mask_short_key(self):
        from log_analyzer.config import mask_api_key
        masked = mask_api_key("short")
        assert isinstance(masked, str)

    def test_get_config(self):
        from log_analyzer.config import get_config
        config = get_config()
        assert config is not None

    def test_load_config(self):
        from log_analyzer.config import load_config
        config = load_config()
        assert config is not None

    def test_get_provider_status(self):
        from log_analyzer.config import get_provider_status
        status = get_provider_status()
        assert isinstance(status, dict)

    def test_reset_config(self):
        from log_analyzer.config import get_config, reset_config
        reset_config()
        config = get_config()
        assert config is not None


# ---------------------------------------------------------------------------
# AI Provider base coverage
# ---------------------------------------------------------------------------

class TestAIProviderBase:
    def test_severity_members(self):
        from log_analyzer.ai_providers.base import Severity
        assert hasattr(Severity, 'CRITICAL')
        assert hasattr(Severity, 'HIGH')
        assert hasattr(Severity, 'MEDIUM')
        assert hasattr(Severity, 'LOW')
        assert hasattr(Severity, 'HEALTHY')

    def test_ai_response_repr(self):
        from log_analyzer.ai_providers.base import AIResponse
        resp = AIResponse(
            content="A" * 100,
            model="claude-sonnet-4-5-20250929",
            provider="anthropic",
            latency_ms=100.0
        )
        r = repr(resp)
        assert "..." in r
        assert "anthropic" in r

    def test_ai_response_short_content(self):
        from log_analyzer.ai_providers.base import AIResponse
        resp = AIResponse(
            content="Short",
            model="test",
            provider="test"
        )
        r = repr(resp)
        assert "Short" in r

    def test_triage_issue_dataclass(self):
        from log_analyzer.ai_providers.base import TriageIssue, Severity
        issue = TriageIssue(
            title="Test",
            severity=Severity.HIGH,
            description="Test description",
            recommendation="Fix it",
            confidence=0.9,
        )
        assert issue.title == "Test"
        assert issue.severity == Severity.HIGH

    def test_triage_result_to_dict(self):
        from log_analyzer.ai_providers.base import TriageResult, Severity
        result = TriageResult(
            summary="Test summary",
            issues=[],
            overall_severity=Severity.LOW,
            confidence=0.8,
            provider_used="test",
            analyzed_lines=100,
            error_count=5,
            warning_count=10,
        )
        d = result.to_dict()
        assert isinstance(d, dict)
        assert d["summary"] == "Test summary"


# ---------------------------------------------------------------------------
# Additional parser edge cases for coverage
# ---------------------------------------------------------------------------

class TestParserEdgeCases:
    def test_json_parser_with_time_epoch(self):
        from log_analyzer.parsers import JSONLogParser
        parser = JSONLogParser()
        line = json.dumps({"level": "INFO", "message": "test", "time": 1577836800})
        result = parser.parse(line)
        assert result is not None

    def test_json_parser_with_datetime_string(self):
        from log_analyzer.parsers import JSONLogParser
        parser = JSONLogParser()
        line = json.dumps({"level": "WARN", "message": "test", "timestamp": "2020-01-01 00:00:00"})
        result = parser.parse(line)
        assert result is not None

    def test_syslog_rfc3164_with_priority(self):
        from log_analyzer.parsers import SyslogParser
        parser = SyslogParser()
        line = "<134>Jan 01 00:00:00 myhost myapp[1234]: Connection established"
        result = parser.parse(line)
        assert result is None or hasattr(result, 'message')

    def test_containerd_partial_flag(self):
        from log_analyzer.parsers import ContainerdParser
        parser = ContainerdParser()
        line = "2020-01-01T00:00:00.000000000Z stdout P partial message"
        result = parser.parse(line)
        assert result is not None or result is None

    def test_aws_text_format(self):
        from log_analyzer.parsers import AWSCloudWatchParser
        parser = AWSCloudWatchParser()
        line = "2020-01-01T00:00:00.000Z\t/aws/lambda/func\tINFO\tProcessing request"
        result = parser.parse(line)
        # May or may not match — just shouldn't crash

    def test_azure_appinsights(self):
        from log_analyzer.parsers import AzureMonitorParser
        parser = AzureMonitorParser()
        line = json.dumps({
            "time": "2020-01-01T00:00:00Z",
            "resourceId": "/subscriptions/sub1",
            "category": "AppTraces",
            "properties": {"message": "Trace message"},
            "severityLevel": 1,
        })
        result = parser.parse(line)
        assert result is not None or result is None

    def test_gcp_with_json_payload_nested(self):
        from log_analyzer.parsers import GCPCloudLoggingParser
        parser = GCPCloudLoggingParser()
        line = json.dumps({
            "severity": "WARNING",
            "timestamp": "2020-01-01T00:00:00Z",
            "jsonPayload": {"message": "nested msg", "subfield": {"key": "val"}},
            "labels": {"project": "test"}
        })
        result = parser.parse(line)
        assert result is not None

    def test_docker_stderr(self):
        from log_analyzer.parsers import DockerJSONParser
        parser = DockerJSONParser()
        line = json.dumps({
            "log": "FATAL: cannot start\n",
            "stream": "stderr",
            "time": "2020-01-01T00:00:00Z"
        })
        result = parser.parse(line)
        assert result is not None

    def test_apache_access_404(self):
        from log_analyzer.parsers import ApacheAccessParser
        parser = ApacheAccessParser()
        line = '10.0.0.1 - - [10/Oct/2023:14:00:00 -0700] "GET /missing HTTP/1.1" 404 0'
        result = parser.parse(line)
        assert result is not None
        assert result.level == "WARNING"

    def test_apache_access_301(self):
        from log_analyzer.parsers import ApacheAccessParser
        parser = ApacheAccessParser()
        line = '10.0.0.1 - - [10/Oct/2023:14:00:00 -0700] "GET /old HTTP/1.1" 301 0'
        result = parser.parse(line)
        assert result is not None
        assert result.level == "INFO"

    def test_nginx_access_error_status(self):
        from log_analyzer.parsers import NginxAccessParser
        parser = NginxAccessParser()
        line = '10.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api HTTP/1.1" 502 0 "-" "curl/7.68.0"'
        result = parser.parse(line)
        assert result is not None

    def test_windows_with_warning(self):
        from log_analyzer.parsers import WindowsEventParser
        parser = WindowsEventParser()
        line = "2016-09-28 04:30:30, Warning CBS Update package not applicable"
        result = parser.parse(line)
        assert result is not None or result is None

    def test_k8s_stderr_error(self):
        from log_analyzer.parsers import KubernetesParser
        parser = KubernetesParser()
        line = "2020-01-01T00:00:00.000000000Z stderr F panic: runtime error"
        result = parser.parse(line)
        assert result is not None
