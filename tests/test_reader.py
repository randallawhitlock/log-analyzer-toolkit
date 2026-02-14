"""
Unit tests for LogReader.
"""

import os
import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, mock_open

from log_analyzer.reader import LogReader, read_log_file

class TestLogReader:
    """Tests for LogReader class."""

    def test_init_file_verification(self):
        """Test initialization and file verification."""
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            tf.write(b"test")
            tf_path = tf.name

        try:
            # Valid file
            reader = LogReader(tf_path)
            assert reader.filepath == Path(tf_path)
            
            # Non-existent file
            with pytest.raises(FileNotFoundError):
                LogReader("non_existent_file.log")
                
            # Directory path
            with tempfile.TemporaryDirectory() as td:
                with pytest.raises(ValueError):
                    LogReader(td)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_read_lines(self):
        """Test reading lines from a file."""
        content = "line1\nline2\nline3"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tf:
            tf.write(content)
            tf_path = tf.name

        try:
            reader = LogReader(tf_path)
            lines = list(reader.read_lines())
            assert len(lines) == 3
            assert lines[0] == "line1"
            assert lines[1] == "line2"
            assert lines[2] == "line3"
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_read_all(self):
        """Test reading all lines into memory."""
        content = "line1\nline2"
        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tf:
            tf.write(content)
            tf_path = tf.name
            
        try:
            reader = LogReader(tf_path)
            lines = reader.read_all()
            assert len(lines) == 2
            
            # Test limit
            with pytest.raises(ValueError):
                reader.read_all(max_lines=1)
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_encoding_error(self):
        """Test handling of encoding errors."""
        # Write invalid utf-8 byte
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tf:
            tf.write(b"invalid\x80byte")
            tf_path = tf.name
            
        try:
            # Should replace invalid bytes with replacement character
            reader = LogReader(tf_path, encoding='utf-8')
            lines = list(reader.read_lines())
            assert len(lines) == 1
            # \x80 is invalid in utf-8, should be replaced by \ufffd
            assert "\ufffd" in lines[0] or "?" in lines[0]
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_get_file_info(self):
        """Test file metadata retrieval."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
            tf.write("data")
            tf_path = tf.name
            
        try:
            reader = LogReader(tf_path)
            info = reader.get_file_info()
            assert info['name'] == Path(tf_path).name
            assert info['size_bytes'] == 4
            assert 'modified' in info
            assert 'path' in info
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

    def test_count_lines(self):
        """Test counting lines without loading."""
        content = "1\n2\n3\n4\n5"
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
            tf.write(content)
            tf_path = tf.name
            
        try:
            reader = LogReader(tf_path)
            assert reader.count_lines() == 5
        finally:
            if os.path.exists(tf_path):
                os.remove(tf_path)

def test_read_log_file_convenience():
    """Test the convenience function."""
    content = "test\ndata"
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
        tf.write(content)
        tf_path = tf.name
        
    try:
        lines = list(read_log_file(tf_path))
        assert len(lines) == 2
        assert lines[0] == "test"
    finally:
        if os.path.exists(tf_path):
            os.remove(tf_path)
