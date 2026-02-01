"""
Tests for recent fixes.
"""

import pytest
from log_analyzer.parsers import SyslogParser

class TestSyslogFix:
    """Test fixes for Syslog parser."""
    
    def test_rfc5424_structured_data(self):
        """Test parsing RFC 5424 with structured data."""
        parser = SyslogParser()
        
        # Example with structured data: [exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"]
        line = '<165>1 2023-10-11T22:14:15.003Z mymachine.example.com evntslog - ID47 [exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"] An application event occurred'
        
        entry = parser.parse(line)
        
        assert entry is not None
        assert entry.source == "mymachine.example.com"
        assert entry.message == "An application event occurred"
        assert entry.metadata["structured_data"] == '[exampleSDID@32473 iut="3" eventSource="Application" eventID="1011"]'
        assert entry.metadata["msgid"] == "ID47"

    def test_rfc5424_multiple_structured_data(self):
        """Test parsing RFC 5424 with MULTIPLE structured data elements."""
        parser = SyslogParser()
        
        # Example with two SD elements
        line = '<165>1 2023-10-11T22:14:15.003Z mymachine.example.com evntslog - ID47 [sdOne key="val"][sdTwo key="val2"] The message itself'
        
        entry = parser.parse(line)
        
        assert entry is not None
        assert entry.message == "The message itself"
        assert entry.metadata["structured_data"] == '[sdOne key="val"][sdTwo key="val2"]'

    def test_rfc5424_no_structured_data(self):
        """Test parsing RFC 5424 with NIL structured data."""
        parser = SyslogParser()
        
        line = '<165>1 2023-10-11T22:14:15.003Z mymachine.example.com evntslog - ID47 - A message with no SD'
        
        entry = parser.parse(line)
        
        assert entry is not None
        assert entry.message == "A message with no SD"
        assert entry.metadata["structured_data"] == "-"


class TestMemorySafety:
    """Test memory usage safeguards."""
    
    def test_read_all_limit(self, tmp_path):
        """Test that read_all raises ValueError when limit exceeded."""
        from log_analyzer.reader import LogReader
        
        # Create dummy file with 20 lines
        p = tmp_path / "large.log"
        p.write_text("\n".join([f"Line {i}" for i in range(20)]))
        
        reader = LogReader(str(p))
        
        # Standard read should pass
        lines = reader.read_all(max_lines=100)
        assert len(lines) == 20
        
        # Limit read should fail
        with pytest.raises(ValueError, match="exceeds maximum line limit"):
            reader.read_all(max_lines=10)
