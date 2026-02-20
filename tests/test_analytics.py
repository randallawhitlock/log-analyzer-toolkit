"""
Unit tests for analytics module.
"""

from datetime import datetime, timedelta

from log_analyzer.analytics import (
    compute_analytics,
    compute_temporal_distribution,
    detect_trend,
)
from log_analyzer.parsers import LogEntry
from log_analyzer.stats_models import AnalyticsData


class TestComputeTemporalDistribution:
    """Tests for temporal distribution bucketing."""

    def test_basic_bucketing(self):
        """Entries at different times land in separate buckets."""
        base = datetime(2020, 1, 1, 12, 0, 0)
        entries = [
            LogEntry(timestamp=base, level="INFO"),
            LogEntry(timestamp=base + timedelta(minutes=1), level="INFO"),
            LogEntry(timestamp=base + timedelta(hours=2), level="INFO"),
        ]
        dist = compute_temporal_distribution(entries)
        assert isinstance(dist, dict)
        assert len(dist) >= 2  # At least 2 buckets (hour 12 and hour 14)

    def test_empty_entries(self):
        """Empty list produces empty distribution."""
        dist = compute_temporal_distribution([])
        assert isinstance(dist, dict)
        assert len(dist) == 0

    def test_entries_without_timestamps(self):
        """Entries with None timestamps are skipped."""
        entries = [
            LogEntry(timestamp=None, level="ERROR", message="no ts"),
        ]
        dist = compute_temporal_distribution(entries)
        assert len(dist) == 0


class TestDetectTrend:
    """Tests for trend detection from bucketed data."""

    def test_increasing_trend(self):
        buckets = {
            "2020-01-01T12:00": 10,
            "2020-01-01T13:00": 20,
            "2020-01-01T14:00": 30,
        }
        assert detect_trend(buckets) == "increasing"

    def test_decreasing_trend(self):
        buckets = {
            "2020-01-01T12:00": 30,
            "2020-01-01T13:00": 20,
            "2020-01-01T14:00": 10,
        }
        assert detect_trend(buckets) == "decreasing"

    def test_stable_trend(self):
        buckets = {
            "2020-01-01T12:00": 10,
            "2020-01-01T13:00": 10,
            "2020-01-01T14:00": 10,
        }
        assert detect_trend(buckets) == "stable"

    def test_empty_buckets(self):
        result = detect_trend({})
        assert result in ("stable", "unknown", None, "")

    def test_single_bucket(self):
        result = detect_trend({"2020-01-01T12:00": 5})
        assert result in ("stable", "unknown", None, "")


class TestComputeAnalytics:
    """Tests for full analytics computation."""

    def test_basic_computation(self):
        entries = [
            LogEntry(timestamp=datetime(2020, 1, 1, 12, 0), level="ERROR", message="Error A"),
            LogEntry(timestamp=datetime(2020, 1, 1, 13, 0), level="INFO", message="Info B"),
        ]
        warnings = []
        level_counts = {"ERROR": 1, "INFO": 1}
        source_counts = [("src1", 1)]

        analytics = compute_analytics(entries, warnings, level_counts, source_counts)

        assert isinstance(analytics, AnalyticsData)
        assert len(analytics.temporal_distribution) > 0
        assert analytics.hourly_distribution[12] == 1
        assert analytics.hourly_distribution[13] == 1

    def test_empty_entries(self):
        analytics = compute_analytics([], [], {}, [])
        assert isinstance(analytics, AnalyticsData)
        assert len(analytics.temporal_distribution) == 0

    def test_entries_without_timestamps(self):
        entries = [
            LogEntry(timestamp=None, level="ERROR", message="no ts"),
        ]
        analytics = compute_analytics(entries, [], {"ERROR": 1}, [])
        assert isinstance(analytics, AnalyticsData)
        # No temporal data since there are no timestamps
        assert len(analytics.hourly_distribution) == 0
