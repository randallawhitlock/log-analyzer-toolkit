"""
Unit tests for chart generation.
"""

import json
from unittest.mock import MagicMock
import pytest

from log_analyzer.charts import generate_chartjs_config, generate_ascii_bar_chart
from log_analyzer.stats_models import AnalyticsData

class TestCharts:
    """Tests for chart generation functions."""

    def test_generate_chartjs_config(self):
        """Test generating Chart.js JSON config."""
        analytics = AnalyticsData(
            temporal_distribution={"2020-01-01T12:00": 10},
            hourly_distribution={12: 10}
        )
        
        config_json = generate_chartjs_config(analytics)
        config = json.loads(config_json)
        
        assert "temporal" in config
        assert "hourly" in config
        assert config["temporal"]["type"] == "line"
        assert config["hourly"]["type"] == "bar"
        
        # Check data
        assert config["temporal"]["data"]["datasets"][0]["data"] == [10]
        assert config["hourly"]["data"]["datasets"][0]["data"] == [10]

    def test_generate_ascii_bar_chart(self):
        """Test ASCII bar chart generation."""
        data = {'A': 10, 'B': 20}
        chart = generate_ascii_bar_chart(data, max_width=10)
        
        assert len(chart) == 2
        # ('A', 10, '█████') -> 5 chars roughly if max 20 mapped to 10 width.
        # 10 / 20 * 10 = 5.
        
        label, value, bar = chart[0]
        assert label == 'A'
        assert value == 10
        assert len(bar) == 5
        
        label, value, bar = chart[1]
        assert label == 'B'
        assert value == 20
        assert len(bar) == 10

    def test_generate_ascii_bar_chart_empty(self):
        """Test ASCII chart with empty data."""
        assert generate_ascii_bar_chart({}) == []
