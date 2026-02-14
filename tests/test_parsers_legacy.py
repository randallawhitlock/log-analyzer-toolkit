"""
Unit tests for standard/legacy log parsers.
"""

from datetime import datetime
import pytest

from log_analyzer.parsers import (
    ApacheAccessParser,
    ApacheErrorParser,
    NginxAccessParser,
    SyslogParser,
    JSONLogParser
)

class TestStandardParsers:
    """Tests for standard log parsers (Apache, Nginx, Syslog)."""

    def test_apache_access_parser(self):
        parser = ApacheAccessParser()
        line = '127.0.0.1 - - [01/Jan/2020:12:00:00 +0000] "GET /index.html HTTP/1.1" 200 1024'
        
        assert parser.can_parse(line)
        entry = parser.parse(line)
        
        assert entry is not None
        assert entry.timestamp.year == 2020
        assert entry.level == "INFO"
        assert entry.message == "GET /index.html HTTP/1.1"
        assert int(entry.metadata["status"]) == 200
        assert int(entry.metadata["size"]) == 1024

    def test_apache_error_parser(self):
        parser = ApacheErrorParser()
        line = '[Wed Jan 01 12:00:00 2020] [error] [client 127.0.0.1] File does not exist: /var/www/missing'
        
        assert parser.can_parse(line)
        entry = parser.parse(line)
        
        assert entry is not None
        assert entry.timestamp is None  # Parser does not currently parse timestamp string to datetime
        assert entry.level == "ERROR"
        assert entry.message == "[client 127.0.0.1] File does not exist: /var/www/missing"
        # Source is not extracted in legacy pattern logic according to code inspection
        # legacy pattern puts everything after level into message
        # Wait, let's verify regex "message" group captures [client...] too. Yes.

    def test_nginx_access_parser(self):
        parser = NginxAccessParser()
        line = '127.0.0.1 - - [01/Jan/2020:12:00:00 +0000] "POST /api/login HTTP/1.1" 401 532 "-" "Mozilla/5.0"'
        
        assert parser.can_parse(line)
        entry = parser.parse(line)
        
        assert entry is not None
        assert int(entry.metadata["status"]) == 401
        
    def test_syslog_parser(self):
        parser = SyslogParser()
        line = 'Jan  1 12:00:00 localhost sshd[1234]: Failed password for root'
        # Note: Syslog parsing relies on current year usually if not specified, 
        # or defaults. The parser might need mocking for datetime if it uses `datetime.now().year`.
        
        assert parser.can_parse(line)
        entry = parser.parse(line)
        
        assert entry is not None
        assert entry.source == "localhost"
        assert "Failed password" in entry.message

    def test_json_log_parser(self):
        parser = JSONLogParser()
        line = '{"timestamp": "2020-01-01T12:00:00Z", "level": "error", "message": "Something went wrong"}'
        
        assert parser.can_parse(line)
        entry = parser.parse(line)
        
        assert entry is not None
        assert entry.level == "ERROR"
        assert entry.message == "Something went wrong"
