"""
Unit tests for the log analyzer.
"""

import pytest
import tempfile
import os
from collections import Counter
from unittest.mock import patch

from log_analyzer.analyzer import LogAnalyzer, AnalysisResult
from log_analyzer.reader import LogReader
from log_analyzer.constants import MAX_COUNTER_SIZE, COUNTER_PRUNE_TO


class TestLogReader:
    """Tests for LogReader class."""
    
    def test_read_lines(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("line 1\nline 2\nline 3\n")
            f.flush()
            
            reader = LogReader(f.name)
            lines = reader.read_all()
            
            assert len(lines) == 3
            assert lines[0] == "line 1"
            assert lines[2] == "line 3"
            
            os.unlink(f.name)
    
    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            LogReader("/nonexistent/path/file.log")
    
    def test_count_lines(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("a\nb\nc\nd\ne\n")
            f.flush()
            
            reader = LogReader(f.name)
            assert reader.count_lines() == 5
            
            os.unlink(f.name)
    
    def test_get_file_info(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("test content")
            f.flush()
            
            reader = LogReader(f.name)
            info = reader.get_file_info()
            
            assert 'path' in info
            assert 'name' in info
            assert 'size_bytes' in info
            assert info['size_bytes'] == 12
            
            os.unlink(f.name)


class TestLogAnalyzer:
    """Tests for LogAnalyzer class."""
    
    def test_detect_format_apache(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write('192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET / HTTP/1.1" 200 100\n')
            f.write('192.168.1.2 - - [10/Oct/2023:13:55:37 +0000] "GET /api HTTP/1.1" 200 200\n')
            f.flush()
            
            analyzer = LogAnalyzer()
            parser = analyzer.detect_format(f.name)
            
            assert parser is not None
            assert parser.name in ['apache_access', 'nginx_access']
            
            os.unlink(f.name)
    
    def test_detect_format_json(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write('{"level": "info", "msg": "test"}\n')
            f.write('{"level": "error", "msg": "fail"}\n')
            f.flush()
            
            analyzer = LogAnalyzer()
            parser = analyzer.detect_format(f.name)
            
            assert parser is not None
            assert parser.name == 'json'
            
            os.unlink(f.name)
    
    def test_analyze_basic(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write('{"level": "info", "msg": "started"}\n')
            f.write('{"level": "error", "msg": "failed"}\n')
            f.write('{"level": "info", "msg": "completed"}\n')
            f.flush()
            
            analyzer = LogAnalyzer()
            result = analyzer.analyze(f.name)
            
            assert result.total_lines == 3
            assert result.parsed_lines == 3
            assert result.level_counts['INFO'] == 2
            assert result.level_counts['ERROR'] == 1
            
            os.unlink(f.name)


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass."""
    
    def test_error_rate_calculation(self):
        result = AnalysisResult(
            filepath="/test.log",
            detected_format="test",
            total_lines=100,
            parsed_lines=100,
            failed_lines=0,
            level_counts={'ERROR': 10, 'CRITICAL': 5, 'INFO': 85}
        )
        
        assert result.error_rate == 15.0
    
    def test_parse_success_rate(self):
        result = AnalysisResult(
            filepath="/test.log",
            detected_format="test",
            total_lines=100,
            parsed_lines=90,
            failed_lines=10
        )
        
        assert result.parse_success_rate == 90.0
    
    def test_zero_lines_no_division_error(self):
        result = AnalysisResult(
            filepath="/test.log",
            detected_format="test",
            total_lines=0,
            parsed_lines=0,
            failed_lines=0
        )

        assert result.error_rate == 0.0
        assert result.parse_success_rate == 0.0


class TestMultithreading:
    """Tests for multithreaded analysis features."""

    def test_max_workers_from_init(self):
        """Test that max_workers can be set via __init__."""
        analyzer = LogAnalyzer(max_workers=2)
        assert analyzer.max_workers == 2

    def test_max_workers_from_env(self):
        """Test that max_workers can be set via environment variable."""
        with patch.dict(os.environ, {'LOG_ANALYZER_MAX_WORKERS': '3'}):
            # Reset config to pick up env var
            from log_analyzer.config import reset_config
            reset_config()

            analyzer = LogAnalyzer()
            assert analyzer.max_workers == 3

            # Clean up
            reset_config()

    def test_counter_pruning(self):
        """Test that _prune_counter correctly prunes oversized counters."""
        # Create a counter with more than MAX_COUNTER_SIZE items
        counter = Counter({f"item_{i}": i for i in range(MAX_COUNTER_SIZE + 1000)})
        original_size = len(counter)

        assert original_size > MAX_COUNTER_SIZE

        # Prune it
        LogAnalyzer._prune_counter(counter)

        # Should be pruned to COUNTER_PRUNE_TO
        assert len(counter) == COUNTER_PRUNE_TO

        # Should keep the most common items (highest numbers)
        assert counter[f"item_{MAX_COUNTER_SIZE + 999}"] > 0

    def test_counter_no_prune_when_small(self):
        """Test that _prune_counter doesn't prune small counters."""
        counter = Counter({'a': 1, 'b': 2, 'c': 3})
        original_size = len(counter)

        LogAnalyzer._prune_counter(counter)

        # Should remain unchanged
        assert len(counter) == original_size
        assert counter['a'] == 1

    def test_single_threaded_analysis(self):
        """Test single-threaded analysis still works."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(100):
                f.write(f'{{"level": "info", "msg": "message {i}"}}\n')
            f.flush()

            analyzer = LogAnalyzer(max_workers=1)
            # Disable threading explicitly
            result = analyzer.analyze(f.name, use_threading=False)

            assert result.total_lines == 100
            assert result.parsed_lines == 100
            assert result.detected_format == 'json'

            os.unlink(f.name)

    def test_multithreaded_analysis(self):
        """Test multithreaded analysis produces same results as single-threaded."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            # Create a file with enough lines to benefit from multithreading
            for i in range(1000):
                level = "error" if i % 10 == 0 else "info"
                f.write(f'{{"level": "{level}", "msg": "message {i}"}}\n')
            f.flush()

            analyzer = LogAnalyzer(max_workers=2)

            # Single-threaded analysis
            result_single = analyzer.analyze(f.name, use_threading=False)

            # Multithreaded analysis
            result_multi = analyzer.analyze(f.name, use_threading=True, chunk_size=100)

            # Results should be identical
            assert result_single.total_lines == result_multi.total_lines
            assert result_single.parsed_lines == result_multi.parsed_lines
            assert result_single.level_counts == result_multi.level_counts
            assert result_single.detected_format == result_multi.detected_format

            os.unlink(f.name)

    def test_multithreaded_with_different_workers(self):
        """Test multithreading with different worker counts."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(500):
                f.write(f'{{"level": "info", "msg": "message {i}"}}\n')
            f.flush()

            results = []
            for workers in [1, 2, 4]:
                analyzer = LogAnalyzer(max_workers=workers)
                result = analyzer.analyze(f.name, use_threading=True, chunk_size=50)
                results.append(result)

            # All results should be identical regardless of worker count
            for result in results:
                assert result.total_lines == 500
                assert result.parsed_lines == 500
                assert result.level_counts['INFO'] == 500

            os.unlink(f.name)

    def test_chunk_processing(self):
        """Test that _process_chunk correctly processes a chunk of lines."""
        from log_analyzer.parsers import JSONLogParser

        parser = JSONLogParser()
        analyzer = LogAnalyzer()

        lines = [
            '{"level": "info", "msg": "test1"}',
            '{"level": "error", "msg": "test2"}',
            '{"level": "info", "msg": "test3"}',
        ]

        result = analyzer._process_chunk(lines, parser, max_errors=50)

        assert result['parsed_lines'] == 3
        assert result['failed_lines'] == 0
        assert result['level_counts']['INFO'] == 2
        assert result['level_counts']['ERROR'] == 1
        assert len(result['errors']) == 1

    def test_merge_chunk_results(self):
        """Test that _merge_chunk_results correctly merges results from multiple chunks."""
        from log_analyzer.parsers import JSONLogParser

        parser = JSONLogParser()
        analyzer = LogAnalyzer()

        # Simulate results from two chunks
        chunk_results = [
            {
                'parsed_lines': 50,
                'failed_lines': 0,
                'level_counts': Counter({'INFO': 40, 'ERROR': 10}),
                'status_codes': Counter(),
                'source_counts': Counter({'app': 50}),
                'error_messages': Counter({'error1': 10}),
                'errors': [],
                'warnings': [],
                'earliest': None,
                'latest': None,
            },
            {
                'parsed_lines': 50,
                'failed_lines': 0,
                'level_counts': Counter({'INFO': 45, 'ERROR': 5}),
                'status_codes': Counter(),
                'source_counts': Counter({'app': 50}),
                'error_messages': Counter({'error2': 5}),
                'errors': [],
                'warnings': [],
                'earliest': None,
                'latest': None,
            },
        ]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write('test\n')
            f.flush()

            result = analyzer._merge_chunk_results(
                filepath=f.name,
                parser=parser,
                total_lines=100,
                chunk_results=chunk_results,
                max_errors=50,
                start_time=0
            )

            assert result.parsed_lines == 100
            assert result.level_counts['INFO'] == 85
            assert result.level_counts['ERROR'] == 15

            os.unlink(f.name)

    def test_inline_detection_disabled_with_threading(self):
        """Test that inline detection is disabled when multithreading is enabled."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            for i in range(100):
                f.write(f'{{"level": "info", "msg": "message {i}"}}\n')
            f.flush()

            analyzer = LogAnalyzer(max_workers=2)

            # Even if detect_inline=True, it should be forced to False for threading
            result = analyzer.analyze(f.name, use_threading=True, detect_inline=True)

            assert result.parsed_lines == 100
            assert result.detected_format == 'json'

            os.unlink(f.name)
