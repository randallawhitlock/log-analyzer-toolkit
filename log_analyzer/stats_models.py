"""
Statistical data models for advanced analytics.

Provides data structures for storing analytics results including
time-series analysis, anomaly detection, and pattern mining.
"""

from dataclasses import dataclass, field
from typing import Optional

__all__ = ["AnalyticsData"]


@dataclass
class AnalyticsData:
    """
    Advanced analytics data computed from log analysis.

    This dataclass stores results from various analytics operations
    including time-series analysis and trend detection.
    """

    # Time-Series Analysis
    temporal_distribution: dict[str, int] = field(default_factory=dict)
    """Distribution of log entries across time buckets (e.g., {timestamp: count})"""

    hourly_distribution: dict[int, int] = field(default_factory=dict)
    """Distribution by hour of day (0-23) -> count"""

    trend_direction: Optional[str] = None
    """Overall trend: 'increasing', 'decreasing', or 'stable'"""

    peak_period: Optional[str] = None
    """Time period with highest activity"""

    def to_dict(self) -> dict:
        """
        Convert analytics data to dictionary for serialization.

        Returns:
            Dictionary representation of analytics data
        """
        return {
            "temporal_distribution": self.temporal_distribution,
            "hourly_distribution": self.hourly_distribution,
            "trend_direction": self.trend_direction,
            "peak_period": self.peak_period,
        }
