"""
Log format parsers for various log types.

This module provides parsers for common log formats including Apache,
nginx, JSON, and syslog.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any


@dataclass
class LogEntry:
    """
    Represents a single parsed log entry.
    
    Attributes:
        raw: The original raw log line
        timestamp: Parsed timestamp (if available)
        level: Log level/severity (if available)
        message: The main message content
        source: Source of the log (IP, hostname, etc.)
        metadata: Additional parsed fields
    """
    raw: str
    timestamp: Optional[datetime] = None
    level: Optional[str] = None
    message: str = ""
    source: Optional[str] = None
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseParser(ABC):
    """Abstract base class for log format parsers."""
    
    name: str = "base"
    
    @abstractmethod
    def parse(self, line: str) -> Optional[LogEntry]:
        """
        Parse a single log line.
        
        Args:
            line: Raw log line to parse
            
        Returns:
            LogEntry if parsing succeeds, None if line doesn't match format
        """
        pass
    
    @abstractmethod
    def can_parse(self, line: str) -> bool:
        """
        Check if this parser can handle the given line.
        
        Args:
            line: Raw log line to check
            
        Returns:
            True if this parser can parse the line
        """
        pass


class ApacheAccessParser(BaseParser):
    """
    Parser for Apache Combined Log Format.
    
    Format: %h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-agent}i"
    Example: 192.168.1.1 - - [10/Oct/2023:13:55:36 -0700] "GET /index.html HTTP/1.1" 200 2326
    """
    
    name = "apache_access"
    
    # Regex pattern for Apache Combined Log Format
    PATTERN = re.compile(
        r'^(?P<ip>[\d.]+)\s+'           # IP address
        r'(?P<ident>\S+)\s+'             # Ident
        r'(?P<user>\S+)\s+'              # User
        r'\[(?P<timestamp>[^\]]+)\]\s+'  # Timestamp
        r'"(?P<request>[^"]*)"\s+'       # Request
        r'(?P<status>\d+)\s+'            # Status code
        r'(?P<size>\S+)'                 # Size
        r'(?:\s+"(?P<referer>[^"]*)"\s+' # Referer (optional)
        r'"(?P<user_agent>[^"]*)")?'     # User Agent (optional)
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches Apache access log format."""
        return bool(self.PATTERN.match(line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse an Apache access log line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        
        # Parse timestamp
        timestamp = None
        try:
            timestamp = datetime.strptime(
                data['timestamp'], 
                '%d/%b/%Y:%H:%M:%S %z'
            )
        except (ValueError, TypeError):
            pass
        
        # Determine level based on status code
        status = int(data.get('status', 0))
        if status >= 500:
            level = 'ERROR'
        elif status >= 400:
            level = 'WARNING'
        else:
            level = 'INFO'
        
        return LogEntry(
            raw=line,
            timestamp=timestamp,
            level=level,
            message=data.get('request', ''),
            source=data.get('ip'),
            metadata={
                'status': status,
                'size': data.get('size'),
                'user': data.get('user'),
                'referer': data.get('referer'),
                'user_agent': data.get('user_agent'),
            }
        )


class ApacheErrorParser(BaseParser):
    """
    Parser for Apache Error Log Format.
    
    Example: [Sat Oct 10 13:55:36.123456 2023] [core:error] [pid 1234] [client 192.168.1.1:12345] Error message
    """
    
    name = "apache_error"
    
    PATTERN = re.compile(
        r'^\[(?P<timestamp>[^\]]+)\]\s+'     # Timestamp
        r'\[(?P<module>\w+):(?P<level>\w+)\]\s+'  # Module:Level
        r'(?:\[pid\s+(?P<pid>\d+)\]\s+)?'    # PID (optional)
        r'(?:\[client\s+(?P<client>[^\]]+)\]\s+)?'  # Client (optional)
        r'(?P<message>.+)$'                   # Message
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches Apache error log format."""
        return bool(self.PATTERN.match(line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse an Apache error log line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        
        # Map Apache error levels to standard levels
        level_map = {
            'emerg': 'CRITICAL',
            'alert': 'CRITICAL', 
            'crit': 'CRITICAL',
            'error': 'ERROR',
            'warn': 'WARNING',
            'notice': 'INFO',
            'info': 'INFO',
            'debug': 'DEBUG',
        }
        
        level = level_map.get(data.get('level', '').lower(), 'INFO')
        
        return LogEntry(
            raw=line,
            timestamp=None,  # Apache error timestamps vary, handle later
            level=level,
            message=data.get('message', ''),
            source=data.get('client'),
            metadata={
                'module': data.get('module'),
                'pid': data.get('pid'),
            }
        )
