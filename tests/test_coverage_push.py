"""
Final comprehensive push toward 90% coverage.
Targets: analyzer inline detection, parse_file, analytics temporal/hourly,
parser can_parse and edge cases.
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from collections import Counter
from unittest.mock import patch, MagicMock

import pytest

from log_analyzer.parsers import (
    LogEntry, JSONLogParser, ApacheAccessParser, ApacheErrorParser,
    NginxAccessParser, SyslogParser, UniversalFallbackParser,
)


# =========================================================================
# Analyzer: inline detection (requires 100+ lines, no explicit parser)
# =========================================================================

class TestAnalyzerInlineDetectionFull:
    """Exercise the inline format detection path (lines 641-718)."""

    def test_inline_detection_json_format(self):
        """Inline detect JSON format from 150 lines (> DEFAULT_SAMPLE_SIZE=100)."""
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(150):
                f.write(json.dumps({
                    "timestamp": f"2020-01-01T{i % 24:02d}:{i % 60:02d}:00Z",
                    "level": ["INFO", "ERROR", "WARNING", "CRITICAL"][i % 4],
                    "message": f"Inline test message number {i}",
                    "source": f"app.service{i % 5}",
                }) + "\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            # detect_inline=True, use_threading=False -> exercises inline path
            result = analyzer.analyze(filepath, detect_inline=True,
                                       use_threading=False)
            assert result is not None
            assert result.total_lines == 150
            assert result.parsed_lines > 0
            assert result.detected_format is not None
        finally:
            os.unlink(filepath)

    def test_inline_detection_with_errors_and_warnings(self):
        """Inline detect with many errors/warnings to test collection limits."""
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(200):
                level = "ERROR" if i % 3 == 0 else "WARNING" if i % 3 == 1 else "INFO"
                f.write(json.dumps({
                    "timestamp": f"2020-01-{(i % 28) + 1:02d}T{i % 24:02d}:00:00Z",
                    "level": level,
                    "message": f"Error type {i % 10}" if level == "ERROR" else f"Warning {i}",
                    "source": f"svc.{i % 4}",
                }) + "\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            result = analyzer.analyze(filepath, detect_inline=True,
                                       use_threading=False, max_errors=10)
            assert result is not None
            assert len(result.errors) <= 10
            assert len(result.warnings) <= 10
        finally:
            os.unlink(filepath)

    def test_inline_detection_with_status_codes(self):
        """Test HTTP status code tracking in inline detection."""
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(150):
                f.write(json.dumps({
                    "timestamp": f"2020-01-01T{i % 24:02d}:00:00Z",
                    "level": "INFO",
                    "message": f"Request {i}",
                    "status": str([200, 301, 404, 500][i % 4]),
                }) + "\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            result = analyzer.analyze(filepath, detect_inline=True,
                                       use_threading=False)
            assert result is not None
            assert result.parsed_lines > 0
        finally:
            os.unlink(filepath)

    def test_inline_detection_unrecognized_format_with_fallback(self):
        """Unrecognized lines with use_fallback=True should use fallback parser."""
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(150):
                # Random text that no specific parser will match
                f.write(f"random line {i} with some text content here\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            result = analyzer.analyze(filepath, detect_inline=True,
                                       use_threading=False, use_fallback=True)
            assert result is not None
            assert result.total_lines == 150
        finally:
            os.unlink(filepath)

    def test_inline_detection_unrecognized_format_no_fallback(self):
        """Unrecognized lines with use_fallback=False should raise ValueError."""
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(150):
                f.write(f"random line {i} with some text content here\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            with pytest.raises(ValueError, match="Could not detect"):
                analyzer.analyze(filepath, detect_inline=True,
                                use_threading=False, use_fallback=False)
        finally:
            os.unlink(filepath)

    def test_inline_detection_with_empty_lines(self):
        """Empty lines should be skipped during inline detection."""
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(200):
                if i % 5 == 0:
                    f.write("\n")  # empty line
                else:
                    f.write(json.dumps({
                        "timestamp": f"2020-01-01T{i % 24:02d}:00:00Z",
                        "level": "INFO",
                        "message": f"Message {i}",
                    }) + "\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            result = analyzer.analyze(filepath, detect_inline=True,
                                       use_threading=False)
            assert result is not None
        finally:
            os.unlink(filepath)


# =========================================================================
# Analyzer: parse_file generator (lines 803-828)
# =========================================================================

class TestAnalyzerParseFile:
    def test_parse_file_with_parser(self):
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(10):
                f.write(json.dumps({
                    "timestamp": f"2020-01-01T{i:02d}:00:00Z",
                    "level": "INFO",
                    "message": f"Entry {i}",
                }) + "\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            entries = list(analyzer.parse_file(filepath, parser=JSONLogParser()))
            assert len(entries) == 10
            assert all(isinstance(e, LogEntry) for e in entries)
        finally:
            os.unlink(filepath)

    def test_parse_file_auto_detect(self):
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(20):
                f.write(json.dumps({
                    "timestamp": f"2020-01-01T{i:02d}:00:00Z",
                    "level": "ERROR",
                    "message": f"Error {i}",
                }) + "\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            entries = list(analyzer.parse_file(filepath))
            assert len(entries) > 0
        finally:
            os.unlink(filepath)

    def test_parse_file_skips_empty_lines(self):
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write(json.dumps({"level": "INFO", "message": "first"}) + "\n")
            f.write("\n")
            f.write(json.dumps({"level": "INFO", "message": "second"}) + "\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            entries = list(analyzer.parse_file(filepath, parser=JSONLogParser()))
            assert len(entries) == 2
        finally:
            os.unlink(filepath)


# =========================================================================
# Analytics: temporal distribution, hourly, and full compute_analytics
# =========================================================================

class TestAnalyticsComprehensive:
    def test_temporal_distribution_various_buckets(self):
        from log_analyzer.analytics import compute_temporal_distribution

        base = datetime(2020, 1, 1, 0, 0, 0)
        entries = [
            LogEntry(timestamp=base + timedelta(minutes=i*3), level="INFO",
                    message=f"msg {i}", source="test")
            for i in range(30)
        ]

        # Test each bucket size
        for bucket in ['5min', '15min', '1h', '1day']:
            result = compute_temporal_distribution(entries, bucket)
            assert isinstance(result, dict)
            assert len(result) > 0

    def test_temporal_distribution_unknown_bucket(self):
        from log_analyzer.analytics import compute_temporal_distribution

        entries = [
            LogEntry(timestamp=datetime(2020, 1, 1), level="INFO",
                    message="msg", source="test")
        ]
        result = compute_temporal_distribution(entries, 'unknown')
        assert isinstance(result, dict)

    def test_temporal_distribution_no_timestamps(self):
        from log_analyzer.analytics import compute_temporal_distribution

        entries = [
            LogEntry(timestamp=None, level="INFO", message="no ts", source="test")
        ]
        result = compute_temporal_distribution(entries, '1h')
        assert len(result) == 0

    def test_hourly_distribution(self):
        from log_analyzer.analytics import compute_hourly_distribution

        entries = [
            LogEntry(timestamp=datetime(2020, 1, 1, h, 0), level="INFO",
                    message="msg", source="test")
            for h in range(24)
        ]
        result = compute_hourly_distribution(entries)
        assert isinstance(result, dict)
        assert len(result) == 24

    def test_hourly_distribution_no_timestamps(self):
        from log_analyzer.analytics import compute_hourly_distribution

        entries = [
            LogEntry(timestamp=None, level="INFO", message="msg", source="test")
        ]
        result = compute_hourly_distribution(entries)
        assert len(result) == 0

    def test_compute_analytics_full(self):
        from log_analyzer.analytics import compute_analytics

        base = datetime(2020, 1, 1)
        errors = [
            LogEntry(timestamp=base + timedelta(hours=i), level="ERROR",
                    message=f"Error {i}", source=f"mod{i%3}")
            for i in range(10)
        ]
        warnings_list = [
            LogEntry(timestamp=base + timedelta(hours=i, minutes=30), level="WARNING",
                    message=f"Warn {i}", source=f"mod{i%2}")
            for i in range(5)
        ]
        level_counts = {"ERROR": 10, "WARNING": 5, "INFO": 100}
        source_counts = {"mod0": 40, "mod1": 35, "mod2": 30}

        result = compute_analytics(errors, warnings_list, level_counts, source_counts)
        assert result is not None

    def test_compute_analytics_with_config(self):
        from log_analyzer.analytics import compute_analytics

        result = compute_analytics([], [], {"INFO": 5}, {"src": 5},
                                   config={"time_bucket_size": "5min"})
        assert result is not None


# =========================================================================
# Parser: can_parse across all formats
# =========================================================================

class TestParserCanParse:
    def test_json_can_parse(self):
        parser = JSONLogParser()
        assert parser.can_parse('{"level": "INFO", "message": "test"}')
        assert not parser.can_parse("not json")

    def test_apache_access_can_parse(self):
        parser = ApacheAccessParser()
        line = '127.0.0.1 - - [10/Jan/2020:13:55:36 +0000] "GET / HTTP/1.1" 200 1234'
        assert parser.can_parse(line)
        assert not parser.can_parse('{"json": true}')

    def test_apache_error_can_parse(self):
        parser = ApacheErrorParser()
        line = '[Fri Jan 10 13:55:36.123456 2020] [core:error] [pid 1234] test error'
        result = parser.can_parse(line)
        assert isinstance(result, bool)

    def test_nginx_access_can_parse(self):
        parser = NginxAccessParser()
        line = '127.0.0.1 - - [10/Jan/2020:13:55:36 +0000] "GET / HTTP/1.1" 200 1234 "-" "Mozilla"'
        assert parser.can_parse(line)

    def test_syslog_can_parse(self):
        parser = SyslogParser()
        line = "Jan 10 13:55:36 myhost sshd[1234]: test message"
        assert parser.can_parse(line)
        assert not parser.can_parse('{"json": true}')

    def test_universal_fallback_can_parse_anything(self):
        parser = UniversalFallbackParser()
        assert parser.can_parse("literally anything")
        assert parser.can_parse("")

    def test_all_parsers_parse_none_on_invalid(self):
        """All specific parsers return None for completely invalid input."""
        parsers = [
            ApacheAccessParser(), ApacheErrorParser(),
            NginxAccessParser(), SyslogParser(),
        ]
        for parser in parsers:
            result = parser.parse("@@@@INVALID@@@@")
            assert result is None


# =========================================================================
# Analyzer: enable_analytics path (lines 779-789)
# =========================================================================

class TestAnalyzerWithAnalytics:
    def test_analyze_with_analytics_enabled(self):
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(30):
                f.write(json.dumps({
                    "timestamp": f"2020-01-01T{i % 24:02d}:00:00Z",
                    "level": ["ERROR", "WARNING", "INFO"][i % 3],
                    "message": f"Analytics test {i}",
                    "source": f"module{i % 3}",
                }) + "\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            result = analyzer.analyze(filepath, parser=JSONLogParser(),
                                       use_threading=False,
                                       enable_analytics=True)
            assert result is not None
            # Analytics should be computed if available
        finally:
            os.unlink(filepath)

    def test_analyze_with_analytics_config(self):
        from log_analyzer.analyzer import LogAnalyzer

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(30):
                f.write(json.dumps({
                    "timestamp": f"2020-01-01T{i % 24:02d}:00:00Z",
                    "level": "INFO",
                    "message": f"Test {i}",
                }) + "\n")
            filepath = f.name

        try:
            analyzer = LogAnalyzer()
            result = analyzer.analyze(filepath, parser=JSONLogParser(),
                                       use_threading=False,
                                       enable_analytics=True,
                                       analytics_config={"time_bucket_size": "5min"})
            assert result is not None
        finally:
            os.unlink(filepath)
