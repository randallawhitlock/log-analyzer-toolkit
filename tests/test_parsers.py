"""
Unit tests for log parsers.
"""

import json
from datetime import timezone

import pytest

from log_analyzer.parsers import (
    AWSCloudWatchParser,
    AzureMonitorParser,
    ContainerdParser,
    DockerJSONParser,
    GCPCloudLoggingParser,
    KubernetesParser,
    extract_level_from_message,
    parse_cloud_timestamp,
)

# ============================================================================
# Utilities Tests
# ============================================================================

class TestUtilities:
    """Tests for utility functions in parsers module."""

    def test_parse_cloud_timestamp(self):
        """Test timestamp parsing for various formats."""
        # ISO8601 / RFC3339
        ts = parse_cloud_timestamp("2020-01-01T12:00:00Z")
        assert ts.year == 2020
        assert ts.hour == 12
        assert ts.tzinfo == timezone.utc

        # Unix milliseconds
        ts = parse_cloud_timestamp("1577880000000")
        assert ts.year == 2020
        assert ts.hour == 12  # 12:00 UTC (approx check)

        # RFC3339Nano
        ts = parse_cloud_timestamp("2020-01-01T12:00:00.123456789Z")
        assert ts.microsecond == 123456

        # Invalid
        assert parse_cloud_timestamp("invalid") is None
        assert parse_cloud_timestamp("") is None
        assert parse_cloud_timestamp(None) is None

    def test_extract_level_from_message(self):
        """Test level extraction from message strings."""
        assert extract_level_from_message("[INFO] System started") == "INFO"
        assert extract_level_from_message("Error: connection failed") == "ERROR"
        assert extract_level_from_message("CRITICAL FAILURE") == "CRITICAL"
        assert extract_level_from_message("Warning: disk full") == "WARNING"
        assert extract_level_from_message("Debug: entering function") == "DEBUG"
        assert extract_level_from_message("Normal message") is None


# ============================================================================
# AWS CloudWatch Parser Tests
# ============================================================================

class TestAWSCloudWatchParser:
    """Tests for AWS CloudWatch parser."""

    @pytest.fixture
    def parser(self):
        return AWSCloudWatchParser()

    def test_can_parse(self, parser):
        """Test format detection."""
        # JSON format
        assert parser.can_parse('{"logGroup": "/aws/lambda/test", "logEvents": []}')
        assert parser.can_parse('{"message": "Hello", "timestamp": 1234567890, "logGroup": "group1"}')

        # Text format
        assert parser.can_parse('2020-01-01T12:00:00.000Z [INFO] Message')

        # Invalid
        assert not parser.can_parse('Invalid format')

    def test_parse_json_batch(self, parser):
        """Test parsing JSON batch format."""
        line = json.dumps({
            "messageType": "DATA_MESSAGE",
            "logGroup": "/aws/lambda/func",
            "logStream": "stream1",
            "logEvents": [{
                "timestamp": 1577836800000,
                "message": "[INFO] Hello World"
            }]
        })
        entry = parser.parse(line)

        assert entry is not None
        assert entry.timestamp.year == 2020
        assert entry.level == "INFO"
        assert entry.message == "[INFO] Hello World"
        assert entry.source == "/aws/lambda/func"
        assert entry.metadata["log_stream"] == "stream1"

    def test_parse_json_single(self, parser):
        """Test parsing single JSON event."""
        line = json.dumps({
            "timestamp": 1577836800000,
            "message": "Error occurred",
            "logGroup": "group1"
        })
        entry = parser.parse(line)

        assert entry is not None
        assert entry.level == "ERROR"  # Extracted from message
        assert entry.message == "Error occurred"

    def test_parse_text(self, parser):
        """Test parsing plain text export format."""
        line = "2020-01-01T12:00:00.000Z [WARNING] Disk usage high"
        entry = parser.parse(line)

        assert entry is not None
        assert entry.timestamp.year == 2020
        assert entry.level == "WARNING"
        assert entry.message == "Disk usage high"


# ============================================================================
# GCP Cloud Logging Parser Tests
# ============================================================================

class TestGCPCloudLoggingParser:
    """Tests for GCP Cloud Logging parser."""

    @pytest.fixture
    def parser(self):
        return GCPCloudLoggingParser()

    def test_can_parse(self, parser):
        line = json.dumps({
            "timestamp": "2020-01-01T00:00:00Z",
            "severity": "INFO"
        })
        assert parser.can_parse(line)
        assert not parser.can_parse('{"other": "data"}')
        assert not parser.can_parse('Invalid')

    def test_parse_text_payload(self, parser):
        line = json.dumps({
            "timestamp": "2020-01-01T12:00:00Z",
            "severity": "ERROR",
            "textPayload": "Connection failed",
            "resource": {
                "type": "gce_instance",
                "labels": {"instance_id": "123"}
            }
        })
        entry = parser.parse(line)

        assert entry is not None
        assert entry.timestamp.hour == 12
        assert entry.level == "ERROR"
        assert entry.message == "Connection failed"
        assert entry.source == "gce_instance"
        assert entry.metadata["instance_id"] == "123"

    def test_parse_json_payload(self, parser):
        line = json.dumps({
            "timestamp": "2020-01-01T12:00:00Z",
            "severity": "INFO",
            "jsonPayload": {"message": "Structured log", "user": "admin"}
        })
        entry = parser.parse(line)

        assert entry is not None
        assert entry.message == "Structured log"


# ============================================================================
# Azure Monitor Parser Tests
# ============================================================================

class TestAzureMonitorParser:
    """Tests for Azure Monitor parser."""

    @pytest.fixture
    def parser(self):
        return AzureMonitorParser()

    def test_can_parse(self, parser):
        # App Insights format
        assert parser.can_parse('{"time": "2020-01-01", "level": "Error"}')
        # Log Analytics format
        assert parser.can_parse('{"TimeGenerated": "2020-01-01", "SeverityLevel": 3}')
        # Array format
        assert parser.can_parse('[{"time": "2020-01-01", "level": "Info"}]')

    def test_parse_app_insights(self, parser):
        line = json.dumps({
            "time": "2020-01-01T12:00:00.000Z",
            "level": "Error",
            "message": "Exception thrown",
            "operationName": "GET /api/data"
        })
        entry = parser.parse(line)

        assert entry is not None
        assert entry.level == "ERROR"
        assert entry.message == "Exception thrown"
        assert entry.metadata["operation"] == "GET /api/data"

    def test_parse_log_analytics(self, parser):
        line = json.dumps({
            "TimeGenerated": "2020-01-01T12:00:00.000Z",
            "SeverityLevel": 2,  # Warning
            "Message": "Latency high",
            "Computer": "web-01"
        })
        entry = parser.parse(line)

        assert entry is not None
        assert entry.level == "WARNING"
        assert entry.message == "Latency high"
        assert entry.source == "web-01"


# ============================================================================
# Container Parsers Tests
# ============================================================================

class TestContainerParsers:
    """Tests for Docker and Kubernetes parsers."""

    def test_docker_json_parser(self):
        parser = DockerJSONParser()
        line = json.dumps({
            "log": "Application started\n",
            "stream": "stdout",
            "time": "2020-01-01T12:00:00.000Z"
        })

        assert parser.can_parse(line)
        entry = parser.parse(line)

        assert entry is not None
        assert entry.timestamp.year == 2020
        assert entry.message == "Application started"
        assert entry.source == "stdout"
        # Level inferred from stream (stdout -> INFO)
        assert entry.level == "INFO"

    def test_kubernetes_cri_parser(self):
        parser = KubernetesParser()
        line = "2020-01-01T12:00:00.000Z stdout F [ERROR] Crash detected"

        assert parser.can_parse(line)
        entry = parser.parse(line)

        assert entry is not None
        assert entry.timestamp.year == 2020
        assert entry.source == "stdout"
        assert entry.level == "ERROR"
        assert entry.message == "[ERROR] Crash detected"

    def test_containerd_parser(self):
        parser = ContainerdParser()
        # Mixed CRI header + JSON content
        line = '2020-01-01T12:00:00.000Z stdout F {"level":"info","msg":"Service up"}'

        assert parser.can_parse(line)
        entry = parser.parse(line)

        assert entry is not None
        assert entry.level == "INFO"
        assert entry.message == "Service up"
