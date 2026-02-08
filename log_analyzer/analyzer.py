"""
Log format auto-detection and analysis engine.

Provides automatic format detection and comprehensive log analysis
including error detection, pattern recognition, and statistics.
"""

import logging
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterator, Optional

from .parsers import (
    BaseParser,
    LogEntry,
    ApacheAccessParser,
    ApacheErrorParser,
    NginxAccessParser,
    JSONLogParser,
    SyslogParser,
)
from .reader import LogReader


logger = logging.getLogger(__name__)


# Registry of all available parsers
AVAILABLE_PARSERS = [
    ApacheAccessParser(),
    ApacheErrorParser(),
    NginxAccessParser(),
    JSONLogParser(),
    SyslogParser(),
]


@dataclass
class AnalysisResult:
    """
    Contains the results of log file analysis.
    """
    filepath: str
    detected_format: str
    total_lines: int
    parsed_lines: int
    failed_lines: int
    
    # Severity breakdown
    level_counts: dict = field(default_factory=dict)
    
    # Time range
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None
    
    # Error details
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    
    # Pattern analysis
    top_sources: list = field(default_factory=list)
    top_errors: list = field(default_factory=list)
    
    # HTTP specific (for access logs)
    status_codes: dict = field(default_factory=dict)
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.parsed_lines == 0:
            return 0.0
        error_count = self.level_counts.get('ERROR', 0) + self.level_counts.get('CRITICAL', 0)
        return (error_count / self.parsed_lines) * 100
    
    @property
    def parse_success_rate(self) -> float:
        """Calculate parse success rate as percentage."""
        if self.total_lines == 0:
            return 0.0
        return (self.parsed_lines / self.total_lines) * 100
    
    @property
    def time_span(self) -> Optional[timedelta]:
        """Calculate time span of logs."""
        if self.earliest_timestamp and self.latest_timestamp:
            return self.latest_timestamp - self.earliest_timestamp
        return None


class LogAnalyzer:
    """
    Main analysis engine for log files.
    
    Handles format detection, parsing, and comprehensive analysis.
    """
    
    def __init__(self, parsers: list[BaseParser] = None):
        """
        Initialize the analyzer.
        
        Args:
            parsers: List of parsers to use. Defaults to all available parsers.
        """
        self.parsers = parsers or AVAILABLE_PARSERS
    
    def detect_format(self, filepath: str, sample_size: int = 100) -> Optional[BaseParser]:
        """
        Auto-detect the log format by sampling lines.

        Args:
            filepath: Path to log file
            sample_size: Number of lines to sample for detection

        Returns:
            Best matching parser, or None if no format detected
        """
        logger.debug(f"Detecting format for {filepath} (sample_size={sample_size})")
        start_time = time.time()

        reader = LogReader(filepath)

        # Count successful parses per parser
        parse_counts = Counter()

        for i, line in enumerate(reader.read_lines()):
            if i >= sample_size:
                break

            for parser in self.parsers:
                if parser.can_parse(line):
                    result = parser.parse(line)
                    if result:
                        parse_counts[parser.name] += 1

        elapsed = time.time() - start_time

        if not parse_counts:
            logger.warning(f"No format detected for {filepath} after sampling {sample_size} lines")
            return None

        # Return parser with most successful parses
        best_format = parse_counts.most_common(1)[0][0]
        logger.info(f"Detected format '{best_format}' for {filepath} "
                   f"(parse_counts={dict(parse_counts)}, elapsed={elapsed:.2f}s)")

        for parser in self.parsers:
            if parser.name == best_format:
                return parser

        return None
    
    def analyze(self, filepath: str, parser: BaseParser = None,
                max_errors: int = 100) -> AnalysisResult:
        """
        Perform comprehensive analysis of a log file.

        Args:
            filepath: Path to log file
            parser: Specific parser to use. Auto-detects if None.
            max_errors: Maximum number of errors/warnings to collect

        Returns:
            AnalysisResult with all analysis data
        """
        logger.info(f"Starting analysis of {filepath}")
        logger.debug(f"Parameters: parser={parser.name if parser else 'auto'}, max_errors={max_errors}")
        start_time = time.time()

        # Detect format if not specified
        if parser is None:
            parser = self.detect_format(filepath)
            if parser is None:
                logger.error(f"Could not detect log format for {filepath}")
                raise ValueError(f"Could not detect log format for: {filepath}")

        logger.debug(f"Using parser: {parser.name}")
        reader = LogReader(filepath)
        
        # Initialize counters
        total_lines = 0
        parsed_lines = 0
        failed_lines = 0
        
        level_counts = Counter()
        status_codes = Counter()
        source_counts = Counter()
        error_messages = Counter()
        
        errors = []
        warnings = []
        
        earliest = None
        latest = None
        
        # Process each line
        for line in reader.read_lines():
            total_lines += 1
            
            if not line.strip():
                continue
            
            entry = parser.parse(line)
            
            if entry is None:
                failed_lines += 1
                continue
            
            parsed_lines += 1
            
            # Count levels
            if entry.level:
                level_counts[entry.level] += 1
            
            # Track timestamps
            if entry.timestamp:
                if earliest is None or entry.timestamp < earliest:
                    earliest = entry.timestamp
                if latest is None or entry.timestamp > latest:
                    latest = entry.timestamp
            
            # Count sources
            if entry.source:
                source_counts[entry.source] += 1
            
            # Track HTTP status codes
            status = entry.metadata.get('status')
            if status:
                status_codes[status] += 1
            
            # Collect errors and warnings
            if entry.level in ('ERROR', 'CRITICAL'):
                error_messages[entry.message] += 1
                if len(errors) < max_errors:
                    errors.append(entry)
            elif entry.level == 'WARNING':
                if len(warnings) < max_errors:
                    warnings.append(entry)
        
        result = AnalysisResult(
            filepath=filepath,
            detected_format=parser.name,
            total_lines=total_lines,
            parsed_lines=parsed_lines,
            failed_lines=failed_lines,
            level_counts=dict(level_counts),
            earliest_timestamp=earliest,
            latest_timestamp=latest,
            errors=errors,
            warnings=warnings,
            top_sources=source_counts.most_common(10),
            top_errors=error_messages.most_common(10),
            status_codes=dict(status_codes),
        )

        elapsed = time.time() - start_time
        logger.info(f"Analysis completed in {elapsed:.2f}s: "
                   f"{parsed_lines:,} lines parsed ({result.parse_success_rate:.1f}% success), "
                   f"{failed_lines:,} failed, "
                   f"{result.error_rate:.1f}% error rate, "
                   f"throughput={parsed_lines/elapsed:.0f} lines/sec")
        logger.debug(f"Level counts: {dict(level_counts)}")
        logger.debug(f"Top sources: {len(source_counts)} unique sources")
        logger.debug(f"Top errors: {len(error_messages)} unique error messages")

        return result
    
    def parse_file(self, filepath: str, parser: BaseParser = None) -> Iterator[LogEntry]:
        """
        Parse a log file and yield entries.
        
        Args:
            filepath: Path to log file
            parser: Specific parser to use. Auto-detects if None.
            
        Yields:
            Parsed LogEntry objects
        """
        if parser is None:
            parser = self.detect_format(filepath)
            if parser is None:
                raise ValueError(f"Could not detect log format for: {filepath}")
        
        reader = LogReader(filepath)
        
        for line in reader.read_lines():
            if not line.strip():
                continue
            
            entry = parser.parse(line)
            if entry:
                yield entry
