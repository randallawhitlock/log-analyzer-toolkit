"""
Log format auto-detection and analysis engine.

Provides automatic format detection and comprehensive log analysis
including error detection, pattern recognition, and statistics.
"""

import logging
import os
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Iterator, Optional, Any

from .parsers import (
    BaseParser,
    LogEntry,
    AWSCloudWatchParser,
    GCPCloudLoggingParser,
    AzureMonitorParser,
    DockerJSONParser,
    KubernetesParser,
    ContainerdParser,
    ApacheAccessParser,
    ApacheErrorParser,
    NginxAccessParser,
    NginxParser,
    JSONLogParser,
    SyslogParser,
    AndroidParser,
    JavaLogParser,
    HDFSParser,
    SupercomputerParser,
    WindowsEventParser,
    ProxifierParser,
    HPCParser,
    HealthAppParser,
    OpenStackParser,
    SquidParser,
    UniversalFallbackParser,
    CustomParserRegistry,
)
from .reader import LogReader
from .constants import DEFAULT_SAMPLE_SIZE, DEFAULT_MAX_ERRORS, MAX_COUNTER_SIZE, COUNTER_PRUNE_TO

# Analytics imports (optional, loaded on demand)
try:
    from .stats_models import AnalyticsData
    from .analytics import compute_analytics
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    AnalyticsData = None


logger = logging.getLogger(__name__)


# Registry of all available parsers (specific formats only, no fallback)
AVAILABLE_PARSERS = [
    # Cloud provider parsers (check first - highly structured)
    AWSCloudWatchParser(),
    GCPCloudLoggingParser(),
    AzureMonitorParser(),

    # Container runtime parsers
    DockerJSONParser(),
    KubernetesParser(),
    ContainerdParser(),

    # Web server and application parsers
    ApacheAccessParser(),
    ApacheErrorParser(),
    NginxAccessParser(),
    NginxParser(),
    JSONLogParser(),
    SyslogParser(),
    AndroidParser(),
    JavaLogParser(),
    HDFSParser(),
    SupercomputerParser(),
    WindowsEventParser(),
    ProxifierParser(),
    HPCParser(),
    HealthAppParser(),
    OpenStackParser(),
    SquidParser(),
]

# Full parser list including universal fallback (for use when no format detected)
ALL_PARSERS_WITH_FALLBACK = AVAILABLE_PARSERS + [UniversalFallbackParser()]


__all__ = [
    "AVAILABLE_PARSERS",
    "ALL_PARSERS_WITH_FALLBACK",
    "AnalysisResult",
    "LogAnalyzer",
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

    # Advanced analytics (optional, Phase 3B)
    analytics: Optional[Any] = None  # AnalyticsData when computed

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
    
    def __init__(self, parsers: list[BaseParser] = None, max_workers: Optional[int] = None):
        """
        Initialize the analyzer.

        Args:
            parsers: List of parsers to use. Defaults to all available parsers.
            max_workers: Maximum number of worker threads. If None, uses config value
                        or CPU count.
        """
        from .config import get_config

        self.parsers = parsers or AVAILABLE_PARSERS

        # Determine max_workers: explicit param > config > CPU count
        if max_workers is not None:
            self.max_workers = max_workers
        else:
            config = get_config()
            self.max_workers = config.max_workers or os.cpu_count() or 4

        logger.debug(f"LogAnalyzer initialized with max_workers={self.max_workers}")

    @staticmethod
    def _prune_counter(counter: Counter, max_size: int = MAX_COUNTER_SIZE, prune_to: int = COUNTER_PRUNE_TO) -> None:
        """
        Prune a Counter to prevent unbounded memory growth.

        Keeps only the most common items when counter exceeds max_size.

        Args:
            counter: Counter to prune (modified in-place)
            max_size: Maximum size before pruning
            prune_to: Number of items to keep after pruning
        """
        if len(counter) > max_size:
            # Keep only the most common items
            top_items = counter.most_common(prune_to)
            counter.clear()
            counter.update(dict(top_items))
            logger.debug(f"Pruned Counter from {max_size}+ items to {len(counter)} items")

    def _analyze_multithreaded(self, filepath: str, parser: BaseParser,
                                max_errors: int, progress_callback: Optional[Any],
                                chunk_size: int, start_time: float,
                                enable_analytics: bool = False,
                                analytics_config: Optional[dict] = None) -> AnalysisResult:
        """
        Analyze log file using multithreaded processing.

        Args:
            filepath: Path to log file
            parser: Parser to use
            max_errors: Maximum errors/warnings to collect
            progress_callback: Optional progress callback
            chunk_size: Number of lines per chunk
            start_time: Analysis start time
            enable_analytics: Whether to compute analytics
            analytics_config: Optional analytics configuration

        Returns:
            AnalysisResult with all analysis data
        """
        reader = LogReader(filepath)

        # Read file into chunks
        chunks = []
        current_chunk = []
        total_lines = 0

        logger.debug("Reading file into chunks for parallel processing")
        for line in reader.read_lines():
            total_lines += 1
            current_chunk.append(line)

            if len(current_chunk) >= chunk_size:
                chunks.append(current_chunk)
                current_chunk = []

        # Add remaining lines
        if current_chunk:
            chunks.append(current_chunk)

        logger.info(f"Split {total_lines:,} lines into {len(chunks)} chunks of ~{chunk_size} lines")

        # Process chunks in parallel
        chunk_results = []
        progress_lock = Lock()
        lines_processed = 0

        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all chunks
                future_to_chunk = {
                    executor.submit(self._process_chunk, chunk, parser, max_errors): i
                    for i, chunk in enumerate(chunks)
                }

                # Collect results as they complete
                for future in as_completed(future_to_chunk):
                    try:
                        result = future.result()
                        chunk_results.append(result)

                        # Update progress
                        if progress_callback and hasattr(progress_callback, 'update'):
                            with progress_lock:
                                lines_in_chunk = result['parsed_lines'] + result['failed_lines']
                                progress_callback.update(advance=lines_in_chunk)
                                lines_processed += lines_in_chunk

                    except Exception as e:
                        logger.error(f"Error processing chunk: {e}", exc_info=True)
                        raise

        except KeyboardInterrupt:
            logger.info("Analysis cancelled by user during multithreaded processing")
            raise

        # Merge results from all chunks
        logger.debug("Merging results from all worker threads")
        return self._merge_chunk_results(
            filepath=filepath,
            parser=parser,
            total_lines=total_lines,
            chunk_results=chunk_results,
            max_errors=max_errors,
            start_time=start_time,
            enable_analytics=enable_analytics,
            analytics_config=analytics_config
        )

    def _merge_chunk_results(self, filepath: str, parser: BaseParser,
                             total_lines: int, chunk_results: list[dict],
                             max_errors: int, start_time: float,
                             enable_analytics: bool = False,
                             analytics_config: Optional[dict] = None) -> AnalysisResult:
        """
        Merge results from multiple chunk processing tasks.

        Args:
            filepath: Path to log file
            parser: Parser used
            total_lines: Total lines in file
            chunk_results: List of results from each chunk
            max_errors: Maximum errors/warnings to keep
            start_time: Analysis start time
            enable_analytics: Whether to compute analytics
            analytics_config: Optional analytics configuration

        Returns:
            Merged AnalysisResult
        """
        # Aggregate counters
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

        for result in chunk_results:
            parsed_lines += result['parsed_lines']
            failed_lines += result['failed_lines']

            level_counts.update(result['level_counts'])
            status_codes.update(result['status_codes'])
            source_counts.update(result['source_counts'])
            error_messages.update(result['error_messages'])

            errors.extend(result['errors'])
            warnings.extend(result['warnings'])

            # Track earliest/latest timestamps
            if result['earliest']:
                if earliest is None or result['earliest'] < earliest:
                    earliest = result['earliest']
            if result['latest']:
                if latest is None or result['latest'] > latest:
                    latest = result['latest']

        # Prune counters to prevent unbounded size
        self._prune_counter(source_counts)
        self._prune_counter(error_messages)

        # Limit errors/warnings to max_errors
        errors = errors[:max_errors]
        warnings = warnings[:max_errors]

        elapsed = time.time() - start_time

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

        # Compute advanced analytics if enabled
        if enable_analytics and ANALYTICS_AVAILABLE:
            logger.debug("Computing advanced analytics (multithreaded)")
            result.analytics = compute_analytics(
                errors=errors,
                warnings=warnings,
                level_counts=dict(level_counts),
                source_counts=dict(source_counts),
                config=analytics_config or {}
            )

        logger.info(f"Multithreaded analysis completed in {elapsed:.2f}s: "
                   f"{parsed_lines:,} lines parsed ({result.parse_success_rate:.1f}% success), "
                   f"{failed_lines:,} failed, "
                   f"{result.error_rate:.1f}% error rate, "
                   f"throughput={parsed_lines/elapsed:.0f} lines/sec")

        return result

    def _process_chunk(self, lines: list[str], parser: BaseParser,
                       max_errors: int) -> dict:
        """
        Process a chunk of lines in a worker thread.

        Args:
            lines: List of lines to process
            parser: Parser to use for this chunk
            max_errors: Maximum errors/warnings to collect

        Returns:
            Dictionary containing chunk results
        """
        # Initialize local counters
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

        for line in lines:
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

        return {
            'parsed_lines': parsed_lines,
            'failed_lines': failed_lines,
            'level_counts': level_counts,
            'status_codes': status_codes,
            'source_counts': source_counts,
            'error_messages': error_messages,
            'errors': errors,
            'warnings': warnings,
            'earliest': earliest,
            'latest': latest,
        }

    def detect_format(self, filepath: str, sample_size: int = DEFAULT_SAMPLE_SIZE) -> Optional[BaseParser]:
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
                max_errors: int = DEFAULT_MAX_ERRORS,
                progress_callback: Optional[Any] = None,
                use_fallback: bool = True,
                detect_inline: bool = True,
                use_threading: bool = True,
                chunk_size: int = 10000,
                enable_analytics: bool = False,
                analytics_config: Optional[dict] = None) -> AnalysisResult:
        """
        Perform comprehensive analysis of a log file.

        Args:
            filepath: Path to log file
            parser: Specific parser to use. Auto-detects if None.
            max_errors: Maximum number of errors/warnings to collect
            progress_callback: Optional callback for progress updates (Rich Progress task)
            use_fallback: If True, use universal fallback parser when no format detected.
                         If False, raise ValueError when format cannot be detected.
            detect_inline: If True, detect format during first pass (faster).
                          If False, use separate detection pass.
            use_threading: If True, use multithreading for parallel parsing (default: True).
            chunk_size: Number of lines per chunk when using threading (default: 10000).
            enable_analytics: If True, compute advanced analytics (time-series, etc.).
            analytics_config: Optional analytics configuration dict with keys:
                - time_bucket_size: '5min', '15min', '1h', '1day' (default: '1h')
                - enable_time_series: bool (default: True)
                - enable_statistics: bool (default: False)

        Returns:
            AnalysisResult with all analysis data

        Note:
            When fallback parser is used, the detected_format will be "universal"
            and entries will have metadata['parser_type'] = 'fallback'.
            Inline detection (default) is faster as it avoids reading the file twice.
            Multithreading provides significant performance improvements for large files.
        """
        logger.info(f"Starting analysis of {filepath}")
        logger.debug(f"Parameters: parser={parser.name if parser else 'auto'}, max_errors={max_errors}, "
                    f"use_fallback={use_fallback}, detect_inline={detect_inline}, "
                    f"use_threading={use_threading}, chunk_size={chunk_size}")
        start_time = time.time()

        # If using threading, we must detect format first (can't defer)
        if use_threading and parser is None and detect_inline:
            logger.debug("Multithreading enabled - forcing separate format detection pass")
            detect_inline = False

        # Detect format if not specified
        if parser is None:
            if detect_inline:
                # Defer detection - will detect during first pass
                logger.debug("Deferring format detection to first pass (inline detection)")
                parser = None  # Will be set during processing
            else:
                # Traditional two-pass detection
                parser = self.detect_format(filepath)
                if parser is None:
                    if use_fallback:
                        logger.info(f"No specific format detected for {filepath}, using universal fallback parser")
                        parser = UniversalFallbackParser()
                    else:
                        logger.error(f"Could not detect log format for {filepath}")
                        raise ValueError(f"Could not detect log format for: {filepath}")
                logger.debug(f"Using parser: {parser.name}")

        # Use multithreaded implementation if enabled and parser is known
        if use_threading and parser is not None:
            logger.info(f"Using multithreaded analysis with {self.max_workers} workers, chunk_size={chunk_size}")
            return self._analyze_multithreaded(
                filepath=filepath,
                parser=parser,
                max_errors=max_errors,
                progress_callback=progress_callback,
                chunk_size=chunk_size,
                start_time=start_time,
                enable_analytics=enable_analytics,
                analytics_config=analytics_config
            )

        # Fall back to single-threaded implementation
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

        # Inline detection state
        sample_lines = []
        inline_detected = False

        # Process each line
        for line in reader.read_lines():
            total_lines += 1

            # Update progress
            if progress_callback and hasattr(progress_callback, 'update'):
                progress_callback.update(advance=1)

            if not line.strip():
                continue

            # Inline format detection - collect samples until we have enough
            if parser is None and not inline_detected:
                sample_lines.append(line)

                # Once we have enough samples, detect format
                if len(sample_lines) >= DEFAULT_SAMPLE_SIZE:
                    logger.debug(f"Running inline format detection on {len(sample_lines)} sample lines")
                    parse_counts = Counter()

                    # Test each parser against samples
                    for sample_line in sample_lines:
                        for candidate_parser in self.parsers:
                            if candidate_parser.can_parse(sample_line):
                                result = candidate_parser.parse(sample_line)
                                if result:
                                    parse_counts[candidate_parser.name] += 1

                    # Select best parser
                    if parse_counts:
                        best_format = parse_counts.most_common(1)[0][0]
                        for p in self.parsers:
                            if p.name == best_format:
                                parser = p
                                break
                        logger.info(f"Detected format '{parser.name}' inline (parse_counts={dict(parse_counts)})")
                    else:
                        # No format detected
                        if use_fallback:
                            logger.info(f"No specific format detected inline for {filepath}, using universal fallback parser")
                            parser = UniversalFallbackParser()
                        else:
                            logger.error(f"Could not detect log format for {filepath}")
                            raise ValueError(f"Could not detect log format for: {filepath}")

                    inline_detected = True

                    # Process collected sample lines with detected parser
                    for sample_line in sample_lines:
                        entry = parser.parse(sample_line)

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

                    # Clear samples
                    sample_lines = []

                # Skip to next line while collecting samples
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

            # Periodically prune counters to prevent unbounded memory growth
            if parsed_lines % 1000 == 0:
                self._prune_counter(source_counts)
                self._prune_counter(error_messages)

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

        # Compute advanced analytics if enabled
        if enable_analytics and ANALYTICS_AVAILABLE:
            logger.debug("Computing advanced analytics")
            result.analytics = compute_analytics(
                errors=errors,
                warnings=warnings,
                level_counts=dict(level_counts),
                source_counts=dict(source_counts),
                config=analytics_config or {}
            )
        elif enable_analytics and not ANALYTICS_AVAILABLE:
            logger.warning("Analytics requested but analytics module not available")

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
