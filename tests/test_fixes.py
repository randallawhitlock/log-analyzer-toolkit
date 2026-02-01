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


class TestPIIRedaction:
    """Test PII redaction in AI providers."""
    
    def test_redact_ip_addresses(self):
        """Test that IPv4 addresses are redacted."""
        from log_analyzer.ai_providers.base import AIProvider
        
        # Create a concrete implementation for testing
        class MockProvider(AIProvider):
            def analyze(self, prompt, system_prompt=None): return None
            def is_available(self): return True
            def get_model(self): return "mock"
            
        provider = MockProvider()
        
        log = "Connection from 192.168.1.100 failed. Retry from 10.0.0.5."
        redacted = provider.sanitize_log_content(log)
        
        assert "192.168.1.100" not in redacted
        assert "10.0.0.5" not in redacted
        assert "[IP_REDACTED]" in redacted
        # Using string matching rather than exact equality to be resilient to exact substitution order
        assert "Connection from [IP_REDACTED] failed. Retry from [IP_REDACTED]." == redacted

    def test_redact_email_addresses(self):
        """Test that email addresses are redacted."""
        from log_analyzer.ai_providers.base import AIProvider
        
        class MockProvider(AIProvider):
            def analyze(self, prompt, system_prompt=None): return None
            def is_available(self): return True
            def get_model(self): return "mock"
            
        provider = MockProvider()
        
        log = "User admin@example.com login failed. Contact support@company.org."
        redacted = provider.sanitize_log_content(log)
        
        assert "admin@example.com" not in redacted
        assert "support@company.org" not in redacted
        assert "[EMAIL_REDACTED]" in redacted
        assert "User [EMAIL_REDACTED] login failed. Contact [EMAIL_REDACTED]." == redacted

    def test_mixed_pii_content(self):
        """Test redaction of mixed PII content."""
        from log_analyzer.ai_providers.base import AIProvider
        
        class MockProvider(AIProvider):
            def analyze(self, prompt, system_prompt=None): return None
            def is_available(self): return True
            def get_model(self): return "mock"
            
        provider = MockProvider()
        
        log = "Failed login: user=john.doe@test.com ip=203.0.113.1 time=12:00"
        redacted = provider.sanitize_log_content(log)
        
        assert "john.doe@test.com" not in redacted
        assert "203.0.113.1" not in redacted
        assert redacted == "Failed login: user=[EMAIL_REDACTED] ip=[IP_REDACTED] time=12:00"
