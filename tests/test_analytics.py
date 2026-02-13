"""
Unit tests for advanced analytics module.
"""

from datetime import datetime, timedelta

from log_analyzer.analytics import (
    _calculate_slope,
    _round_to_bucket,
    compute_analytics,
    compute_hourly_distribution,
    compute_temporal_distribution,
    detect_trend,
    identify_peak_period,
)
from log_analyzer.parsers import LogEntry
from log_analyzer.stats_models import AnalyticsData


class TestTimeSeries:
    """Tests for time-series analysis functions."""

    def test_temporal_bucketing_1hour(self):
        """Test temporal distribution with 1-hour buckets."""
        # Create log entries with timestamps at different hours
        entries = [
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 15, 0), level="INFO", message="test1"),
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 30, 0), level="INFO", message="test2"),
            LogEntry(timestamp=datetime(2024, 2, 9, 15, 10, 0), level="INFO", message="test3"),
            LogEntry(timestamp=datetime(2024, 2, 9, 15, 45, 0), level="INFO", message="test4"),
            LogEntry(timestamp=datetime(2024, 2, 9, 16, 5, 0), level="ERROR", message="test5"),
        ]

        dist = compute_temporal_distribution(entries, '1h')

        assert len(dist) == 3  # 3 distinct hours
        assert dist['2024-02-09T14:00:00'] == 2  # 14:00 hour
        assert dist['2024-02-09T15:00:00'] == 2  # 15:00 hour
        assert dist['2024-02-09T16:00:00'] == 1  # 16:00 hour

    def test_temporal_bucketing_1day(self):
        """Test temporal distribution with 1-day buckets."""
        entries = [
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 0, 0), level="INFO", message="test1"),
            LogEntry(timestamp=datetime(2024, 2, 9, 23, 0, 0), level="INFO", message="test2"),
            LogEntry(timestamp=datetime(2024, 2, 10, 1, 0, 0), level="INFO", message="test3"),
            LogEntry(timestamp=datetime(2024, 2, 10, 12, 0, 0), level="ERROR", message="test4"),
        ]

        dist = compute_temporal_distribution(entries, '1day')

        assert len(dist) == 2  # 2 distinct days
        assert dist['2024-02-09T00:00:00'] == 2  # Feb 9
        assert dist['2024-02-10T00:00:00'] == 2  # Feb 10

    def test_temporal_bucketing_5min(self):
        """Test temporal distribution with 5-minute buckets."""
        entries = [
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 2, 0), level="INFO", message="test1"),
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 4, 0), level="INFO", message="test2"),
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 7, 0), level="INFO", message="test3"),
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 8, 0), level="ERROR", message="test4"),
        ]

        dist = compute_temporal_distribution(entries, '5min')

        assert len(dist) == 2  # 2 distinct 5-min buckets
        assert dist['2024-02-09T14:00:00'] == 2  # 14:00-14:05
        assert dist['2024-02-09T14:05:00'] == 2  # 14:05-14:10

    def test_temporal_bucketing_15min(self):
        """Test temporal distribution with 15-minute buckets."""
        entries = [
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 5, 0), level="INFO", message="test1"),
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 12, 0), level="INFO", message="test2"),
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 20, 0), level="INFO", message="test3"),
        ]

        dist = compute_temporal_distribution(entries, '15min')

        assert len(dist) == 2  # 2 distinct 15-min buckets
        assert dist['2024-02-09T14:00:00'] == 2  # 14:00-14:15
        assert dist['2024-02-09T14:15:00'] == 1  # 14:15-14:30

    def test_temporal_bucketing_no_timestamps(self):
        """Test temporal distribution with entries that have no timestamps."""
        entries = [
            LogEntry(timestamp=None, level="INFO", message="test1"),
            LogEntry(timestamp=None, level="ERROR", message="test2"),
        ]

        dist = compute_temporal_distribution(entries, '1h')

        assert len(dist) == 0  # No entries with timestamps

    def test_hourly_distribution(self):
        """Test hour-of-day distribution."""
        entries = [
            LogEntry(timestamp=datetime(2024, 2, 9, 0, 30, 0), level="INFO", message="test1"),
            LogEntry(timestamp=datetime(2024, 2, 9, 0, 45, 0), level="INFO", message="test2"),
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 10, 0), level="INFO", message="test3"),
            LogEntry(timestamp=datetime(2024, 2, 10, 14, 20, 0), level="ERROR", message="test4"),
            LogEntry(timestamp=datetime(2024, 2, 9, 23, 55, 0), level="INFO", message="test5"),
        ]

        hourly = compute_hourly_distribution(entries)

        assert len(hourly) == 3  # 3 distinct hours (0, 14, 23)
        assert hourly[0] == 2  # 2 entries at hour 0
        assert hourly[14] == 2  # 2 entries at hour 14
        assert hourly[23] == 1  # 1 entry at hour 23

    def test_trend_detection_increasing(self):
        """Test trend detection for increasing pattern."""
        # Create distribution with increasing counts
        dist = {
            '2024-02-09T14:00:00': 10,
            '2024-02-09T15:00:00': 20,
            '2024-02-09T16:00:00': 30,
            '2024-02-09T17:00:00': 40,
        }

        trend = detect_trend(dist)

        assert trend == 'increasing'

    def test_trend_detection_decreasing(self):
        """Test trend detection for decreasing pattern."""
        dist = {
            '2024-02-09T14:00:00': 40,
            '2024-02-09T15:00:00': 30,
            '2024-02-09T16:00:00': 20,
            '2024-02-09T17:00:00': 10,
        }

        trend = detect_trend(dist)

        assert trend == 'decreasing'

    def test_trend_detection_stable(self):
        """Test trend detection for stable pattern."""
        dist = {
            '2024-02-09T14:00:00': 25,
            '2024-02-09T15:00:00': 25,
            '2024-02-09T16:00:00': 25,
            '2024-02-09T17:00:00': 25,
        }

        trend = detect_trend(dist)

        assert trend == 'stable'

    def test_trend_detection_empty(self):
        """Test trend detection with empty distribution."""
        dist = {}

        trend = detect_trend(dist)

        assert trend == 'stable'

    def test_peak_period_identification(self):
        """Test identification of peak period."""
        dist = {
            '2024-02-09T14:00:00': 45,
            '2024-02-09T15:00:00': 145,  # Peak
            '2024-02-09T16:00:00': 52,
            '2024-02-09T17:00:00': 30,
        }

        peak = identify_peak_period(dist)

        assert peak == '2024-02-09T15:00:00'

    def test_peak_period_empty(self):
        """Test peak period with empty distribution."""
        dist = {}

        peak = identify_peak_period(dist)

        assert peak is None

    def test_round_to_bucket_hour(self):
        """Test rounding to hour bucket."""
        timestamp = datetime(2024, 2, 9, 14, 35, 45)
        delta = timedelta(hours=1)

        rounded = _round_to_bucket(timestamp, delta)

        assert rounded == datetime(2024, 2, 9, 14, 0, 0)

    def test_round_to_bucket_day(self):
        """Test rounding to day bucket."""
        timestamp = datetime(2024, 2, 9, 14, 35, 45)
        delta = timedelta(days=1)

        rounded = _round_to_bucket(timestamp, delta)

        assert rounded == datetime(2024, 2, 9, 0, 0, 0)

    def test_round_to_bucket_5min(self):
        """Test rounding to 5-minute bucket."""
        timestamp = datetime(2024, 2, 9, 14, 7, 30)
        delta = timedelta(minutes=5)

        rounded = _round_to_bucket(timestamp, delta)

        assert rounded == datetime(2024, 2, 9, 14, 5, 0)

    def test_calculate_slope(self):
        """Test slope calculation."""
        x = [0, 1, 2, 3, 4]
        y = [10, 20, 30, 40, 50]  # Perfect linear increase

        slope = _calculate_slope(x, y)

        assert slope == 10.0  # Slope should be 10

    def test_calculate_slope_negative(self):
        """Test slope calculation with negative trend."""
        x = [0, 1, 2, 3]
        y = [40, 30, 20, 10]  # Linear decrease

        slope = _calculate_slope(x, y)

        assert slope == -10.0

    def test_calculate_slope_zero(self):
        """Test slope calculation with flat line."""
        x = [0, 1, 2, 3]
        y = [25, 25, 25, 25]

        slope = _calculate_slope(x, y)

        assert slope == 0.0


class TestAnalyticsIntegration:
    """Tests for main analytics computation."""

    def test_compute_analytics_basic(self):
        """Test basic analytics computation."""
        errors = [
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 0, 0), level="ERROR", message="error1"),
            LogEntry(timestamp=datetime(2024, 2, 9, 15, 0, 0), level="ERROR", message="error2"),
        ]
        warnings = [
            LogEntry(timestamp=datetime(2024, 2, 9, 14, 30, 0), level="WARNING", message="warn1"),
        ]

        analytics = compute_analytics(
            errors=errors,
            warnings=warnings,
            level_counts={'ERROR': 2, 'WARNING': 1, 'INFO': 10},
            source_counts={'192.168.1.1': 5, '192.168.1.2': 8},
            config={'time_bucket_size': '1h'}
        )

        assert isinstance(analytics, AnalyticsData)
        assert len(analytics.temporal_distribution) == 2  # 2 hours
        assert analytics.trend_direction in ['increasing', 'decreasing', 'stable']
        assert analytics.peak_period is not None

    def test_compute_analytics_disabled(self):
        """Test analytics computation when disabled."""
        analytics = compute_analytics(
            errors=[],
            warnings=[],
            level_counts={},
            source_counts={},
            config={'enable_time_series': False}
        )

        assert isinstance(analytics, AnalyticsData)
        assert len(analytics.temporal_distribution) == 0  # No time-series

    def test_analytics_data_to_dict(self):
        """Test AnalyticsData to_dict method."""
        analytics = AnalyticsData(
            temporal_distribution={'2024-02-09T14:00:00': 10},
            trend_direction='increasing',
            peak_period='2024-02-09T14:00:00'
        )

        data_dict = analytics.to_dict()

        assert isinstance(data_dict, dict)
        assert 'temporal_distribution' in data_dict
        assert 'trend_direction' in data_dict
        assert data_dict['trend_direction'] == 'increasing'
