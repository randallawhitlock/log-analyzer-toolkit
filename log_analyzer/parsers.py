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


class NginxAccessParser(BaseParser):
    """
    Parser for nginx access log format.
    
    Default format similar to Apache Combined Log Format.
    Example: 192.168.1.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/v1/users HTTP/1.1" 200 1234 "-" "curl/7.68.0"
    """
    
    name = "nginx_access"
    
    # nginx uses same format as Apache by default
    PATTERN = re.compile(
        r'^(?P<ip>[\d.:a-fA-F]+)\s+'      # IP address (v4 or v6)
        r'(?P<ident>\S+)\s+'               # Ident
        r'(?P<user>\S+)\s+'                # User
        r'\[(?P<timestamp>[^\]]+)\]\s+'    # Timestamp
        r'"(?P<request>[^"]*)"\s+'         # Request
        r'(?P<status>\d+)\s+'              # Status code
        r'(?P<size>\S+)'                   # Size
        r'(?:\s+"(?P<referer>[^"]*)"\s+'   # Referer (optional)
        r'"(?P<user_agent>[^"]*)")?'       # User Agent (optional)
        r'(?:\s+"(?P<forwarded>[^"]*)")?'  # X-Forwarded-For (optional)
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches nginx access log format."""
        return bool(self.PATTERN.match(line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse an nginx access log line."""
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
        elif status >= 300:
            level = 'INFO'
        else:
            level = 'DEBUG'
        
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
                'forwarded': data.get('forwarded'),
            }
        )


class JSONLogParser(BaseParser):
    """
    Parser for JSON-formatted log entries.
    
    Supports structured logging formats like those from Python's json logger,
    Node.js, or other applications that output JSON.
    
    Expected fields (all optional):
    - timestamp/time/@timestamp: Timestamp field
    - level/severity/lvl: Log level
    - message/msg: Log message
    - source/host/hostname: Source identifier
    """
    
    name = "json"
    
    import json
    
    # Common timestamp field names
    TIMESTAMP_FIELDS = ['timestamp', 'time', '@timestamp', 'ts', 'datetime']
    LEVEL_FIELDS = ['level', 'severity', 'lvl', 'log_level', 'loglevel']
    MESSAGE_FIELDS = ['message', 'msg', 'text', 'log']
    SOURCE_FIELDS = ['source', 'host', 'hostname', 'server', 'ip']
    
    def can_parse(self, line: str) -> bool:
        """Check if line is valid JSON."""
        line = line.strip()
        return line.startswith('{') and line.endswith('}')
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse a JSON log line."""
        import json
        
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return None
        
        if not isinstance(data, dict):
            return None
        
        # Extract timestamp
        timestamp = None
        for field in self.TIMESTAMP_FIELDS:
            if field in data:
                ts_value = data[field]
                timestamp = self._parse_timestamp(ts_value)
                if timestamp:
                    break
        
        # Extract level
        level = None
        for field in self.LEVEL_FIELDS:
            if field in data:
                level = str(data[field]).upper()
                break
        
        # Normalize level
        level = self._normalize_level(level)
        
        # Extract message
        message = ""
        for field in self.MESSAGE_FIELDS:
            if field in data:
                message = str(data[field])
                break
        
        # Extract source
        source = None
        for field in self.SOURCE_FIELDS:
            if field in data:
                source = str(data[field])
                break
        
        return LogEntry(
            raw=line,
            timestamp=timestamp,
            level=level,
            message=message,
            source=source,
            metadata=data
        )
    
    def _parse_timestamp(self, value: Any) -> Optional[datetime]:
        """Attempt to parse various timestamp formats."""
        if isinstance(value, (int, float)):
            # Unix timestamp
            try:
                return datetime.fromtimestamp(value)
            except (ValueError, OSError):
                pass
        
        if isinstance(value, str):
            # Try common formats
            formats = [
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        
        return None
    
    def _normalize_level(self, level: Optional[str]) -> str:
        """Normalize log level to standard values."""
        if not level:
            return 'INFO'
        
        level_map = {
            'FATAL': 'CRITICAL',
            'ERR': 'ERROR',
            'WARN': 'WARNING',
            'INFORMATION': 'INFO',
            'DBG': 'DEBUG',
            'TRACE': 'DEBUG',
        }
        
        return level_map.get(level, level)


class SyslogParser(BaseParser):
    """
    Parser for syslog format (RFC 3164 and RFC 5424).
    
    RFC 3164 Example: <34>Oct 11 22:14:15 mymachine su: 'su root' failed for lonvick
    RFC 5424 Example: <34>1 2023-10-11T22:14:15.003Z mymachine.example.com su - - 'su root' failed
    """
    
    name = "syslog"
    
    # RFC 3164 pattern
    PATTERN_3164 = re.compile(
        r'^<(?P<priority>\d+)>'           # Priority
        r'(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'  # Timestamp
        r'(?P<hostname>\S+)\s+'           # Hostname
        r'(?P<tag>\S+?)(?:\[(?P<pid>\d+)\])?:\s*'  # Tag and optional PID
        r'(?P<message>.*)$'               # Message
    )
    
    # RFC 5424 pattern
    PATTERN_5424 = re.compile(
        r'^<(?P<priority>\d+)>'           # Priority
        r'(?P<version>\d+)\s+'            # Version
        r'(?P<timestamp>\S+)\s+'          # Timestamp
        r'(?P<hostname>\S+)\s+'           # Hostname
        r'(?P<appname>\S+)\s+'            # App name
        r'(?P<procid>\S+)\s+'             # Process ID
        r'(?P<msgid>\S+)\s+'              # Message ID
        r'(?P<structured_data>-|(?:\[.+?\])+)\s+'  # Structured Data
        r'(?P<message>.*)$'               # Message
    )
    
    # Syslog severity levels (from priority)
    SEVERITY_MAP = {
        0: 'CRITICAL',  # Emergency
        1: 'CRITICAL',  # Alert
        2: 'CRITICAL',  # Critical
        3: 'ERROR',     # Error
        4: 'WARNING',   # Warning
        5: 'INFO',      # Notice
        6: 'INFO',      # Informational
        7: 'DEBUG',     # Debug
    }
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches syslog format."""
        return line.startswith('<') and '>' in line[:5]
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse a syslog line."""
        # Try RFC 5424 first (has version number)
        match = self.PATTERN_5424.match(line)
        if match:
            return self._parse_5424(match, line)
        
        # Try RFC 3164
        match = self.PATTERN_3164.match(line)
        if match:
            return self._parse_3164(match, line)
        
        return None
    
    def _parse_3164(self, match: re.Match, line: str) -> LogEntry:
        """Parse RFC 3164 syslog."""
        data = match.groupdict()
        
        priority = int(data.get('priority', 0))
        severity = priority % 8
        facility = priority // 8
        
        return LogEntry(
            raw=line,
            timestamp=None,  # 3164 timestamps need current year
            level=self.SEVERITY_MAP.get(severity, 'INFO'),
            message=data.get('message', ''),
            source=data.get('hostname'),
            metadata={
                'facility': facility,
                'severity': severity,
                'tag': data.get('tag'),
                'pid': data.get('pid'),
            }
        )
    
    def _parse_5424(self, match: re.Match, line: str) -> LogEntry:
        """Parse RFC 5424 syslog."""
        data = match.groupdict()
        
        priority = int(data.get('priority', 0))
        severity = priority % 8
        facility = priority // 8
        
        # Parse ISO timestamp
        timestamp = None
        ts_str = data.get('timestamp', '')
        if ts_str and ts_str != '-':
            try:
                timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            except ValueError:
                pass
        
        return LogEntry(
            raw=line,
            timestamp=timestamp,
            level=self.SEVERITY_MAP.get(severity, 'INFO'),
            message=data.get('message', ''),
            source=data.get('hostname'),
            metadata={
                'facility': facility,
                'severity': severity,
                'appname': data.get('appname'),
                'procid': data.get('procid'),
                'msgid': data.get('msgid'),
                'structured_data': data.get('structured_data'),
            }
        )
