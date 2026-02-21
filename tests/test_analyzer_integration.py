"""
Integration-style tests for LogAnalyzer using real file I/O.

These tests exercise the full analyzer pipeline (including multithreaded
and single-threaded paths) with temp files containing realistic log data.
"""

import os
import tempfile
from datetime import datetime

import pytest

from log_analyzer.analyzer import AnalysisResult, LogAnalyzer
from log_analyzer.parsers import UniversalFallbackParser

# ---------------------------------------------------------------------------
# Fixtures — temporary log files
# ---------------------------------------------------------------------------

@pytest.fixture
def syslog_file():
    """Create a temp syslog-ish file."""
    lines = (
        "2020-01-01T00:00:01Z [INFO] Application started\n"
        "2020-01-01T00:00:02Z [WARNING] Disk usage at 80%\n"
        "2020-01-01T00:00:03Z [ERROR] Failed to connect to database\n"
        "2020-01-01T00:00:04Z [ERROR] Connection timeout\n"
        "2020-01-01T00:00:05Z [INFO] Retry attempt 1\n"
        "2020-01-01T00:00:06Z [INFO] Retry attempt 2\n"
        "2020-01-01T00:00:07Z [INFO] Connection restored\n"
        "2020-01-01T00:00:08Z [DEBUG] Query executed in 12ms\n"
        "2020-01-01T00:00:09Z [INFO] Request processed\n"
        "2020-01-01T00:00:10Z [ERROR] Null pointer exception\n"
        "Random unparseable line\n"
        "Another random line without timestamp\n"
    )
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        f.write(lines)
        path = f.name
    yield path
    os.remove(path)


@pytest.fixture
def json_log_file():
    """Create a temp JSON-structured log file."""
    import json
    lines = []
    for i in range(20):
        entry = {
            "timestamp": f"2020-01-01T{i:02d}:00:00Z",
            "level": "ERROR" if i % 5 == 0 else "INFO",
            "message": f"Event {i}",
            "service": "api" if i < 10 else "worker",
        }
        lines.append(json.dumps(entry))
    content = "\n".join(lines) + "\n"
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        f.write(content)
        path = f.name
    yield path
    os.remove(path)


@pytest.fixture
def large_log_file():
    """Create a larger temp log file for threading tests."""
    lines = []
    for i in range(200):
        level = "ERROR" if i % 20 == 0 else ("WARNING" if i % 10 == 0 else "INFO")
        lines.append(f"2020-01-01T{(i // 60):02d}:{(i % 60):02d}:00Z [{level}] Line {i}\n")
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        f.writelines(lines)
        path = f.name
    yield path
    os.remove(path)


# ---------------------------------------------------------------------------
# Single-threaded analysis
# ---------------------------------------------------------------------------

class TestAnalyzerSingleThreaded:
    def test_analyze_syslog(self, syslog_file):
        analyzer = LogAnalyzer()
        parser = UniversalFallbackParser()
        result = analyzer.analyze(syslog_file, parser=parser, use_threading=False)
        assert isinstance(result, AnalysisResult)
        assert result.total_lines == 12
        assert result.parsed_lines > 0

    def test_analyze_with_specific_parser(self, syslog_file):
        analyzer = LogAnalyzer()
        parser = UniversalFallbackParser()
        result = analyzer.analyze(syslog_file, parser=parser, use_threading=False)
        assert result.detected_format == "universal"
        assert result.total_lines == 12

    def test_analyze_with_analytics(self, syslog_file):
        analyzer = LogAnalyzer()
        parser = UniversalFallbackParser()
        result = analyzer.analyze(
            syslog_file,
            parser=parser,
            use_threading=False,
            enable_analytics=True,
            analytics_config={"time_bucket_size": "1h"}
        )
        assert isinstance(result, AnalysisResult)

    def test_analysis_result_properties(self, syslog_file):
        analyzer = LogAnalyzer()
        parser = UniversalFallbackParser()
        result = analyzer.analyze(syslog_file, parser=parser, use_threading=False)
        assert 0 <= result.error_rate <= 100
        assert 0 <= result.parse_success_rate <= 100
        if result.earliest_timestamp and result.latest_timestamp:
            assert result.time_span is not None

    def test_analyze_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("")
            path = f.name
        try:
            analyzer = LogAnalyzer()
            parser = UniversalFallbackParser()
            result = analyzer.analyze(path, parser=parser, use_threading=False)
            assert result.total_lines == 0
            assert result.parsed_lines == 0
        finally:
            os.remove(path)

    def test_progress_callback(self, syslog_file):
        from unittest.mock import MagicMock
        callback = MagicMock()
        callback.update = MagicMock()
        analyzer = LogAnalyzer()
        parser = UniversalFallbackParser()
        result = analyzer.analyze(
            syslog_file, parser=parser, use_threading=False,
            progress_callback=callback
        )
        assert result.parsed_lines > 0
        assert callback.update.call_count >= 1


# ---------------------------------------------------------------------------
# Multithreaded analysis
# ---------------------------------------------------------------------------

class TestAnalyzerMultithreaded:
    def test_analyze_multithreaded(self, large_log_file):
        analyzer = LogAnalyzer(max_workers=2)
        result = analyzer.analyze(large_log_file, use_threading=True)
        assert isinstance(result, AnalysisResult)
        assert result.total_lines == 200
        assert result.parsed_lines > 0

    def test_multithreaded_matches_singlethreaded(self, syslog_file):
        analyzer = LogAnalyzer()
        parser = UniversalFallbackParser()

        single = analyzer.analyze(syslog_file, parser=parser, use_threading=False)
        multi = analyzer.analyze(syslog_file, parser=parser, use_threading=True)

        assert single.total_lines == multi.total_lines
        assert single.parsed_lines == multi.parsed_lines
        assert single.failed_lines == multi.failed_lines

    def test_multithreaded_with_progress(self, large_log_file):
        from unittest.mock import MagicMock
        callback = MagicMock()
        callback.update = MagicMock()
        analyzer = LogAnalyzer(max_workers=2)
        result = analyzer.analyze(
            large_log_file, use_threading=True,
            progress_callback=callback
        )
        assert result.parsed_lines > 0
        assert callback.update.call_count >= 1

    def test_multithreaded_with_analytics(self, large_log_file):
        analyzer = LogAnalyzer(max_workers=2)
        result = analyzer.analyze(
            large_log_file, use_threading=True,
            enable_analytics=True,
            analytics_config={"time_bucket_size": "1h"}
        )
        assert isinstance(result, AnalysisResult)


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

class TestFormatDetection:
    def test_detect_json_format(self, json_log_file):
        analyzer = LogAnalyzer()
        parser = analyzer.detect_format(json_log_file)
        # Should detect as JSON or universal fallback
        assert parser is not None

    def test_detect_unknown_format(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write("xyzzy\n" * 100)
            path = f.name
        try:
            analyzer = LogAnalyzer()
            analyzer.detect_format(path)
            # May return None for unrecognizable content
            # (depends on parsers)
        finally:
            os.remove(path)


# ---------------------------------------------------------------------------
# AnalysisResult properties
# ---------------------------------------------------------------------------

class TestAnalysisResultProperties:
    def test_error_rate_no_errors(self):
        r = AnalysisResult(filepath="x", detected_format="test",
                           total_lines=10, parsed_lines=10, failed_lines=0,
                           level_counts={"INFO": 10})
        assert r.error_rate == 0.0

    def test_error_rate_with_errors(self):
        r = AnalysisResult(filepath="x", detected_format="test",
                           total_lines=10, parsed_lines=10, failed_lines=0,
                           level_counts={"ERROR": 2, "INFO": 8})
        assert r.error_rate == 20.0

    def test_error_rate_zero_parsed(self):
        r = AnalysisResult(filepath="x", detected_format="test",
                           total_lines=0, parsed_lines=0, failed_lines=0)
        assert r.error_rate == 0.0

    def test_parse_success_rate(self):
        r = AnalysisResult(filepath="x", detected_format="test",
                           total_lines=100, parsed_lines=90, failed_lines=10)
        assert r.parse_success_rate == 90.0

    def test_time_span(self):
        r = AnalysisResult(
            filepath="x", detected_format="test",
            total_lines=10, parsed_lines=10, failed_lines=0,
            earliest_timestamp=datetime(2020, 1, 1, 0, 0, 0),
            latest_timestamp=datetime(2020, 1, 1, 12, 0, 0),
        )
        assert r.time_span is not None

    def test_time_span_no_timestamps(self):
        r = AnalysisResult(filepath="x", detected_format="test",
                           total_lines=10, parsed_lines=10, failed_lines=0)
        assert r.time_span is None
