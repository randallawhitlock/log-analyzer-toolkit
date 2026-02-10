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
    including time-series analysis, statistical computations, anomaly
    detection, and pattern mining.
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

    # Statistical Analysis
    error_statistics: dict = field(default_factory=dict)
    """Statistical metrics for errors: mean, median, std_dev, percentiles"""

    level_statistics: dict = field(default_factory=dict)
    """Statistics per severity level"""

    # Anomaly Detection
    anomalies: list = field(default_factory=list)
    """List of detected anomalies with details"""

    baseline_deviation: Optional[float] = None
    """Percentage deviation from baseline error rate"""

    # Pattern Analysis
    burst_periods: list = field(default_factory=list)
    """Time periods with sudden activity spikes"""

    recurring_patterns: list = field(default_factory=list)
    """Detected periodic patterns"""

    error_clusters: list = field(default_factory=list)
    """Groups of similar error messages"""

    # Correlation Analysis
    source_error_rates: dict = field(default_factory=dict)
    """Error rate per source (IP/hostname)"""

    level_correlations: dict = field(default_factory=dict)
    """Cross-level correlation coefficients"""

    def to_dict(self) -> dict:
        """
        Convert analytics data to dictionary for serialization.

        Returns:
            Dictionary representation of analytics data
        """
        return {
            'temporal_distribution': self.temporal_distribution,
            'hourly_distribution': self.hourly_distribution,
            'trend_direction': self.trend_direction,
            'peak_period': self.peak_period,
            'error_statistics': self.error_statistics,
            'level_statistics': self.level_statistics,
            'anomalies': self.anomalies,
            'baseline_deviation': self.baseline_deviation,
            'burst_periods': self.burst_periods,
            'recurring_patterns': self.recurring_patterns,
            'error_clusters': self.error_clusters,
            'source_error_rates': self.source_error_rates,
            'level_correlations': self.level_correlations,
        }
