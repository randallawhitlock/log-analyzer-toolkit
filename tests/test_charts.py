"""
Unit tests for chart generation.
"""

import json

from log_analyzer.charts import generate_chartjs_config
from log_analyzer.stats_models import AnalyticsData


class TestCharts:
    """Tests for chart generation functions."""

    def test_generate_chartjs_config(self):
        """Test generating Chart.js JSON config."""
        analytics = AnalyticsData(temporal_distribution={"2020-01-01T12:00": 10}, hourly_distribution={12: 10})

        config_json = generate_chartjs_config(analytics)
        config = json.loads(config_json)

        assert "temporal" in config
        assert "hourly" in config
        assert config["temporal"]["type"] == "line"
        assert config["hourly"]["type"] == "bar"

        # Check data
        assert config["temporal"]["data"]["datasets"][0]["data"] == [10]
        assert config["hourly"]["data"]["datasets"][0]["data"] == [10]
