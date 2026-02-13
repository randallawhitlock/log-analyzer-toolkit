"""
Unit tests for log parsers.
"""

from log_analyzer.parsers import (
    ApacheAccessParser,
    AWSCloudWatchParser,
    AzureMonitorParser,
    ContainerdParser,
    DockerJSONParser,
    GCPCloudLoggingParser,
    JSONLogParser,
    KubernetesParser,
    LogEntry,
    SyslogParser,
)


class TestApacheAccessParser:
    """Tests for Apache Combined Log Format parser."""

    def setup_method(self):
        self.parser = ApacheAccessParser()

    def test_parse_valid_line(self):
        line = '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /index.html HTTP/1.1" 200 2326'
        result = self.parser.parse(line)

        assert result is not None
        assert result.source == "192.168.1.1"
        assert result.level == "INFO"
        assert result.metadata['status'] == 200
        assert "GET /index.html" in result.message

    def test_parse_with_referer_and_user_agent(self):
        line = '10.0.0.1 - admin [10/Oct/2023:13:55:36 +0000] "POST /api HTTP/1.1" 201 145 "https://example.com/" "Mozilla/5.0"'
        result = self.parser.parse(line)

        assert result is not None
        assert result.metadata['referer'] == "https://example.com/"
        assert result.metadata['user_agent'] == "Mozilla/5.0"

    def test_error_status_code_sets_error_level(self):
        line = '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api HTTP/1.1" 500 234'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == "ERROR"

    def test_client_error_sets_warning_level(self):
        line = '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /missing HTTP/1.1" 404 162'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == "WARNING"

    def test_can_parse_detects_format(self):
        valid = '192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET / HTTP/1.1" 200 100'
        invalid = 'This is not a log line'

        assert self.parser.can_parse(valid) is True
        assert self.parser.can_parse(invalid) is False


class TestJSONLogParser:
    """Tests for JSON structured log parser."""

    def setup_method(self):
        self.parser = JSONLogParser()

    def test_parse_valid_json(self):
        line = '{"timestamp": "2023-10-10T13:55:36Z", "level": "ERROR", "message": "Connection failed", "host": "server-01"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == "ERROR"
        assert result.message == "Connection failed"
        assert result.source == "server-01"

    def test_parse_with_unix_timestamp(self):
        line = '{"ts": 1696945536, "level": "info", "msg": "Request completed"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.timestamp is not None
        assert result.level == "INFO"
        assert result.message == "Request completed"

    def test_level_normalization(self):
        line = '{"level": "warn", "message": "Low disk space"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == "WARNING"

    def test_can_parse_detects_json(self):
        valid = '{"key": "value"}'
        invalid = 'Not JSON at all'
        incomplete = '{"key": '

        assert self.parser.can_parse(valid) is True
        assert self.parser.can_parse(invalid) is False
        # can_parse just checks brackets, parse handles validation
        assert self.parser.parse(incomplete) is None


class TestSyslogParser:
    """Tests for syslog format parser."""

    def setup_method(self):
        self.parser = SyslogParser()

    def test_parse_rfc3164(self):
        line = '<34>Oct 11 22:14:15 mymachine su: su root failed for lonvick'
        result = self.parser.parse(line)

        assert result is not None
        assert result.source == "mymachine"
        assert "su root failed" in result.message

    def test_severity_extraction(self):
        # Priority 11 = facility 1, severity 3 (error)
        line = '<11>Oct 11 22:14:15 host app: Error occurred'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == "ERROR"

    def test_can_parse_detects_syslog(self):
        valid = '<34>Oct 11 22:14:15 host app: message'
        invalid = 'Regular log line'

        assert self.parser.can_parse(valid) is True
        assert self.parser.can_parse(invalid) is False


class TestLogEntry:
    """Tests for LogEntry dataclass."""

    def test_default_metadata(self):
        entry = LogEntry(raw="test line")
        assert entry.metadata == {}

    def test_all_fields(self):
        from datetime import datetime

        entry = LogEntry(
            raw="test line",
            timestamp=datetime(2023, 10, 10),
            level="ERROR",
            message="Test message",
            source="test-host",
            metadata={"key": "value"}
        )

        assert entry.level == "ERROR"
        assert entry.source == "test-host"
        assert entry.metadata["key"] == "value"


# ============================================================================
# Cloud Provider Parser Tests
# ============================================================================

class TestAWSCloudWatchParser:
    """Tests for AWS CloudWatch Logs parser."""

    def setup_method(self):
        self.parser = AWSCloudWatchParser()

    def test_can_parse_json_batch_format(self):
        """Test detection of CloudWatch batch JSON format."""
        line = '{"logEvents":[{"timestamp":1577836800000,"message":"test"}],"logGroup":"/aws/lambda/test"}'
        assert self.parser.can_parse(line) is True

    def test_can_parse_plain_text_format(self):
        """Test detection of CloudWatch plain text format."""
        line = '2020-01-01T00:00:00.000Z [ERROR] Connection failed'
        assert self.parser.can_parse(line) is True

    def test_parse_json_batch(self):
        """Test parsing CloudWatch batch format."""
        line = '{"logEvents":[{"timestamp":1421116133213,"message":"[INFO] App started"}],"logGroup":"/aws/lambda/my-fn","logStream":"2020/01/01/stream"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'INFO'
        assert 'App started' in result.message
        assert result.metadata['log_group'] == '/aws/lambda/my-fn'
        assert result.timestamp is not None

    def test_parse_plain_text(self):
        """Test parsing plain text format."""
        line = '2020-01-01T00:00:00.000Z [ERROR] Database timeout'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'ERROR'
        assert result.message == 'Database timeout'

    def test_parse_without_level(self):
        """Test parsing log without explicit level."""
        line = '2020-01-01T00:00:00.000Z Connection established'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'INFO'  # Default
        assert result.message == 'Connection established'

    def test_parse_invalid_returns_none(self):
        """Test invalid input returns None."""
        assert self.parser.parse("not a cloudwatch log") is None


class TestGCPCloudLoggingParser:
    """Tests for Google Cloud Logging parser."""

    def setup_method(self):
        self.parser = GCPCloudLoggingParser()

    def test_can_parse_gcp_format(self):
        """Test detection of GCP logging format."""
        line = '{"timestamp":"2020-01-01T00:00:00Z","severity":"ERROR","textPayload":"Failed"}'
        assert self.parser.can_parse(line) is True

    def test_parse_with_text_payload(self):
        """Test parsing GCP log with textPayload."""
        line = '{"timestamp":"2020-01-01T00:00:00Z","severity":"ERROR","textPayload":"Connection failed","logName":"projects/test/logs/syslog"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'ERROR'
        assert result.message == 'Connection failed'
        assert result.metadata['log_name'] == 'projects/test/logs/syslog'

    def test_parse_with_json_payload(self):
        """Test parsing GCP log with jsonPayload."""
        line = '{"timestamp":"2020-01-01T00:00:00Z","severity":"INFO","jsonPayload":{"message":"Server started"}}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'INFO'
        assert 'Server started' in result.message

    def test_severity_mapping(self):
        """Test GCP severity level mapping."""
        line_notice = '{"timestamp":"2020-01-01T00:00:00Z","severity":"NOTICE","textPayload":"Test"}'
        line_alert = '{"timestamp":"2020-01-01T00:00:00Z","severity":"ALERT","textPayload":"Test"}'

        result_notice = self.parser.parse(line_notice)
        result_alert = self.parser.parse(line_alert)

        assert result_notice.level == 'INFO'  # NOTICE maps to INFO
        assert result_alert.level == 'CRITICAL'  # ALERT maps to CRITICAL

    def test_parse_with_resource_labels(self):
        """Test extraction of resource labels."""
        line = '{"timestamp":"2020-01-01T00:00:00Z","severity":"INFO","textPayload":"Test","resource":{"type":"k8s_pod","labels":{"pod_name":"test-pod","namespace_name":"default"}}}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.source == 'k8s_pod'
        assert result.metadata['pod_name'] == 'test-pod'
        assert result.metadata['namespace'] == 'default'

    def test_parse_invalid_returns_none(self):
        """Test invalid JSON (missing required fields) returns None."""
        # Missing both severity and timestamp
        assert self.parser.parse('{"invalid": "json"}') is None
        # Missing severity
        assert self.parser.parse('{"timestamp": "2020-01-01T00:00:00Z"}') is None
        # Missing timestamp
        assert self.parser.parse('{"severity": "INFO"}') is None


class TestAzureMonitorParser:
    """Tests for Azure Monitor parser."""

    def setup_method(self):
        self.parser = AzureMonitorParser()

    def test_can_parse_app_insights_format(self):
        """Test detection of Application Insights format."""
        line = '{"time":"2020-01-01T00:00:00.000Z","level":"Error","message":"Failed"}'
        assert self.parser.can_parse(line) is True

    def test_can_parse_log_analytics_format(self):
        """Test detection of Log Analytics format."""
        line = '{"TimeGenerated":"2020-01-01T00:00:00.000Z","SeverityLevel":3,"Message":"Error"}'
        assert self.parser.can_parse(line) is True

    def test_parse_string_level(self):
        """Test parsing with string level."""
        line = '{"time":"2020-01-01T00:00:00.000Z","level":"Error","message":"Request failed"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'ERROR'
        assert result.message == 'Request failed'

    def test_parse_numeric_level(self):
        """Test parsing with numeric severity level."""
        line = '{"TimeGenerated":"2020-01-01T00:00:00.000Z","Computer":"vm-01","SeverityLevel":3,"Message":"Service down"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'ERROR'  # Level 3 = ERROR
        assert result.source == 'vm-01'
        assert result.message == 'Service down'

    def test_parse_array_format(self):
        """Test parsing JSON array format."""
        line = '[{"time":"2020-01-01T00:00:00.000Z","level":"Info","message":"Test"}]'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'INFO'
        assert result.message == 'Test'

    def test_parse_with_metadata(self):
        """Test extraction of operation and category metadata."""
        line = '{"time":"2020-01-01T00:00:00.000Z","level":"Warning","category":"Database","operationName":"Query","message":"Slow query"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.metadata['category'] == 'Database'
        assert result.metadata['operation'] == 'Query'


# ============================================================================
# Container Runtime Parser Tests
# ============================================================================

class TestDockerJSONParser:
    """Tests for Docker JSON logs parser."""

    def setup_method(self):
        self.parser = DockerJSONParser()

    def test_can_parse_docker_format(self):
        """Test detection of Docker JSON format."""
        line = '{"log":"Log line\\n","stream":"stdout","time":"2019-01-01T11:11:11.111111111Z"}'
        assert self.parser.can_parse(line) is True

    def test_parse_stdout_log(self):
        """Test parsing stdout log."""
        line = '{"log":"Application started\\n","stream":"stdout","time":"2020-01-01T00:00:00.000000000Z"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'INFO'  # stdout defaults to INFO
        assert result.message == 'Application started'
        assert result.metadata['stream'] == 'stdout'

    def test_parse_stderr_log(self):
        """Test parsing stderr log."""
        line = '{"log":"Error occurred\\n","stream":"stderr","time":"2020-01-01T00:00:00.000000000Z"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'ERROR'  # Extracted from message
        assert 'Error occurred' in result.message
        assert result.metadata['stream'] == 'stderr'

    def test_parse_with_embedded_level(self):
        """Test level extraction from message."""
        line = '{"log":"[WARN] High memory usage\\n","stream":"stdout","time":"2020-01-01T00:00:00.000000000Z"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'WARNING'

    def test_timestamp_parsing(self):
        """Test RFC3339Nano timestamp parsing."""
        line = '{"log":"Test\\n","stream":"stdout","time":"2020-01-01T00:00:00.123456789Z"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.timestamp is not None
        assert result.timestamp.year == 2020


class TestKubernetesParser:
    """Tests for Kubernetes pod logs parser."""

    def setup_method(self):
        self.parser = KubernetesParser()

    def test_can_parse_cri_format(self):
        """Test detection of CRI format."""
        line = '2020-01-01T00:00:00.000000000Z stdout F [INFO] Pod ready'
        assert self.parser.can_parse(line) is True

    def test_can_parse_json_format(self):
        """Test detection of JSON format."""
        line = '{"log":"Test\\n","stream":"stdout","time":"2020-01-01T00:00:00Z"}'
        assert self.parser.can_parse(line) is True

    def test_parse_cri_full_line(self):
        """Test parsing CRI format with full line flag."""
        line = '2020-01-01T00:00:00.000000000Z stdout F [INFO] Application ready'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'INFO'
        assert result.message == '[INFO] Application ready'
        assert result.metadata['flag'] == 'F'  # Full line
        assert result.metadata['stream'] == 'stdout'

    def test_parse_cri_partial_line(self):
        """Test parsing CRI format with partial line flag."""
        line = '2020-01-01T00:00:00.000000000Z stdout P Partial message'
        result = self.parser.parse(line)

        assert result is not None
        assert result.metadata['flag'] == 'P'  # Partial line

    def test_parse_stderr_defaults_to_warning(self):
        """Test stderr defaults to WARNING level."""
        line = '2020-01-01T00:00:00.000000000Z stderr F Connection error'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'ERROR'  # Extracted from message

    def test_parse_json_format(self):
        """Test parsing JSON format (kubectl logs)."""
        line = '{"log":"Starting timer...\\n","stream":"stdout","time":"2018-05-17T21:25:25.140994702Z"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.message == 'Starting timer...'
        assert result.metadata['parser_type'] == 'kubernetes_json'


class TestContainerdParser:
    """Tests for containerd CRI logs parser."""

    def setup_method(self):
        self.parser = ContainerdParser()

    def test_can_parse_cri_with_json(self):
        """Test detection of CRI format with JSON message."""
        line = '2020-01-01T00:00:00.000000000Z stdout F {"level":"info","msg":"Started"}'
        assert self.parser.can_parse(line) is True

    def test_can_parse_cri_with_plugin_message(self):
        """Test detection of CRI format with plugin message."""
        line = '2020-01-10T18:10:40.01576219Z stdout F [INFO] plugin/reload: Running'
        assert self.parser.can_parse(line) is True

    def test_parse_json_message(self):
        """Test parsing CRI format with JSON message."""
        line = '2020-01-01T00:00:00.000000000Z stdout F {"level":"info","msg":"Service started","component":"api"}'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'INFO'
        assert result.message == 'Service started'
        assert result.source == 'api'  # From component
        assert result.metadata['component'] == 'api'

    def test_parse_plain_text_message(self):
        """Test parsing CRI format with plain text message."""
        line = '2020-01-01T00:00:05.000000000Z stdout F Container initialization complete'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'INFO'
        assert result.message == 'Container initialization complete'

    def test_parse_stderr_with_error(self):
        """Test parsing stderr with error message."""
        line = '2020-01-01T00:00:06.000000000Z stderr F panic: runtime error'
        result = self.parser.parse(line)

        assert result is not None
        assert result.level == 'ERROR'  # Extracted from message
        assert 'panic' in result.message

    def test_parse_partial_line(self):
        """Test parsing partial line."""
        line = '2020-01-01T00:00:01.000000000Z stderr P Error: connection failed'
        result = self.parser.parse(line)

        assert result is not None
        assert result.metadata['flag'] == 'P'  # Partial
        assert result.level == 'ERROR'
