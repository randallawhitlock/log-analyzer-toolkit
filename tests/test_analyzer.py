"""
Unit tests for the log analyzer.
"""

import pytest
import tempfile
import os

from log_analyzer.analyzer import LogAnalyzer, AnalysisResult
from log_analyzer.reader import LogReader


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
