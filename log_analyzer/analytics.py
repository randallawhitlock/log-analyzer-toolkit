"""
Advanced analytics engine for log analysis.

Provides time-series analysis, statistical computations, anomaly detection,
and pattern mining capabilities for log data.
"""

import logging
import statistics
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

from .constants import (
    DEFAULT_TIME_BUCKET_SIZE,
)
from .parsers import LogEntry
from .stats_models import AnalyticsData

logger = logging.getLogger(__name__)


__all__ = [
    "compute_analytics",
    "compute_temporal_distribution",
    "compute_hourly_distribution",
    "detect_trend",
    "identify_peak_period",
]


# ============================================================================
# Time-Series Analysis Functions
# ============================================================================


def compute_temporal_distribution(entries: list[LogEntry], bucket_size: str = "1h") -> dict[str, int]:
    """
    Compute distribution of log entries across time buckets.

    Args:
        entries: List of log entries with timestamps
        bucket_size: Bucket size - '5min', '15min', '1h', '1day'

    Returns:
        Dictionary mapping time bucket (ISO format string) to count

    Example:
        >>> entries = [...]  # LogEntry objects with timestamps
        >>> dist = compute_temporal_distribution(entries, '1h')
        >>> dist
        {'2024-02-09T14:00:00': 45, '2024-02-09T15:00:00': 52, ...}
    """
    bucket_counts = Counter()

    # Parse bucket size
    if bucket_size == "5min":
        delta = timedelta(minutes=5)
    elif bucket_size == "15min":
        delta = timedelta(minutes=15)
    elif bucket_size == "1h":
        delta = timedelta(hours=1)
    elif bucket_size == "1day":
        delta = timedelta(days=1)
    else:
        logger.warning(f"Unknown bucket size '{bucket_size}', defaulting to 1h")
        delta = timedelta(hours=1)

    for entry in entries:
        if entry.timestamp is None:
            continue

        # Round timestamp down to bucket boundary
        bucket = _round_to_bucket(entry.timestamp, delta)
        bucket_counts[bucket.isoformat()] += 1

    logger.debug(f"Computed temporal distribution: {len(bucket_counts)} buckets")
    return dict(bucket_counts)


def _round_to_bucket(timestamp: datetime, delta: timedelta) -> datetime:
    """
    Round timestamp down to the nearest bucket boundary.

    Args:
        timestamp: Timestamp to round
        delta: Bucket size as timedelta

    Returns:
        Rounded timestamp
    """
    # For day buckets, round to start of day
    if delta.days >= 1:
        return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

    # For hour buckets, round to start of hour
    if delta.seconds >= 3600:
        return timestamp.replace(minute=0, second=0, microsecond=0)

    # For minute buckets, round to bucket boundary
    minutes = delta.seconds // 60
    rounded_minute = (timestamp.minute // minutes) * minutes
    return timestamp.replace(minute=rounded_minute, second=0, microsecond=0)


def compute_hourly_distribution(entries: list[LogEntry]) -> dict[int, int]:
    """
    Compute distribution of log entries by hour of day (0-23).

    Args:
        entries: List of log entries with timestamps

    Returns:
        Dictionary mapping hour (0-23) to count

    Example:
        >>> entries = [...]
        >>> hourly = compute_hourly_distribution(entries)
        >>> hourly
        {0: 12, 1: 8, 2: 5, ..., 14: 145, ...}
    """
    hourly_counts = Counter()

    for entry in entries:
        if entry.timestamp is None:
            continue

        hour = entry.timestamp.hour
        hourly_counts[hour] += 1

    logger.debug(f"Computed hourly distribution: {len(hourly_counts)} hours")
    return dict(hourly_counts)


def detect_trend(temporal_dist: dict[str, int]) -> str:
    """
    Detect overall trend in temporal distribution.

    Uses simple linear regression to determine if activity is
    increasing, decreasing, or stable over time.

    Args:
        temporal_dist: Temporal distribution from compute_temporal_distribution()

    Returns:
        'increasing', 'decreasing', or 'stable'

    Example:
        >>> dist = {'2024-02-09T14:00:00': 10, '2024-02-09T15:00:00': 15, ...}
        >>> detect_trend(dist)
        'increasing'
    """
    if not temporal_dist or len(temporal_dist) < 2:
        return "stable"

    # Sort by time
    sorted_buckets = sorted(temporal_dist.items())

    # Extract x (time index) and y (counts)
    x_values = list(range(len(sorted_buckets)))
    y_values = [count for _, count in sorted_buckets]

    # Simple linear regression: y = mx + b
    slope = _calculate_slope(x_values, y_values)

    # Determine trend based on slope
    if slope > 0.1:  # Arbitrary threshold for "increasing"
        return "increasing"
    elif slope < -0.1:
        return "decreasing"
    else:
        return "stable"


def _calculate_slope(x_values: list[float], y_values: list[float]) -> float:
    """
    Calculate slope using least squares linear regression.

    Args:
        x_values: Independent variable values
        y_values: Dependent variable values

    Returns:
        Slope of best-fit line
    """
    if not x_values or not y_values or len(x_values) != len(y_values):
        return 0.0

    x_mean = statistics.mean(x_values)
    y_mean = statistics.mean(y_values)

    # Calculate slope: sum((x - x_mean) * (y - y_mean)) / sum((x - x_mean)^2)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_values, y_values))
    denominator = sum((x - x_mean) ** 2 for x in x_values)

    if denominator == 0:
        return 0.0

    return numerator / denominator


def identify_peak_period(temporal_dist: dict[str, int]) -> Optional[str]:
    """
    Identify time period with highest activity.

    Args:
        temporal_dist: Temporal distribution from compute_temporal_distribution()

    Returns:
        ISO format timestamp of peak period, or None if empty

    Example:
        >>> dist = {'2024-02-09T14:00:00': 145, '2024-02-09T15:00:00': 52}
        >>> identify_peak_period(dist)
        '2024-02-09T14:00:00'
    """
    if not temporal_dist:
        return None

    # Find bucket with maximum count
    peak_bucket = max(temporal_dist.items(), key=lambda item: item[1])
    logger.debug(f"Peak period: {peak_bucket[0]} with {peak_bucket[1]} entries")

    return peak_bucket[0]


# ============================================================================
# Main Analytics Computation
# ============================================================================


def compute_analytics(
    errors: list[LogEntry],
    warnings: list[LogEntry],
    level_counts: dict,
    source_counts: dict,
    config: Optional[dict] = None,
) -> AnalyticsData:
    """
    Compute advanced analytics from log analysis data.

    This is the main entry point for analytics computation. It takes
    aggregated data from log analysis and computes various analytics.

    Args:
        errors: List of error log entries
        warnings: List of warning log entries
        level_counts: Dictionary of level -> count
        source_counts: Dictionary of source -> count
        config: Optional configuration dictionary with keys:
            - time_bucket_size: '5min', '15min', '1h', '1day' (default: '1h')
            - enable_time_series: bool (default: True)
            - enable_statistics: bool (default: True)
            - enable_anomaly_detection: bool (default: False)
            - enable_pattern_mining: bool (default: False)

    Returns:
        AnalyticsData object with computed analytics

    Example:
        >>> from log_analyzer.analytics import compute_analytics
        >>> analytics = compute_analytics(
        ...     errors=error_entries,
        ...     warnings=warning_entries,
        ...     level_counts={'ERROR': 10, 'INFO': 100},
        ...     source_counts={'192.168.1.1': 50},
        ...     config={'time_bucket_size': '1h'}
        ... )
        >>> print(analytics.trend_direction)
        'increasing'
    """
    config = config or {}
    logger.debug(f"Computing analytics with config: {config}")

    # Combine errors and warnings for time-series analysis
    all_entries = errors + warnings

    # Initialize analytics data
    analytics = AnalyticsData()

    # Time-Series Analysis (enabled by default)
    if config.get("enable_time_series", True):
        bucket_size = config.get("time_bucket_size", DEFAULT_TIME_BUCKET_SIZE)

        logger.debug(f"Computing time-series analytics (bucket_size={bucket_size})")
        analytics.temporal_distribution = compute_temporal_distribution(all_entries, bucket_size)
        analytics.hourly_distribution = compute_hourly_distribution(all_entries)
        analytics.trend_direction = detect_trend(analytics.temporal_distribution)
        analytics.peak_period = identify_peak_period(analytics.temporal_distribution)

    logger.info(
        f"Analytics computed: {len(analytics.temporal_distribution)} time buckets, "
        f"trend={analytics.trend_direction}, peak={analytics.peak_period}"
    )

    return analytics
