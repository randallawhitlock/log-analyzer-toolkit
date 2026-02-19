"""
Chart generation utilities for log analysis reporting.

Provides functions to generate Chart.js configurations for visualizing
analytics data in HTML reports.
"""

import json


def generate_chartjs_config(analytics) -> str:
    """
    Generate Chart.js configuration JSON for analytics visualization.

    Args:
        analytics: AnalyticsData object containing analytics results

    Returns:
        JSON string containing Chart.js configuration for temporal and hourly charts

    Example:
        >>> config_json = generate_chartjs_config(analytics)
        >>> # Embed in HTML: const chartConfig = {config_json};
    """
    charts = {}

    # Time-series line chart (temporal distribution)
    if analytics.temporal_distribution:
        sorted_buckets = sorted(analytics.temporal_distribution.items())

        # Limit to last 50 buckets for readability
        if len(sorted_buckets) > 50:
            sorted_buckets = sorted_buckets[-50:]

        labels = []
        data = []
        for timestamp_str, count in sorted_buckets:
            # Format label for display
            if "T" in timestamp_str:
                time_part = timestamp_str.split("T")[1][:5]  # HH:MM
                date_part = timestamp_str.split("T")[0][5:]  # MM-DD
                label = f"{date_part} {time_part}"
            else:
                label = timestamp_str[:16]

            labels.append(label)
            data.append(count)

        charts["temporal"] = {
            "type": "line",
            "data": {
                "labels": labels,
                "datasets": [
                    {
                        "label": "Log Entries",
                        "data": data,
                        "borderColor": "rgb(75, 192, 192)",
                        "backgroundColor": "rgba(75, 192, 192, 0.1)",
                        "tension": 0.1,
                        "fill": True,
                    }
                ],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Temporal Distribution (Trend: {analytics.trend_direction})",
                        "font": {"size": 16},
                    },
                    "legend": {"display": False},
                },
                "scales": {
                    "y": {"beginAtZero": True, "title": {"display": True, "text": "Count"}},
                    "x": {"title": {"display": True, "text": "Time Period"}},
                },
            },
        }

    # Hourly bar chart
    if analytics.hourly_distribution:
        hourly_labels = []
        hourly_data = []

        for hour in range(24):
            count = analytics.hourly_distribution.get(hour, 0)
            if count > 0:  # Only include hours with activity
                hourly_labels.append(f"{hour:02d}:00")
                hourly_data.append(count)

        # Determine bar color based on activity level
        max_count = max(hourly_data) if hourly_data else 0
        colors = []
        for count in hourly_data:
            if count >= max_count * 0.8:  # Peak hours (red)
                colors.append("rgba(255, 99, 132, 0.8)")
            elif count >= max_count * 0.5:  # High activity (orange)
                colors.append("rgba(255, 159, 64, 0.8)")
            else:  # Normal activity (blue)
                colors.append("rgba(54, 162, 235, 0.8)")

        charts["hourly"] = {
            "type": "bar",
            "data": {
                "labels": hourly_labels,
                "datasets": [
                    {
                        "label": "Count",
                        "data": hourly_data,
                        "backgroundColor": colors,
                        "borderColor": colors,
                        "borderWidth": 1,
                    }
                ],
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "title": {
                        "display": True,
                        "text": f"Hourly Distribution (Peak: {analytics.peak_period or 'N/A'})",
                        "font": {"size": 16},
                    },
                    "legend": {"display": False},
                },
                "scales": {
                    "y": {"beginAtZero": True, "title": {"display": True, "text": "Count"}},
                    "x": {"title": {"display": True, "text": "Hour of Day"}},
                },
            },
        }

    return json.dumps(charts, indent=2)
