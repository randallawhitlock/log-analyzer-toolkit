"""
Unit tests for log parsers.
"""

import pytest
from log_analyzer.parsers import (
    LogEntry,
    ApacheAccessParser,
    ApacheErrorParser,
    NginxAccessParser,
    JSONLogParser,
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
