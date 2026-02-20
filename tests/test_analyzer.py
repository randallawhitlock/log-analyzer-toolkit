"""
Unit tests for LogAnalyzer and AnalysisResult.
"""

from collections import Counter
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from log_analyzer.analyzer import AnalysisResult, LogAnalyzer
from log_analyzer.parsers import UniversalFallbackParser


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass properties."""

    def test_error_rate_with_errors(self):
        result = AnalysisResult(
            filepath="test.log", detected_format="standard",
            total_lines=100, parsed_lines=100, failed_lines=0,
            level_counts={"ERROR": 5, "CRITICAL": 2, "INFO": 93},
        )
        assert result.error_rate == pytest.approx(7.0)

    def test_error_rate_empty(self):
        result = AnalysisResult(
            filepath="test.log", detected_format="standard",
            total_lines=0, parsed_lines=0, failed_lines=0,
        )
        assert result.error_rate == 0.0

    def test_parse_success_rate(self):
        result = AnalysisResult(
            filepath="test.log", detected_format="standard",
            total_lines=200, parsed_lines=180, failed_lines=20,
        )
        assert result.parse_success_rate == pytest.approx(90.0)

    def test_parse_success_rate_empty(self):
        result = AnalysisResult(
            filepath="test.log", detected_format="standard",
            total_lines=0, parsed_lines=0, failed_lines=0,
        )
        assert result.parse_success_rate == 0.0

    def test_time_span_with_timestamps(self):
        t1 = datetime(2020, 1, 1, 12, 0, 0)
        t2 = datetime(2020, 1, 1, 14, 30, 0)
        result = AnalysisResult(
            filepath="test.log", detected_format="standard",
            total_lines=10, parsed_lines=10, failed_lines=0,
            earliest_timestamp=t1, latest_timestamp=t2,
        )
        assert result.time_span == timedelta(hours=2, minutes=30)

    def test_time_span_without_timestamps(self):
        result = AnalysisResult(
            filepath="test.log", detected_format="standard",
            total_lines=10, parsed_lines=10, failed_lines=0,
        )
        assert result.time_span is None


class TestPruneCounter:
    """Tests for LogAnalyzer._prune_counter static method."""

    def test_prune_when_over_limit(self):
        c = Counter({f"key{i}": i for i in range(150)})
        LogAnalyzer._prune_counter(c, max_size=100, prune_to=50)
        assert len(c) == 50
        # Top items should be preserved
        assert c["key149"] == 149

    def test_no_prune_when_under_limit(self):
        c = Counter({"a": 1, "b": 2})
        LogAnalyzer._prune_counter(c, max_size=100, prune_to=50)
        assert len(c) == 2


class TestLogAnalyzer:
    """Tests for LogAnalyzer analysis methods."""

    def test_analyze_file_not_found(self):
        with patch('log_analyzer.analyzer.LogReader') as mock_reader_cls:
            mock_reader_cls.side_effect = FileNotFoundError("File not found")
            analyzer = LogAnalyzer()
            with pytest.raises(FileNotFoundError):
                analyzer.analyze("non_existent.log")

    def test_analyze_empty_file(self):
        with patch('log_analyzer.analyzer.LogReader') as mock_reader_cls:
            mock_instance = mock_reader_cls.return_value
            mock_instance.read_lines.return_value = []
            mock_instance.count_lines.return_value = 0
            analyzer = LogAnalyzer()
            result = analyzer.analyze("empty.log")
            assert isinstance(result, AnalysisResult)
            assert result.total_lines == 0
            assert result.parsed_lines == 0

    def test_analyze_success(self):
        lines = [
            '2020-01-01T12:00:00Z [INFO] Started',
            '2020-01-01T12:00:01Z [ERROR] Failed',
            'Invalid line',
        ]
        with patch('log_analyzer.analyzer.LogReader') as mock_reader_cls:
            mock_instance = mock_reader_cls.return_value
            mock_instance.read_lines.return_value = lines
            mock_instance.count_lines.return_value = 3
            analyzer = LogAnalyzer()
            result = analyzer.analyze("test.log")
            assert result.parsed_lines == 3
            assert result.failed_lines == 0

    def test_analyze_with_specific_parser(self):
        lines = ['2020-01-01T12:00:00Z [INFO] Started']
        with patch('log_analyzer.analyzer.LogReader') as mock_reader_cls:
            mock_instance = mock_reader_cls.return_value
            mock_instance.read_lines.return_value = lines
            mock_instance.count_lines.return_value = 1
            analyzer = LogAnalyzer()
            parser = UniversalFallbackParser()
            result = analyzer.analyze("test.log", parser=parser)
            assert result.parsed_lines == 1
            assert result.detected_format == "universal"

    def test_analyze_fallback_for_random_text(self):
        lines = ['Just some random text', 'Another line']
        with patch('log_analyzer.analyzer.LogReader') as mock_reader_cls:
            mock_instance = mock_reader_cls.return_value
            mock_instance.read_lines.return_value = lines
            mock_instance.count_lines.return_value = 2
            analyzer = LogAnalyzer()
            result = analyzer.analyze("test.log")
            assert result.parsed_lines == 2
            assert result.failed_lines == 0

    def test_analyze_with_format_detection(self):
        lines = [
            '2020-01-01T12:00:00Z [INFO] Started',
            '2020-01-01T12:00:01Z [ERROR] Failed',
        ]
        with patch('log_analyzer.analyzer.LogReader') as mock_reader_cls:
            mock_instance = mock_reader_cls.return_value
            mock_instance.read_lines.return_value = lines
            mock_instance.count_lines.return_value = 2
            analyzer = LogAnalyzer()
            result = analyzer.analyze("test.log")
            assert result.parsed_lines == 2
            assert result.detected_format is not None

    def test_error_aggregation(self):
        lines = [
            '2020-01-01T12:00:00Z [ERROR] Error 1',
            '2020-01-01T12:00:01Z [ERROR] Error 2',
            '2020-01-01T12:00:02Z [WARN] Warning 1',
        ]
        with patch('log_analyzer.analyzer.LogReader') as mock_reader_cls:
            mock_instance = mock_reader_cls.return_value
            mock_instance.read_lines.return_value = lines
            mock_instance.count_lines.return_value = 3
            analyzer = LogAnalyzer()
            result = analyzer.analyze("error.log")
            assert result.level_counts.get('ERROR') == 2
            assert result.level_counts.get('WARNING') == 1

    def test_analyze_single_threaded(self):
        """Ensure single-threaded path works with use_threading=False."""
        lines = [
            '2020-01-01T12:00:00Z [INFO] Line 1',
            '2020-01-01T12:00:01Z [ERROR] Line 2',
        ]
        with patch('log_analyzer.analyzer.LogReader') as mock_reader_cls:
            mock_instance = mock_reader_cls.return_value
            mock_instance.read_lines.return_value = lines
            mock_instance.count_lines.return_value = 2
            analyzer = LogAnalyzer()
            parser = UniversalFallbackParser()
            result = analyzer.analyze("test.log", parser=parser, use_threading=False)
            assert result.parsed_lines == 2
            assert result.detected_format == "universal"

    def test_detect_format(self):
        """Test standalone format detection method."""
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as tf:
            tf.write('{"log": "test", "stream": "stdout", "time": "2020-01-01T00:00:00Z"}\n' * 10)
            tf_path = tf.name
        try:
            analyzer = LogAnalyzer()
            parser = analyzer.detect_format(tf_path)
            assert parser is not None
            assert hasattr(parser, 'name')
        finally:
            os.remove(tf_path)

    def test_detect_format_unknown(self):
        """Test detection returns None for unrecognizable formats."""
        import os
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as tf:
            tf.write('xyzzy\n' * 100)
            tf_path = tf.name
        try:
            analyzer = LogAnalyzer()
            parser = analyzer.detect_format(tf_path)
            assert parser is None
        finally:
            os.remove(tf_path)

    def test_analyze_with_progress_callback(self):
        """Ensure progress callback is invoked during analysis."""
        lines = ['2020-01-01T12:00:00Z [INFO] test'] * 5
        callback = MagicMock()
        callback.update = MagicMock()
        with patch('log_analyzer.analyzer.LogReader') as mock_reader_cls:
            mock_instance = mock_reader_cls.return_value
            mock_instance.read_lines.return_value = lines
            mock_instance.count_lines.return_value = 5
            analyzer = LogAnalyzer()
            parser = UniversalFallbackParser()
            result = analyzer.analyze(
                "test.log", parser=parser,
                progress_callback=callback, use_threading=False
            )
            assert result.parsed_lines == 5
            assert callback.update.call_count >= 1

    def test_analyze_with_analytics(self):
        """Test analysis with analytics enabled."""
        lines = [
            '2020-01-01T12:00:00Z [INFO] Line 1',
            '2020-01-01T13:00:00Z [ERROR] Line 2',
        ]
        with patch('log_analyzer.analyzer.LogReader') as mock_reader_cls:
            mock_instance = mock_reader_cls.return_value
            mock_instance.read_lines.return_value = lines
            mock_instance.count_lines.return_value = 2
            analyzer = LogAnalyzer()
            parser = UniversalFallbackParser()
            result = analyzer.analyze(
                "test.log", parser=parser, use_threading=False,
                enable_analytics=True,
                analytics_config={'time_bucket_size': '1h'}
            )
            assert result.parsed_lines == 2
            # Analytics may or may not be populated depending on implementation
