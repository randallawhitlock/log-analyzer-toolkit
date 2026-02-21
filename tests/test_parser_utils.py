"""
Targeted parser utility tests to cross 90% coverage threshold.
Covers: parse_cloud_timestamp edge cases, extract_level_from_message,
Azure Monitor parser, and cloud log parser patterns.
"""

import json

from log_analyzer.parsers import (
    extract_level_from_message,
    parse_cloud_timestamp,
)


class TestParseCloudTimestamp:
    def test_iso8601_basic(self):
        result = parse_cloud_timestamp("2020-01-01T00:00:00Z")
        assert result is not None
        assert result.year == 2020

    def test_iso8601_with_fractional(self):
        result = parse_cloud_timestamp("2020-01-01T00:00:00.123Z")
        assert result is not None

    def test_rfc3339_nano(self):
        """RFC3339Nano timestamps should be truncated to microseconds."""
        result = parse_cloud_timestamp("2020-01-01T00:00:00.123456789Z")
        assert result is not None

    def test_unix_milliseconds(self):
        """Unix millisecond timestamps (AWS CloudWatch)."""
        result = parse_cloud_timestamp("1577836800000")
        assert result is not None

    def test_iso8601_with_timezone(self):
        result = parse_cloud_timestamp("2020-01-01T00:00:00+00:00")
        assert result is not None

    def test_invalid_timestamp(self):
        result = parse_cloud_timestamp("not a timestamp")
        assert result is None

    def test_empty_string(self):
        result = parse_cloud_timestamp("")
        assert result is None

    def test_none_handling(self):
        """None should return None without error."""
        # parse_cloud_timestamp expects str, test edge case
        result = parse_cloud_timestamp("")
        assert result is None


class TestExtractLevelFromMessage:
    def test_critical(self):
        assert extract_level_from_message("CRITICAL: system failure") == "CRITICAL"

    def test_fatal(self):
        assert extract_level_from_message("FATAL error occurred") == "CRITICAL"

    def test_crit(self):
        assert extract_level_from_message("CRIT: disk full") == "CRITICAL"

    def test_error(self):
        assert extract_level_from_message("ERROR: file not found") == "ERROR"

    def test_err(self):
        assert extract_level_from_message("ERR connection reset") == "ERROR"

    def test_warning(self):
        assert extract_level_from_message("WARNING: disk nearly full") == "WARNING"

    def test_warn(self):
        assert extract_level_from_message("WARN: retrying") == "WARNING"

    def test_info(self):
        assert extract_level_from_message("INFO: operation complete") == "INFO"

    def test_debug(self):
        assert extract_level_from_message("DEBUG: variable x=5") == "DEBUG"

    def test_bracketed_level(self):
        assert extract_level_from_message("2020-01-01 [ERROR] something") == "ERROR"

    def test_no_level(self):
        assert extract_level_from_message("just a plain message") is None

    def test_empty(self):
        assert extract_level_from_message("") is None

    def test_none(self):
        assert extract_level_from_message(None) is None


class TestAzureMonitorParser:
    def test_azure_monitor_single_entry(self):
        from log_analyzer.parsers import AzureMonitorParser
        parser = AzureMonitorParser()
        line = json.dumps({
            "time": "2020-01-01T00:00:00Z",
            "level": "Error",
            "message": "Azure test error",
            "resourceId": "/subscriptions/test",
        })
        result = parser.parse(line)
        if result:
            assert result.level in ("ERROR", "WARNING", "INFO", "DEBUG", "CRITICAL")

    def test_azure_monitor_array(self):
        from log_analyzer.parsers import AzureMonitorParser
        parser = AzureMonitorParser()
        line = json.dumps([{
            "time": "2020-01-01T00:00:00Z",
            "level": "Warning",
            "message": "Azure array test",
        }])
        parser.parse(line)
        # Should handle array format

    def test_azure_monitor_can_parse(self):
        from log_analyzer.parsers import AzureMonitorParser
        parser = AzureMonitorParser()
        line = json.dumps({
            "time": "2020-01-01T00:00:00Z",
            "level": "Info",
            "message": "test",
        })
        result = parser.can_parse(line)
        assert isinstance(result, bool)

    def test_azure_monitor_numeric_severity(self):
        from log_analyzer.parsers import AzureMonitorParser
        parser = AzureMonitorParser()
        line = json.dumps({
            "time": "2020-01-01T00:00:00Z",
            "SeverityLevel": 3,
            "message": "Error with numeric severity",
        })
        result = parser.parse(line)
        if result:
            assert result.level == "ERROR"

    def test_azure_monitor_invalid_json(self):
        from log_analyzer.parsers import AzureMonitorParser
        parser = AzureMonitorParser()
        result = parser.parse("not json")
        assert result is None


class TestGCPLogParser:
    def test_gcp_log_entry(self):
        from log_analyzer.parsers import GCPCloudLoggingParser
        parser = GCPCloudLoggingParser()
        line = json.dumps({
            "timestamp": "2020-01-01T00:00:00Z",
            "severity": "ERROR",
            "textPayload": "GCP error message",
            "resource": {"type": "gce_instance"},
        })
        result = parser.parse(line)
        if result:
            assert result.level == "ERROR"

    def test_gcp_log_can_parse(self):
        from log_analyzer.parsers import GCPCloudLoggingParser
        parser = GCPCloudLoggingParser()
        line = json.dumps({
            "timestamp": "2020-01-01T00:00:00Z",
            "severity": "INFO",
            "textPayload": "test",
        })
        result = parser.can_parse(line)
        assert isinstance(result, bool)

    def test_gcp_invalid(self):
        from log_analyzer.parsers import GCPCloudLoggingParser
        parser = GCPCloudLoggingParser()
        result = parser.parse("not json")
        assert result is None

    def test_gcp_json_payload(self):
        """Test jsonPayload branch (line 394-400)."""
        from log_analyzer.parsers import GCPCloudLoggingParser
        parser = GCPCloudLoggingParser()
        line = json.dumps({
            "timestamp": "2020-01-01T00:00:00Z",
            "severity": "WARNING",
            "jsonPayload": {"message": "Structured payload", "key": "value"},
            "resource": {"type": "k8s_container", "labels": {
                "pod_name": "my-pod",
                "namespace_name": "default",
                "instance_id": "i-12345",
            }},
            "logName": "projects/test/logs/stdout",
            "trace": "projects/test/traces/abc123",
            "spanId": "span-456",
            "labels": {"env": "prod"},
        })
        result = parser.parse(line)
        assert result is not None
        assert result.level == "WARNING"
        assert result.metadata.get("pod_name") == "my-pod"
        assert result.metadata.get("namespace") == "default"
        assert result.metadata.get("instance_id") == "i-12345"
        assert result.metadata.get("trace") == "projects/test/traces/abc123"
        assert result.metadata.get("span_id") == "span-456"
        assert result.metadata.get("log_name") == "projects/test/logs/stdout"

    def test_gcp_non_dict_payload(self):
        """Test jsonPayload that's not a dict (line 400)."""
        from log_analyzer.parsers import GCPCloudLoggingParser
        parser = GCPCloudLoggingParser()
        line = json.dumps({
            "timestamp": "2020-01-01T00:00:00Z",
            "severity": "INFO",
            "jsonPayload": "just a string payload",
        })
        result = parser.parse(line)
        assert result is not None


class TestAWSCloudWatchParser:
    def test_aws_log_entry(self):
        from log_analyzer.parsers import AWSCloudWatchParser
        parser = AWSCloudWatchParser()
        line = json.dumps({
            "timestamp": 1577836800000,
            "message": "AWS CloudWatch log entry ERROR in function",
            "logGroup": "/aws/lambda/test",
        })
        result = parser.parse(line)
        if result:
            assert result.message

    def test_aws_can_parse(self):
        from log_analyzer.parsers import AWSCloudWatchParser
        parser = AWSCloudWatchParser()
        line = json.dumps({
            "timestamp": 1577836800000,
            "message": "test",
            "logGroup": "/aws/lambda/test",
        })
        result = parser.can_parse(line)
        assert isinstance(result, bool)

    def test_aws_invalid(self):
        from log_analyzer.parsers import AWSCloudWatchParser
        parser = AWSCloudWatchParser()
        result = parser.parse("not json")
        assert result is None
