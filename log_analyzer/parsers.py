"""
Log format parsers for various log types.

This module provides parsers for common log formats including Apache,
nginx, JSON, and syslog.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Any
import json


__all__ = [
    "LogEntry",
    "BaseParser",
    "AWSCloudWatchParser",
    "GCPCloudLoggingParser",
    "AzureMonitorParser",
    "DockerJSONParser",
    "KubernetesParser",
    "ContainerdParser",
    "ApacheAccessParser",
    "ApacheErrorParser",
    "NginxAccessParser",
    "NginxParser",
    "JSONLogParser",
    "SyslogParser",
    "AndroidParser",
    "JavaLogParser",
    "HDFSParser",
    "SupercomputerParser",
    "WindowsEventParser",
    "ProxifierParser",
    "HPCParser",
    "HealthAppParser",
    "OpenStackParser",
    "SquidParser",
    "UniversalFallbackParser",
    "CustomParserRegistry",
]


@dataclass
class LogEntry:
    """
    Represents a single parsed log entry.

    Attributes:
        raw: The original raw log line (optional, defaults to empty for memory efficiency)
        timestamp: Parsed timestamp (if available)
        level: Log level/severity (if available)
        message: The main message content
        source: Source of the log (IP, hostname, etc.)
        metadata: Additional parsed fields
    """
    raw: str = ""
    timestamp: Optional[datetime] = None
    level: Optional[str] = None
    message: str = ""
    source: Optional[str] = None
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


# Cloud provider severity mapping
GCP_SEVERITY_MAP = {
    'DEFAULT': 'INFO',
    'DEBUG': 'DEBUG',
    'INFO': 'INFO',
    'NOTICE': 'INFO',
    'WARNING': 'WARNING',
    'ERROR': 'ERROR',
    'CRITICAL': 'CRITICAL',
    'ALERT': 'CRITICAL',
    'EMERGENCY': 'CRITICAL',
}

# Azure severity level mapping (numeric)
AZURE_SEVERITY_MAP = {
    0: 'DEBUG',    # Verbose
    1: 'INFO',     # Information
    2: 'WARNING',  # Warning
    3: 'ERROR',    # Error
    4: 'CRITICAL', # Critical
}


def parse_cloud_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse cloud provider timestamps (ISO8601, RFC3339, Unix ms).

    Supports:
    - ISO8601: 2020-01-01T00:00:00Z, 2020-01-01T00:00:00.000Z
    - RFC3339Nano: 2020-01-01T00:00:00.000000000Z
    - Unix milliseconds: 1577836800000

    Args:
        timestamp_str: Timestamp string to parse

    Returns:
        datetime object with UTC timezone, or None if parsing fails
    """
    if not timestamp_str:
        return None

    # Try Unix milliseconds (AWS CloudWatch format)
    if timestamp_str.isdigit():
        try:
            return datetime.fromtimestamp(int(timestamp_str) / 1000, tz=timezone.utc)
        except (ValueError, OSError):
            pass

    # Handle RFC3339Nano (nanoseconds) - truncate to microseconds
    if '.' in timestamp_str and 'Z' in timestamp_str:
        try:
            # Split into date-time and fractional seconds
            parts = timestamp_str.split('.')
            if len(parts) == 2:
                fractional = parts[1].rstrip('Z')
                # Truncate to 6 digits (microseconds) if longer
                if len(fractional) > 6:
                    fractional = fractional[:6]
                # Reconstruct timestamp
                timestamp_str = f"{parts[0]}.{fractional}Z"
        except (ValueError, IndexError):
            pass

    # Try ISO8601/RFC3339 formats
    formats = [
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%S%z',
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(timestamp_str, fmt)
            # Ensure timezone aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue

    return None


def extract_level_from_message(message: str) -> Optional[str]:
    """
    Extract log level from message content using common patterns.

    Args:
        message: Message text to search

    Returns:
        Extracted level (CRITICAL, ERROR, WARNING, INFO, DEBUG) or None
    """
    if not message:
        return None

    message_upper = message.upper()

    # Check for common level indicators
    if any(indicator in message_upper for indicator in ['FATAL', 'CRITICAL', 'CRIT']):
        return 'CRITICAL'
    if 'ERROR' in message_upper or 'ERR' in message_upper:
        return 'ERROR'
    if any(indicator in message_upper for indicator in ['WARN', 'WARNING']):
        return 'WARNING'
    if 'INFO' in message_upper:
        return 'INFO'
    if 'DEBUG' in message_upper:
        return 'DEBUG'

    # Check for bracketed levels like [ERROR] or [INFO]
    level_match = re.search(r'\[(CRITICAL|ERROR|WARN|WARNING|INFO|DEBUG)\]', message_upper)
    if level_match:
        level = level_match.group(1)
        return 'WARNING' if level == 'WARN' else level

    return None


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


# ============================================================================
# Cloud Provider Parsers
# ============================================================================

class AWSCloudWatchParser(BaseParser):
    """
    Parser for AWS CloudWatch Logs format.

    Supports both JSON batch format and plain text export format.

    JSON format example:
        {"messageType":"DATA_MESSAGE","logGroup":"/aws/lambda/func",
         "logEvents":[{"timestamp":1421116133213,"message":"Hello"}]}

    Plain text export format example:
        2020-01-01T00:00:00.000Z [INFO] Application started
    """

    name = "aws_cloudwatch"

    # JSON keys that identify CloudWatch logs
    JSON_KEYS = {'logEvents', 'logGroup', 'logStream'}

    # Plain text pattern for CloudWatch exports
    PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)\s+'
        r'(?:\[(?P<level>\w+)\]\s+)?'
        r'(?P<message>.+)$'
    )

    def can_parse(self, line: str) -> bool:
        """Check if line matches AWS CloudWatch format."""
        line = line.strip()

        # Try JSON format first
        if line.startswith('{'):
            try:
                data = json.loads(line)
                return any(key in data for key in self.JSON_KEYS)
            except (json.JSONDecodeError, ValueError):
                pass

        # Try plain text format
        return bool(self.PATTERN.match(line))

    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse AWS CloudWatch log line."""
        line = line.strip()

        # Try JSON format first
        if line.startswith('{'):
            try:
                data = json.loads(line)
                if 'logEvents' in data:
                    # Batch format - parse first event
                    events = data.get('logEvents', [])
                    if events:
                        return self._parse_event(
                            events[0],
                            log_group=data.get('logGroup'),
                            log_stream=data.get('logStream')
                        )
                elif 'message' in data:
                    # Single event format
                    return self._parse_event(data)
            except (json.JSONDecodeError, ValueError, KeyError):
                pass

        # Try plain text format
        match = self.PATTERN.match(line)
        if match:
            data = match.groupdict()
            timestamp = parse_cloud_timestamp(data['timestamp'])
            level = data.get('level') or extract_level_from_message(data['message'])

            return LogEntry(
                raw=line,
                timestamp=timestamp,
                level=level.upper() if level else 'INFO',
                message=data['message'],
                metadata={'parser_type': 'aws_cloudwatch_text'}
            )

        return None

    def _parse_event(self, event: dict, log_group=None, log_stream=None) -> Optional[LogEntry]:
        """Parse CloudWatch event object."""
        message = event.get('message', '')
        timestamp_ms = event.get('timestamp')

        # Parse timestamp (Unix milliseconds)
        timestamp = None
        if timestamp_ms:
            timestamp = parse_cloud_timestamp(str(timestamp_ms))

        # Extract level from message
        level = extract_level_from_message(message) or 'INFO'

        # Build metadata
        metadata = {'parser_type': 'aws_cloudwatch_json'}
        if log_group:
            metadata['log_group'] = log_group
        if log_stream:
            metadata['log_stream'] = log_stream

        # Extract request ID if present (Lambda format)
        request_id_match = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', message)
        if request_id_match:
            metadata['request_id'] = request_id_match.group(1)

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message.strip(),
            source=log_group,
            metadata=metadata
        )


class GCPCloudLoggingParser(BaseParser):
    """
    Parser for Google Cloud Logging (Stackdriver) format.

    JSON format with fields like severity, timestamp, textPayload/jsonPayload,
    resource, labels, logName, etc.

    Example:
        {"timestamp":"2020-01-01T00:00:00Z","severity":"ERROR",
         "textPayload":"Connection failed","resource":{"type":"gce_instance"}}
    """

    name = "gcp_logging"

    # Required/identifying fields for GCP logs
    GCP_KEYS = {'severity', 'timestamp'}

    def can_parse(self, line: str) -> bool:
        """Check if line matches GCP Cloud Logging format."""
        line = line.strip()
        if not line.startswith('{'):
            return False

        try:
            data = json.loads(line)
            # Must have severity and timestamp fields
            return all(key in data for key in self.GCP_KEYS)
        except (json.JSONDecodeError, ValueError):
            return False

    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse GCP Cloud Logging log line."""
        try:
            data = json.loads(line.strip())
        except (json.JSONDecodeError, ValueError):
            return None

        # Validate required fields (must have both severity and timestamp)
        if 'severity' not in data or 'timestamp' not in data:
            return None

        # Extract timestamp
        timestamp_str = data.get('timestamp')
        timestamp = parse_cloud_timestamp(timestamp_str) if timestamp_str else None

        # Extract severity and map to standard levels
        severity = data.get('severity', 'INFO').upper()
        level = GCP_SEVERITY_MAP.get(severity, severity)

        # Extract message from textPayload or jsonPayload
        message = ''
        if 'textPayload' in data:
            message = data['textPayload']
        elif 'jsonPayload' in data:
            payload = data['jsonPayload']
            # Try to get 'message' or 'msg' field, or serialize the whole payload
            if isinstance(payload, dict):
                message = payload.get('message') or payload.get('msg') or json.dumps(payload)
            else:
                message = str(payload)

        # Extract source from resource.type
        source = None
        resource = data.get('resource', {})
        if isinstance(resource, dict):
            source = resource.get('type')

        # Build metadata
        metadata = {'parser_type': 'gcp_logging'}

        # Add resource labels
        if isinstance(resource, dict) and 'labels' in resource:
            resource_labels = resource['labels']
            if isinstance(resource_labels, dict):
                metadata['resource_labels'] = resource_labels
                # Extract common fields
                if 'pod_name' in resource_labels:
                    metadata['pod_name'] = resource_labels['pod_name']
                if 'namespace_name' in resource_labels:
                    metadata['namespace'] = resource_labels['namespace_name']
                if 'instance_id' in resource_labels:
                    metadata['instance_id'] = resource_labels['instance_id']

        # Add log-level labels
        if 'labels' in data and isinstance(data['labels'], dict):
            metadata['labels'] = data['labels']

        # Add logName
        if 'logName' in data:
            metadata['log_name'] = data['logName']

        # Add trace/span IDs if present
        if 'trace' in data:
            metadata['trace'] = data['trace']
        if 'spanId' in data:
            metadata['span_id'] = data['spanId']

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message.strip() if message else '',
            source=source,
            metadata=metadata
        )


class AzureMonitorParser(BaseParser):
    """
    Parser for Azure Monitor and Application Insights logs.

    Supports both string-based and numeric severity levels.

    Application Insights format:
        {"time":"2020-01-01T00:00:00.000Z","level":"Error","message":"Failed"}

    Log Analytics format:
        {"TimeGenerated":"2020-01-01T00:00:00.000Z","Computer":"vm-01",
         "SeverityLevel":3,"Message":"Service unavailable"}
    """

    name = "azure_monitor"

    # Identifying field combinations
    TIME_FIELDS = {'time', 'TimeGenerated'}
    LEVEL_FIELDS = {'level', 'SeverityLevel'}

    def can_parse(self, line: str) -> bool:
        """Check if line matches Azure Monitor format."""
        line = line.strip()

        # Handle JSON array format
        if line.startswith('['):
            try:
                data = json.loads(line)
                if isinstance(data, list) and data:
                    # Check first element
                    item = data[0]
                    return self._has_azure_fields(item)
            except (json.JSONDecodeError, ValueError):
                return False

        # Handle single JSON object
        if line.startswith('{'):
            try:
                data = json.loads(line)
                return self._has_azure_fields(data)
            except (json.JSONDecodeError, ValueError):
                return False

        return False

    def _has_azure_fields(self, data: dict) -> bool:
        """Check if data has Azure Monitor identifying fields."""
        if not isinstance(data, dict):
            return False
        # Must have a time field and either level or SeverityLevel
        has_time = any(field in data for field in self.TIME_FIELDS)
        has_level = any(field in data for field in self.LEVEL_FIELDS)
        return has_time and has_level

    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse Azure Monitor log line."""
        line = line.strip()

        # Handle JSON array (take first element)
        if line.startswith('['):
            try:
                data = json.loads(line)
                if isinstance(data, list) and data:
                    return self._parse_entry(data[0])
            except (json.JSONDecodeError, ValueError):
                return None

        # Handle single JSON object
        if line.startswith('{'):
            try:
                data = json.loads(line)
                return self._parse_entry(data)
            except (json.JSONDecodeError, ValueError):
                return None

        return None

    def _parse_entry(self, data: dict) -> Optional[LogEntry]:
        """Parse single Azure Monitor entry."""
        if not isinstance(data, dict):
            return None

        # Extract timestamp (try both field names)
        timestamp_str = data.get('time') or data.get('TimeGenerated')
        timestamp = parse_cloud_timestamp(timestamp_str) if timestamp_str else None

        # Extract level (string or numeric)
        level = 'INFO'
        if 'level' in data:
            # String level (Application Insights)
            level_str = data['level']
            if isinstance(level_str, str):
                level_upper = level_str.upper()
                if level_upper == 'ERROR':
                    level = 'ERROR'
                elif level_upper in ('WARN', 'WARNING'):
                    level = 'WARNING'
                elif level_upper in ('INFO', 'INFORMATION'):
                    level = 'INFO'
                elif level_upper in ('CRITICAL', 'FATAL'):
                    level = 'CRITICAL'
                elif level_upper == 'DEBUG' or level_upper == 'VERBOSE':
                    level = 'DEBUG'
        elif 'SeverityLevel' in data:
            # Numeric level (Log Analytics)
            severity_num = data['SeverityLevel']
            if isinstance(severity_num, int):
                level = AZURE_SEVERITY_MAP.get(severity_num, 'INFO')

        # Extract message (try different field names)
        message = data.get('message') or data.get('Message') or ''

        # Extract source (Computer field or category)
        source = data.get('Computer') or data.get('category')

        # Build metadata
        metadata = {'parser_type': 'azure_monitor'}

        # Add operation name if present
        if 'operationName' in data:
            metadata['operation'] = data['operationName']

        # Add category
        if 'category' in data:
            metadata['category'] = data['category']

        # Add properties/AdditionalContext
        if 'properties' in data and isinstance(data['properties'], dict):
            metadata['properties'] = data['properties']
        if 'AdditionalContext' in data and isinstance(data['AdditionalContext'], dict):
            metadata['additional_context'] = data['AdditionalContext']

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message.strip() if message else '',
            source=source,
            metadata=metadata
        )


# ============================================================================
# Container Runtime Parsers
# ============================================================================

class DockerJSONParser(BaseParser):
    """
    Parser for Docker container JSON logs.

    Format: {"log":"message\\n","stream":"stdout","time":"2019-01-01T11:11:11.111111111Z"}

    The log field contains the actual message, stream is stdout/stderr,
    and time is RFC3339Nano timestamp.
    """

    name = "docker_json"

    # Required fields for Docker JSON logs
    DOCKER_KEYS = {'log', 'stream', 'time'}

    def can_parse(self, line: str) -> bool:
        """Check if line matches Docker JSON log format."""
        line = line.strip()
        if not line.startswith('{'):
            return False

        try:
            data = json.loads(line)
            return all(key in data for key in self.DOCKER_KEYS)
        except (json.JSONDecodeError, ValueError):
            return False

    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse Docker JSON log line."""
        try:
            data = json.loads(line.strip())
        except (json.JSONDecodeError, ValueError):
            return None

        # Extract fields
        log_message = data.get('log', '').rstrip('\n')
        stream = data.get('stream', 'stdout')
        time_str = data.get('time')

        # Parse timestamp
        timestamp = parse_cloud_timestamp(time_str) if time_str else None

        # Extract level from message content
        level = extract_level_from_message(log_message)

        # Default level based on stream if not found in message
        if not level:
            level = 'WARNING' if stream == 'stderr' else 'INFO'

        # Build metadata
        metadata = {
            'parser_type': 'docker_json',
            'stream': stream
        }

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=log_message,
            source=stream,
            metadata=metadata
        )


class KubernetesParser(BaseParser):
    """
    Parser for Kubernetes pod logs.

    Supports both CRI format and Docker JSON format:
    - CRI: "2020-01-01T00:00:00.000000000Z stdout F [INFO] Message"
    - JSON: {"log":"message\\n","stream":"stdout","time":"2020-01-01T00:00:00Z"}

    CRI format: TIMESTAMP STREAM FLAG MESSAGE
    - STREAM: stdout or stderr
    - FLAG: F (full line) or P (partial line)
    """

    name = "kubernetes"

    # CRI format pattern
    CRI_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+'
        r'(?P<stream>stdout|stderr)\s+'
        r'(?P<flag>[FP])\s+'
        r'(?P<message>.*)$'
    )

    def can_parse(self, line: str) -> bool:
        """Check if line matches Kubernetes log format."""
        line = line.strip()

        # Try CRI format
        if self.CRI_PATTERN.match(line):
            return True

        # Try Docker JSON format (also used by Kubernetes)
        if line.startswith('{'):
            try:
                data = json.loads(line)
                # Must have log, stream, and time fields
                return all(key in data for key in ['log', 'stream', 'time'])
            except (json.JSONDecodeError, ValueError):
                return False

        return False

    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse Kubernetes log line."""
        line = line.strip()

        # Try CRI format first
        match = self.CRI_PATTERN.match(line)
        if match:
            data = match.groupdict()

            timestamp = parse_cloud_timestamp(data['timestamp'])
            stream = data['stream']
            flag = data['flag']
            message = data['message']

            # Extract level from message
            level = extract_level_from_message(message)

            # Default based on stream if not found
            if not level:
                level = 'WARNING' if stream == 'stderr' else 'INFO'

            metadata = {
                'parser_type': 'kubernetes_cri',
                'stream': stream,
                'flag': flag,  # F=full, P=partial
            }

            return LogEntry(
                timestamp=timestamp,
                level=level,
                message=message,
                source=stream,
                metadata=metadata
            )

        # Try Docker JSON format
        if line.startswith('{'):
            try:
                data = json.loads(line)
                if all(key in data for key in ['log', 'stream', 'time']):
                    log_message = data['log'].rstrip('\n')
                    stream = data['stream']
                    time_str = data['time']

                    timestamp = parse_cloud_timestamp(time_str)
                    level = extract_level_from_message(log_message)

                    if not level:
                        level = 'WARNING' if stream == 'stderr' else 'INFO'

                    metadata = {
                        'parser_type': 'kubernetes_json',
                        'stream': stream
                    }

                    return LogEntry(
                        timestamp=timestamp,
                        level=level,
                        message=log_message,
                        source=stream,
                        metadata=metadata
                    )
            except (json.JSONDecodeError, ValueError):
                pass

        return None


class ContainerdParser(BaseParser):
    """
    Parser for containerd CRI logs.

    Format: TIMESTAMP STREAM FLAG MESSAGE

    Example text: "2020-01-01T00:00:00.000000000Z stdout F [INFO] Service started"
    Example with JSON message:
        "2020-01-01T00:00:00.000000000Z stdout F {"level":"info","msg":"Started"}"
    """

    name = "containerd"

    # CRI format pattern (same as Kubernetes, but containerd-specific)
    CRI_PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)\s+'
        r'(?P<stream>stdout|stderr)\s+'
        r'(?P<flag>[FP])\s+'
        r'(?P<message>.*)$'
    )

    def can_parse(self, line: str) -> bool:
        """Check if line matches containerd CRI log format."""
        line = line.strip()

        # CRI format with optional JSON message
        match = self.CRI_PATTERN.match(line)
        if match:
            # This is CRI format - could be containerd or kubernetes
            # Containerd logs often have JSON payloads or [INFO] style messages
            message = match.group('message')
            # Heuristic: if message looks like structured JSON or has component field,
            # likely containerd. Otherwise, might be generic CRI.
            if message.strip().startswith('{'):
                try:
                    data = json.loads(message.strip())
                    # Common containerd JSON fields
                    if any(k in data for k in ['component', 'level', 'msg']):
                        return True
                except (json.JSONDecodeError, ValueError):
                    pass
            # Also match if it has [INFO] style prefix or specific patterns
            if '[INFO]' in message or 'plugin/' in message or 'component' in message:
                return True

        return False

    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse containerd CRI log line."""
        line = line.strip()

        match = self.CRI_PATTERN.match(line)
        if not match:
            return None

        data = match.groupdict()
        timestamp = parse_cloud_timestamp(data['timestamp'])
        stream = data['stream']
        flag = data['flag']
        message = data['message']

        level = None
        source = None
        metadata = {
            'parser_type': 'containerd_cri',
            'stream': stream,
            'flag': flag,
        }

        # Try to parse message as JSON
        if message.strip().startswith('{'):
            try:
                json_msg = json.loads(message.strip())
                if isinstance(json_msg, dict):
                    # Extract level from JSON
                    if 'level' in json_msg:
                        level_str = json_msg['level'].upper()
                        if level_str in ['INFO', 'DEBUG', 'WARN', 'WARNING', 'ERROR', 'CRITICAL']:
                            level = 'WARNING' if level_str == 'WARN' else level_str

                    # Extract component as source
                    if 'component' in json_msg:
                        source = json_msg['component']
                        metadata['component'] = json_msg['component']

                    # Use 'msg' field as message if present
                    if 'msg' in json_msg:
                        message = json_msg['msg']

                    # Store full JSON in metadata
                    metadata['json_data'] = json_msg
            except (json.JSONDecodeError, ValueError):
                pass

        # If level not found in JSON, extract from message text
        if not level:
            level = extract_level_from_message(message)

        # Default level based on stream if still not found
        if not level:
            level = 'WARNING' if stream == 'stderr' else 'INFO'

        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=message.strip(),
            source=source or stream,
            metadata=metadata
        )


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
    
    Modern: [Sat Oct 10 13:55:36.123456 2023] [core:error] [pid 1234] [client 192.168.1.1:12345] Error message
    Legacy: [Sun Dec 04 04:47:44 2005] [error] message
    """
    
    name = "apache_error"
    
    # Modern format with module:level
    PATTERN = re.compile(
        r'^\[(?P<timestamp>[^\]]+)\]\s+'     # Timestamp
        r'\[(?P<module>\w+):(?P<level>\w+)\]\s+'  # Module:Level
        r'(?:\[pid\s+(?P<pid>\d+)\]\s+)?'    # PID (optional)
        r'(?:\[client\s+(?P<client>[^\]]+)\]\s+)?'  # Client (optional)
        r'(?P<message>.+)$'                   # Message
    )
    
    # Legacy format with just level (no module)
    PATTERN_LEGACY = re.compile(
        r'^\[(?P<timestamp>[^\]]+)\]\s+'     # Timestamp
        r'\[(?P<level>\w+)\]\s+'             # Level only
        r'(?P<message>.+)$'                   # Message
    )
    
    LEVEL_MAP = {
        'emerg': 'CRITICAL',
        'alert': 'CRITICAL', 
        'crit': 'CRITICAL',
        'error': 'ERROR',
        'warn': 'WARNING',
        'notice': 'INFO',
        'info': 'INFO',
        'debug': 'DEBUG',
    }
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches Apache error log format."""
        return bool(self.PATTERN.match(line) or self.PATTERN_LEGACY.match(line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse an Apache error log line."""
        # Try modern format first
        match = self.PATTERN.match(line)
        if match:
            data = match.groupdict()
            level = self.LEVEL_MAP.get(data.get('level', '').lower(), 'INFO')
            
            return LogEntry(
                    timestamp=None,
                level=level,
                message=data.get('message', ''),
                source=data.get('client'),
                metadata={
                    'module': data.get('module'),
                    'pid': data.get('pid'),
                }
            )
        
        # Try legacy format
        match = self.PATTERN_LEGACY.match(line)
        if match:
            data = match.groupdict()
            level = self.LEVEL_MAP.get(data.get('level', '').lower(), 'INFO')
            
            return LogEntry(
                    timestamp=None,
                level=level,
                message=data.get('message', ''),
                source=None,
                metadata={}
            )
        
        return None


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
    
    # BSD syslog pattern (common format without priority, used by many log analyzers)
    PATTERN_BSD = re.compile(
        r'^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'  # Timestamp
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
        # Check for RFC format with priority
        if line.startswith('<') and '>' in line[:5]:
            return True
        # Check for BSD format (starts with month abbreviation)
        if len(line) > 15 and line[:3] in ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'):
            return True
        return False
    
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
        
        # Try BSD syslog (no priority field)
        match = self.PATTERN_BSD.match(line)
        if match:
            return self._parse_bsd(match, line)
        
        return None
    
    def _parse_bsd(self, match: re.Match, line: str) -> LogEntry:
        """Parse BSD-style syslog (without priority)."""
        data = match.groupdict()
        
        # Infer severity from message keywords
        message = data.get('message', '')
        level = 'INFO'
        msg_lower = message.lower()
        if 'error' in msg_lower or 'fail' in msg_lower or 'denied' in msg_lower:
            level = 'ERROR'
        elif 'warn' in msg_lower:
            level = 'WARNING'
        elif 'debug' in msg_lower:
            level = 'DEBUG'
        
        return LogEntry(
            timestamp=None,  # BSD timestamps need current year
            level=level,
            message=message,
            source=data.get('hostname'),
            metadata={
                'tag': data.get('tag'),
                'pid': data.get('pid'),
            }
        )
    
    def _parse_3164(self, match: re.Match, line: str) -> LogEntry:
        """Parse RFC 3164 syslog."""
        data = match.groupdict()
        
        priority = int(data.get('priority', 0))
        severity = priority % 8
        facility = priority // 8
        
        return LogEntry(
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


class AndroidParser(BaseParser):
    """
    Parser for Android Logcat format.
    
    Example: 03-17 16:13:38.811  1702  2395 D WindowManager: message
    """
    
    name = "android"
    
    PATTERN = re.compile(
        r'^(?P<month>\d{2})-(?P<day>\d{2})\s+'
        r'(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+'
        r'(?P<pid>\d+)\s+(?P<tid>\d+)\s+'
        r'(?P<level>[VDIWEF])\s+'
        r'(?P<tag>\S+?):\s*'
        r'(?P<message>.*)$'
    )
    
    LEVEL_MAP = {
        'V': 'DEBUG',
        'D': 'DEBUG',
        'I': 'INFO',
        'W': 'WARNING',
        'E': 'ERROR',
        'F': 'CRITICAL',
    }
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches Android logcat format."""
        return bool(re.match(r'^\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3}', line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse an Android logcat line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        level = self.LEVEL_MAP.get(data.get('level', 'I'), 'INFO')
        
        return LogEntry(
            timestamp=None,  # Would need year for full timestamp
            level=level,
            message=data.get('message', ''),
            source=data.get('tag'),
            metadata={
                'pid': data.get('pid'),
                'tid': data.get('tid'),
                'tag': data.get('tag'),
            }
        )


class JavaLogParser(BaseParser):
    """
    Parser for Java log4j style logs (Hadoop, Spark, Zookeeper).
    
    Examples:
    - 2015-10-18 18:01:47,978 INFO [main] org.apache.hadoop...: msg
    - 17/06/09 20:10:40 INFO executor.CoarseGrainedExecutorBackend: msg
    - 2015-07-29 17:41:44,747 - INFO  [QuorumPeer...] - msg
    """
    
    name = "java_log"
    
    # Full timestamp format (Hadoop, Zookeeper)
    PATTERN_FULL = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*'
        r'[-]?\s*'
        r'(?P<level>INFO|WARN|ERROR|DEBUG|TRACE|FATAL)\s+'
        r'(?:\[(?P<thread>[^\]]+)\]\s+)?'
        r'(?P<class>\S+?):\s*'
        r'(?P<message>.*)$'
    )
    
    # Short timestamp format (Spark: YY/MM/DD)
    PATTERN_SHORT = re.compile(
        r'^(?P<timestamp>\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s+'
        r'(?P<level>INFO|WARN|ERROR|DEBUG|TRACE|FATAL)\s+'
        r'(?P<class>\S+?):\s*'
        r'(?P<message>.*)$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches Java log format."""
        # Check for full timestamp
        if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}', line):
            return True
        # Check for short timestamp (Spark)
        if re.match(r'^\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}', line):
            return True
        return False
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse a Java log line."""
        # Try full format first
        match = self.PATTERN_FULL.match(line)
        if match:
            return self._parse_match(match, line)
        
        # Try short format
        match = self.PATTERN_SHORT.match(line)
        if match:
            return self._parse_match(match, line)
        
        return None
    
    def _parse_match(self, match: re.Match, line: str) -> LogEntry:
        """Parse matched data into LogEntry."""
        data = match.groupdict()
        level = data.get('level', 'INFO').upper()
        if level == 'WARN':
            level = 'WARNING'
        elif level == 'FATAL':
            level = 'CRITICAL'
        
        return LogEntry(
            timestamp=None,
            level=level,
            message=data.get('message', ''),
            source=data.get('class'),
            metadata={
                'thread': data.get('thread'),
                'class': data.get('class'),
            }
        )


class HDFSParser(BaseParser):
    """
    Parser for HDFS compact log format.
    
    Example: 081109 203615 148 INFO dfs.DataNode$PacketResponder: msg
    """
    
    name = "hdfs"
    
    PATTERN = re.compile(
        r'^(?P<date>\d{6})\s+'
        r'(?P<time>\d{6})\s+'
        r'(?P<id>\d+)\s+'
        r'(?P<level>INFO|WARN|ERROR|DEBUG|TRACE|FATAL)\s+'
        r'(?P<class>\S+?):\s*'
        r'(?P<message>.*)$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches HDFS format."""
        return bool(re.match(r'^\d{6}\s+\d{6}\s+\d+\s+(?:INFO|WARN|ERROR|DEBUG)', line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse an HDFS log line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        level = data.get('level', 'INFO').upper()
        if level == 'WARN':
            level = 'WARNING'
        
        return LogEntry(
            timestamp=None,
            level=level,
            message=data.get('message', ''),
            source=data.get('class'),
            metadata={
                'id': data.get('id'),
                'class': data.get('class'),
            }
        )


class SupercomputerParser(BaseParser):
    """
    Parser for supercomputer logs (BGL, Thunderbird).
    
    Example: - 1117838570 2005.06.03 R02-M1-N0 2005-06-03-15.42.50 R02 RAS KERNEL INFO msg
    """
    
    name = "supercomputer"
    
    # BGL format
    PATTERN_BGL = re.compile(
        r'^-\s+'
        r'(?P<timestamp>\d+)\s+'
        r'(?P<date>\d{4}\.\d{2}\.\d{2})\s+'
        r'(?P<node>\S+)\s+'
        r'(?P<datetime>\S+)\s+'
        r'(?P<node2>\S+)\s+'
        r'(?P<type>\S+)\s+'
        r'(?P<component>\S+)\s+'
        r'(?P<level>\S+)\s+'
        r'(?P<message>.*)$'
    )
    
    # Thunderbird format (has syslog-like content after prefix)
    PATTERN_THUNDER = re.compile(
        r'^-\s+'
        r'(?P<timestamp>\d+)\s+'
        r'(?P<date>\d{4}\.\d{2}\.\d{2})\s+'
        r'(?P<node>\S+)\s+'
        r'(?P<syslog_data>.*)$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches supercomputer format."""
        return line.startswith('- ') and re.match(r'^-\s+\d+\s+\d{4}\.\d{2}\.\d{2}', line)
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse a supercomputer log line."""
        # Try BGL format first
        match = self.PATTERN_BGL.match(line)
        if match:
            data = match.groupdict()
            level = data.get('level', 'INFO').upper()
            if level not in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
                level = 'INFO'
            
            return LogEntry(
                    timestamp=None,
                level=level,
                message=data.get('message', ''),
                source=data.get('node'),
                metadata={
                    'type': data.get('type'),
                    'component': data.get('component'),
                }
            )
        
        # Try Thunderbird format
        match = self.PATTERN_THUNDER.match(line)
        if match:
            data = match.groupdict()
            syslog_data = data.get('syslog_data', '')
            
            # Infer level from message
            level = 'INFO'
            if 'error' in syslog_data.lower() or 'fail' in syslog_data.lower():
                level = 'ERROR'
            elif 'warn' in syslog_data.lower():
                level = 'WARNING'
            
            return LogEntry(
                    timestamp=None,
                level=level,
                message=syslog_data,
                source=data.get('node'),
                metadata={}
            )
        
        return None


class WindowsEventParser(BaseParser):
    """
    Parser for Windows CBS/CSI logs.
    
    Example: 2016-09-28 04:30:30, Info CBS Loaded Servicing Stack...
    """
    
    name = "windows"
    
    PATTERN = re.compile(
        r'^(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}),\s*'
        r'(?P<level>\w+)\s+'
        r'(?P<component>\w+)\s+'
        r'(?P<message>.*)$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches Windows event format."""
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\s*\w+', line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse a Windows event log line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        level = data.get('level', 'Info').upper()
        if level == 'INFO':
            level = 'INFO'
        elif level in ('WARN', 'WARNING'):
            level = 'WARNING'
        elif level == 'ERROR':
            level = 'ERROR'
        else:
            level = 'INFO'
        
        return LogEntry(
            timestamp=None,
            level=level,
            message=data.get('message', ''),
            source=data.get('component'),
            metadata={
                'component': data.get('component'),
            }
        )


class ProxifierParser(BaseParser):
    """
    Parser for Proxifier logs.
    
    Example: [10.30 16:49:06] chrome.exe - proxy.cse.cuhk.edu.hk:5070 open through proxy
    """
    
    name = "proxifier"
    
    PATTERN = re.compile(
        r'^\[(?P<date>\d+\.\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\]\s+'
        r'(?P<process>\S+)(?:\s+\*\d+)?\s+-\s+'
        r'(?P<message>.*)$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches Proxifier format."""
        return line.startswith('[') and bool(re.match(r'^\[\d+\.\d+\s+\d{2}:\d{2}:\d{2}\]', line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse a Proxifier log line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        message = data.get('message', '')
        
        # Infer level from message
        level = 'INFO'
        if 'error' in message.lower() or 'fail' in message.lower():
            level = 'ERROR'
        elif 'close' in message.lower():
            level = 'DEBUG'
        
        return LogEntry(
            timestamp=None,
            level=level,
            message=message,
            source=data.get('process'),
            metadata={
                'process': data.get('process'),
            }
        )


class HPCParser(BaseParser):
    """
    Parser for HPC (High Performance Computing) logs.
    
    Example: 134681 node-246 unix.hw state_change.unavailable 1077804742 1 msg
    """
    
    name = "hpc"
    
    PATTERN = re.compile(
        r'^(?P<id>\d+)\s+'
        r'(?P<node>\S+)\s+'
        r'(?P<category>\S+)\s+'
        r'(?P<event>\S+)\s+'
        r'(?P<timestamp>\d+)\s+'
        r'(?P<flag>\d+)\s+'
        r'(?P<message>.*)$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches HPC format."""
        # Matches: ID node/gige category.subcategory timestamp flag message
        return bool(re.match(r'^\d+\s+(?:node-\d+|gige\d+)\s+\w+(?:\.\w+)?', line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse an HPC log line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        event = data.get('event', '')
        
        # Infer level from event name
        level = 'INFO'
        if 'unavailable' in event or 'error' in event:
            level = 'ERROR'
        elif 'warning' in event:
            level = 'WARNING'
        
        return LogEntry(
            timestamp=None,
            level=level,
            message=data.get('message', ''),
            source=data.get('node'),
            metadata={
                'id': data.get('id'),
                'category': data.get('category'),
                'event': data.get('event'),
            }
        )


class HealthAppParser(BaseParser):
    """
    Parser for HealthApp logs (Android health application).
    
    Format: YYYYMMDD-HH:MM:SS:mmm|Component|ID|Message
    Example: 20171223-22:15:29:606|Step_LSC|30002312|onStandStepChanged 3579
    """
    
    name = "healthapp"
    
    PATTERN = re.compile(
        r'^(?P<timestamp>\d{8}-\d{1,2}:\d{1,2}:\d{1,2}:\d{1,3})\|'
        r'(?P<component>[^|]+)\|'
        r'(?P<id>\d+)\|'
        r'(?P<message>.*)$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches HealthApp format."""
        return bool(re.match(r'^\d{8}-\d{1,2}:\d{1,2}:\d{1,2}:\d{1,3}\|', line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse a HealthApp log line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        
        # Parse timestamp: 20171223-22:15:29:606
        timestamp = None
        try:
            ts_str = data['timestamp']
            timestamp = datetime.strptime(ts_str, "%Y%m%d-%H:%M:%S:%f")
        except (ValueError, KeyError):
            pass
        
        return LogEntry(
            timestamp=timestamp,
            level='INFO',
            message=data.get('message', ''),
            source=data.get('component'),
            metadata={
                'component': data.get('component'),
                'id': data.get('id'),
            }
        )


class OpenStackParser(BaseParser):
    """
    Parser for OpenStack logs (Nova, Neutron, Cinder, etc.).
    
    Format: filename timestamp PID LEVEL component [req-UUID ...] IP "REQUEST" status: N len: N time: N
    Example: nova-api.log 2017-05-16 00:00:00.008 25746 INFO nova.osapi_compute.wsgi.server [req-xxx] 10.11.10.1 "GET /v2/..." status: 200
    """
    
    name = "openstack"
    
    PATTERN = re.compile(
        r'^(?P<filename>\S+)\s+'
        r'(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+'
        r'(?P<pid>\d+)\s+'
        r'(?P<level>\w+)\s+'
        r'(?P<component>\S+)\s+'
        r'\[(?P<request_id>[^\]]+)\]\s+'
        r'(?P<message>.*)$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches OpenStack format."""
        # Look for the characteristic [req-uuid] pattern
        return bool(re.match(r'^\S+\s+\d{4}-\d{2}-\d{2}.*\[req-', line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse an OpenStack log line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        
        # Parse timestamp
        timestamp = None
        try:
            ts_str = data['timestamp']
            timestamp = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
        except (ValueError, KeyError):
            pass
        
        level = data.get('level', 'INFO').upper()
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=data.get('message', ''),
            source=data.get('component'),
            metadata={
                'filename': data.get('filename'),
                'pid': data.get('pid'),
                'request_id': data.get('request_id'),
            }
        )


class SquidParser(BaseParser):
    """
    Parser for Squid proxy access logs.
    
    Format: timestamp duration client_ip result/status_code bytes method URL user hierarchy/server content_type
    Example: 1157689312.049   5006 10.105.21.199 TCP_MISS/200 19763 CONNECT login.yahoo.com:443 user DIRECT/ip -
    """
    
    name = "squid"
    
    PATTERN = re.compile(
        r'^(?P<timestamp>\d+(?:\.\d+)?)\s+'
        r'(?P<duration>-?\d+)\s+'
        r'(?P<client_ip>\S+)\s+'
        r'(?P<result_code>\S+)\s+'
        r'(?P<bytes>-?\d+)\s+'
        r'(?P<method>\w+)\s+'
        r'(?P<url>\S+)\s+'
        r'(?P<user>\S+)\s+'
        r'(?P<hierarchy>\S+)\s*'
        r'(?P<content_type>\S*)$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches Squid format."""
        # Squid lines start with epoch timestamp (10 digits, optional decimal) followed by duration
        return bool(re.match(r'^\d{10}(?:\.\d+)?\s+-?\d+\s+\S+\s+\w+[_/]', line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse a Squid log line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        
        # Parse epoch timestamp
        timestamp = None
        try:
            epoch = float(data['timestamp'])
            timestamp = datetime.fromtimestamp(epoch)
        except (ValueError, KeyError, OSError):
            pass
        
        # Infer level from result code
        result = data.get('result_code', '')
        level = 'INFO'
        if '/5' in result or 'ERR' in result:
            level = 'ERROR'
        elif '/4' in result or 'DENIED' in result:
            level = 'WARNING'
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=f"{data.get('method', '')} {data.get('url', '')}",
            source=data.get('client_ip'),
            metadata={
                'duration_ms': data.get('duration'),
                'bytes': data.get('bytes'),
                'result_code': data.get('result_code'),
                'user': data.get('user'),
                'hierarchy': data.get('hierarchy'),
            }
        )


class NginxParser(BaseParser):
    """
    Parser for nginx access logs (handles both standard and extended formats).
    
    This parser specifically handles nginx logs that may not match the Apache combined format,
    including logs with additional fields like request time and upstream response time.
    """
    
    name = "nginx"
    
    # Standard nginx combined format with optional extensions
    PATTERN = re.compile(
        r'^(?P<client_ip>\S+)\s+'
        r'-\s+'
        r'(?P<user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<request>[^"]*)"\s+'
        r'(?P<status>\d+)\s+'
        r'(?P<bytes>\d+)\s+'
        r'"(?P<referer>[^"]*)"\s+'
        r'"(?P<user_agent>[^"]*)"'
        r'(?:\s+(?P<extra>.*))?$'
    )
    
    def can_parse(self, line: str) -> bool:
        """Check if line matches nginx format."""
        return bool(self.PATTERN.match(line))
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """Parse a nginx log line."""
        match = self.PATTERN.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        
        # Parse timestamp
        timestamp = None
        try:
            ts_str = data['timestamp']
            timestamp = datetime.strptime(ts_str, "%d/%b/%Y:%H:%M:%S %z")
        except (ValueError, KeyError):
            try:
                timestamp = datetime.strptime(ts_str.split()[0], "%d/%b/%Y:%H:%M:%S")
            except (ValueError, KeyError):
                pass
        
        # Infer level from status code
        status = int(data.get('status', 200))
        if status >= 500:
            level = 'ERROR'
        elif status >= 400:
            level = 'WARNING'
        else:
            level = 'INFO'
        
        return LogEntry(
            timestamp=timestamp,
            level=level,
            message=data.get('request', ''),
            source=data.get('client_ip'),
            metadata={
                'status': status,
                'bytes': data.get('bytes'),
                'user_agent': data.get('user_agent'),
                'referer': data.get('referer'),
            }
        )


class UniversalFallbackParser(BaseParser):
    """
    Universal fallback parser using heuristic pattern detection.
    
    This parser attempts to extract common log elements (timestamps, levels, messages)
    from any text-based log format. It should be used as the LAST parser in the chain
    when no specific format is detected.
    
    The parser indicates that it used fallback/heuristic parsing via metadata.
    """
    
    name = "universal"
    
    # Common timestamp patterns (ordered by specificity)
    TIMESTAMP_PATTERNS = [
        # ISO 8601 format
        (r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)', 'iso'),
        # Common log format
        (r'(\d{2}/\w{3}/\d{4}:\d{2}:\d{2}:\d{2})', 'clf'),
        # US date format
        (r'(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})', 'us_date'),
        # Syslog BSD format
        (r'(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})', 'syslog'),
        # Unix timestamp (epoch)
        (r'\b(\d{10})\b', 'epoch'),
        # Short date format
        (r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', 'short'),
    ]
    
    # Common log level patterns
    LEVEL_PATTERN = re.compile(
        r'\b(FATAL|CRITICAL|CRIT|ERROR|ERR|WARNING|WARN|INFO|DEBUG|DBG|TRACE|NOTICE)\b',
        re.IGNORECASE
    )
    
    # Level normalization map
    LEVEL_MAP = {
        'fatal': 'CRITICAL',
        'critical': 'CRITICAL',
        'crit': 'CRITICAL',
        'error': 'ERROR',
        'err': 'ERROR',
        'warning': 'WARNING',
        'warn': 'WARNING',
        'info': 'INFO',
        'debug': 'DEBUG',
        'dbg': 'DEBUG',
        'trace': 'DEBUG',
        'notice': 'INFO',
    }
    
    def can_parse(self, line: str) -> bool:
        """
        Universal parser can attempt to parse ANY line.
        
        Always returns True - this is the fallback parser.
        """
        return True
    
    def parse(self, line: str) -> Optional[LogEntry]:
        """
        Parse a log line using heuristic pattern detection.
        
        Attempts to extract timestamps, levels, and messages from any format.
        """
        if not line.strip():
            return None
        
        timestamp_str = None
        timestamp_format = None
        level = 'INFO'  # Default level
        message = line
        
        # Try to extract timestamp
        for pattern, fmt in self.TIMESTAMP_PATTERNS:
            match = re.search(pattern, line)
            if match:
                timestamp_str = match.group(1)
                timestamp_format = fmt
                # Remove timestamp from message extraction
                message = line[match.end():].strip()
                if message.startswith('-') or message.startswith(':'):
                    message = message[1:].strip()
                break
        
        # Try to extract log level
        level_match = self.LEVEL_PATTERN.search(line)
        if level_match:
            found_level = level_match.group(1).lower()
            level = self.LEVEL_MAP.get(found_level, 'INFO')
            # Try to clean level from message if it appears at the start
            if message.upper().startswith(level_match.group(1).upper()):
                message = message[len(level_match.group(1)):].strip()
                if message.startswith('-') or message.startswith(':') or message.startswith('|'):
                    message = message[1:].strip()
        
        # Infer level from message keywords if not found
        if not level_match:
            msg_lower = line.lower()
            if 'error' in msg_lower or 'fail' in msg_lower or 'exception' in msg_lower:
                level = 'ERROR'
            elif 'warn' in msg_lower:
                level = 'WARNING'
            elif 'debug' in msg_lower:
                level = 'DEBUG'
        
        return LogEntry(
            timestamp=None,  # Would need parsing logic for each format
            level=level,
            message=message if message else line,
            source=None,
            metadata={
                'parser_type': 'fallback',  # Indicates fallback was used
                'timestamp_raw': timestamp_str,
                'timestamp_format': timestamp_format,
            }
        )


# =============================================================================
# Custom Parser Registration
# =============================================================================

class CustomParserRegistry:
    """
    Registry for custom parser extensions.
    
    This allows companies to easily add their own log format parsers without
    modifying the core codebase.
    
    Usage:
        from log_analyzer.parsers import CustomParserRegistry, BaseParser
        
        class MyCompanyLogParser(BaseParser):
            name = "mycompany"
            
            def can_parse(self, line: str) -> bool:
                return line.startswith('[MYCO]')
            
            def parse(self, line: str) -> Optional[LogEntry]:
                # Your parsing logic here
                ...
        
        # Register the parser
        CustomParserRegistry.register(MyCompanyLogParser)
        
        # Get all parsers (built-in + custom)
        all_parsers = CustomParserRegistry.get_all_parsers()
    """
    
    _custom_parsers: list = []
    
    @classmethod
    def register(cls, parser_class: type) -> None:
        """
        Register a custom parser class.
        
        Args:
            parser_class: A class that extends BaseParser
        """
        if not issubclass(parser_class, BaseParser):
            raise TypeError(f"{parser_class} must be a subclass of BaseParser")
        
        # Instantiate and add to registry
        cls._custom_parsers.append(parser_class())
    
    @classmethod
    def register_instance(cls, parser: BaseParser) -> None:
        """
        Register an already-instantiated parser.
        
        Args:
            parser: An instance of a BaseParser subclass
        """
        if not isinstance(parser, BaseParser):
            raise TypeError(f"{parser} must be an instance of BaseParser")
        
        cls._custom_parsers.append(parser)
    
    @classmethod
    def get_custom_parsers(cls) -> list:
        """Get all registered custom parsers."""
        return cls._custom_parsers.copy()
    
    @classmethod
    def clear(cls) -> None:
        """Clear all custom parsers (useful for testing)."""
        cls._custom_parsers = []
    
    @classmethod
    def get_all_parsers(cls, include_fallback: bool = True) -> list:
        """
        Get all parsers: built-in + custom + optional fallback.
        
        Args:
            include_fallback: Whether to include UniversalFallbackParser at the end
            
        Returns:
            List of all parser instances
        """
        from .analyzer import AVAILABLE_PARSERS
        
        parsers = AVAILABLE_PARSERS.copy()
        parsers.extend(cls._custom_parsers)
        
        if include_fallback:
            parsers.append(UniversalFallbackParser())
        
        return parsers
