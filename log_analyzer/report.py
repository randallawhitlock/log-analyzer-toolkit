"""
Report generation for log analysis results.

Exports analysis results to Markdown and HTML formats for
sharing and documentation purposes.
"""

from datetime import datetime
from pathlib import Path

from .analyzer import AnalysisResult


class ReportGenerator:
    """Generate reports from analysis results."""

    def __init__(self, result: AnalysisResult):
        """
        Initialize the report generator.

        Args:
            result: AnalysisResult to generate report from
        """
        self.result = result

    def to_markdown(self) -> str:
        """
        Generate a Markdown report.

        Returns:
            Markdown-formatted report string
        """
        r = self.result
        lines = []

        # Header
        lines.append("# Log Analysis Report")
        lines.append("")
        lines.append(f"**File:** `{Path(r.filepath).name}`  ")
        lines.append(f"**Format:** {r.detected_format}  ")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Overview
        lines.append("## Overview")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Lines | {r.total_lines:,} |")
        lines.append(f"| Parsed Lines | {r.parsed_lines:,} |")
        lines.append(f"| Failed Lines | {r.failed_lines:,} |")
        lines.append(f"| Parse Success Rate | {r.parse_success_rate:.1f}% |")
        lines.append(f"| Error Rate | {r.error_rate:.1f}% |")

        if r.earliest_timestamp:
            lines.append(f"| First Entry | {r.earliest_timestamp.strftime('%Y-%m-%d %H:%M:%S')} |")
        if r.latest_timestamp:
            lines.append(f"| Last Entry | {r.latest_timestamp.strftime('%Y-%m-%d %H:%M:%S')} |")
        if r.time_span:
            lines.append(f"| Time Span | {r.time_span} |")
        lines.append("")

        # Severity breakdown
        if r.level_counts:
            lines.append("## Severity Breakdown")
            lines.append("")
            lines.append("| Level | Count | Percentage |")
            lines.append("|-------|-------|------------|")
            for level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
                count = r.level_counts.get(level, 0)
                if count > 0:
                    pct = (count / r.parsed_lines * 100) if r.parsed_lines > 0 else 0
                    emoji = {'CRITICAL': '🔴', 'ERROR': '🟠', 'WARNING': '🟡',
                            'INFO': '🟢', 'DEBUG': '⚪'}
                    lines.append(f"| {emoji.get(level, '')} {level} | {count:,} | {pct:.1f}% |")
            lines.append("")

        # HTTP Status Codes
        if r.status_codes:
            lines.append("## HTTP Status Codes")
            lines.append("")
            lines.append("| Code | Count | Category |")
            lines.append("|------|-------|----------|")
            categories = {
                2: "✅ Success",
                3: "↪️ Redirect",
                4: "⚠️ Client Error",
                5: "❌ Server Error"
            }
            for code in sorted(r.status_codes.keys()):
                count = r.status_codes[code]
                cat = categories.get(code // 100, "Unknown")
                lines.append(f"| {code} | {count:,} | {cat} |")
            lines.append("")

        # Top Errors
        if r.top_errors:
            lines.append("## Top Error Messages")
            lines.append("")
            lines.append("| Count | Message |")
            lines.append("|-------|---------|")
            for msg, count in r.top_errors[:10]:
                # Escape pipe characters and truncate
                safe_msg = msg.replace("|", "\\|")[:80]
                lines.append(f"| {count} | {safe_msg} |")
            lines.append("")

        # Top Sources
        if r.top_sources:
            lines.append("## Top Sources")
            lines.append("")
            lines.append("| Source | Requests |")
            lines.append("|--------|----------|")
            for source, count in r.top_sources[:10]:
                lines.append(f"| {source} | {count:,} |")
            lines.append("")

        # Analytics (if available)
        if r.analytics:
            lines.append("## 📈 Time-Series Analytics")
            lines.append("")
            lines.append(f"**Trend:** {r.analytics.trend_direction}  ")
            lines.append(f"**Peak Period:** {r.analytics.peak_period or 'N/A'}  ")
            lines.append(f"**Active Hours:** {len(r.analytics.hourly_distribution)}")
            lines.append("")

            # Hourly Distribution
            if r.analytics.hourly_distribution:
                lines.append("### Hourly Distribution")
                lines.append("")
                lines.append("| Hour | Count | Activity |")
                lines.append("|------|-------|----------|")
                max_count = max(r.analytics.hourly_distribution.values())
                for hour in range(24):
                    count = r.analytics.hourly_distribution.get(hour, 0)
                    if count > 0:
                        bar_width = int((count / max_count) * 20) if max_count > 0 else 0
                        bar = "█" * bar_width
                        lines.append(f"| {hour:02d}:00 | {count:,} | {bar} |")
                lines.append("")

            # Temporal Distribution (recent buckets)
            if r.analytics.temporal_distribution:
                sorted_buckets = sorted(r.analytics.temporal_distribution.items())[-10:]
                if sorted_buckets:
                    lines.append("### Recent Activity")
                    lines.append("")
                    lines.append("| Time Period | Count |")
                    lines.append("|-------------|-------|")
                    for timestamp_str, count in sorted_buckets:
                        # Extract readable time from ISO format
                        if 'T' in timestamp_str:
                            time_display = timestamp_str.split('T')[1][:5]
                            date_display = timestamp_str.split('T')[0]
                            display = f"{date_display} {time_display}"
                        else:
                            display = timestamp_str[:16]
                        lines.append(f"| {display} | {count:,} |")
                    lines.append("")

        # Footer
        lines.append("---")
        lines.append("*Generated by Log Analyzer Toolkit*")

        return "\n".join(lines)

    def to_html(self) -> str:
        """
        Generate an HTML report.

        Returns:
            HTML-formatted report string
        """
        r = self.result

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Log Analysis Report - {Path(r.filepath).name}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .report {{
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{ background: #3498db; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .stat-card {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin: 5px;
            min-width: 150px;
            text-align: center;
        }}
        .stat-value {{ font-size: 2em; font-weight: bold; }}
        .stat-label {{ font-size: 0.9em; opacity: 0.9; }}
        .error {{ color: #e74c3c; }}
        .warning {{ color: #f39c12; }}
        .success {{ color: #27ae60; }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .dashboard-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        @media (max-width: 768px) {{
            .dashboard-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        footer {{ text-align: center; margin-top: 30px; color: #7f8c8d; }}
    </style>
</head>
<body>
    <div class="report">
        <h1>📊 Log Analysis Report</h1>
        <p><strong>File:</strong> <code>{Path(r.filepath).name}</code></p>
        <p><strong>Format:</strong> {r.detected_format}</p>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div style="margin: 20px 0;">
            <div class="stat-card">
                <div class="stat-value">{r.total_lines:,}</div>
                <div class="stat-label">Total Lines</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{r.parse_success_rate:.1f}%</div>
                <div class="stat-label">Parse Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{r.error_rate:.1f}%</div>
                <div class="stat-label">Error Rate</div>
            </div>
        </div>
"""

        # Severity breakdown
        if r.level_counts:
            html += """
        <h2>Severity Breakdown</h2>
        <table>
            <tr><th>Level</th><th>Count</th><th>Percentage</th></tr>
"""
            for level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
                count = r.level_counts.get(level, 0)
                if count > 0:
                    pct = (count / r.parsed_lines * 100) if r.parsed_lines > 0 else 0
                    css_class = {'CRITICAL': 'error', 'ERROR': 'error',
                                'WARNING': 'warning'}.get(level, '')
                    html += f'            <tr><td class="{css_class}">{level}</td><td>{count:,}</td><td>{pct:.1f}%</td></tr>\n'
            html += "        </table>\n"

        # Top Errors
        if r.top_errors:
            html += """
        <h2>Top Error Messages</h2>
        <table>
            <tr><th>Count</th><th>Message</th></tr>
"""
            for msg, count in r.top_errors[:10]:
                safe_msg = msg[:100].replace('<', '&lt;').replace('>', '&gt;')
                html += f'            <tr><td>{count}</td><td>{safe_msg}</td></tr>\n'
            html += "        </table>\n"

        # Analytics (if available)
        if r.analytics:
            from .charts import generate_chartjs_config

            html += """
        <h2>📈 Time-Series Analytics</h2>
        <div style="padding: 20px; background: #e8f5e9; border-radius: 8px; margin: 20px 0;">
            <p><strong>Trend:</strong> <span style="color: #3498db; font-size: 1.2em;">""" + str(r.analytics.trend_direction) + """</span></p>
            <p><strong>Peak Period:</strong> <span style="color: #e67e22; font-size: 1.2em;">""" + str(r.analytics.peak_period or 'N/A') + """</span></p>
            <p><strong>Active Hours:</strong> <span style="color: #27ae60; font-size: 1.2em;">""" + str(len(r.analytics.hourly_distribution)) + """</span></p>
        </div>

        <div class="dashboard-grid">
            <div class="chart-container">
                <canvas id="temporal-chart"></canvas>
            </div>
            <div class="chart-container">
                <canvas id="hourly-chart"></canvas>
            </div>
        </div>
"""

            # Generate Chart.js configuration
            chart_config = generate_chartjs_config(r.analytics)

            html += f"""
        <script>
        const chartConfig = {chart_config};

        // Initialize temporal chart if available
        if (chartConfig.temporal) {{
            new Chart(document.getElementById('temporal-chart'), chartConfig.temporal);
        }}

        // Initialize hourly chart if available
        if (chartConfig.hourly) {{
            new Chart(document.getElementById('hourly-chart'), chartConfig.hourly);
        }}
        </script>
"""

        html += """
        <footer>Generated by Log Analyzer Toolkit</footer>
    </div>
</body>
</html>"""

        return html

    def to_csv(self) -> str:
        """
        Generate a CSV export of analysis results.

        Returns:
            CSV-formatted data string
        """
        import csv
        import io

        r = self.result
        output = io.StringIO()
        writer = csv.writer(output)

        # Metadata section
        writer.writerow(["# Log Analysis Report"])
        writer.writerow(["File", r.filepath])
        writer.writerow(["Format", r.detected_format])
        writer.writerow(["Total Lines", r.total_lines])
        writer.writerow(["Parsed Lines", r.parsed_lines])
        writer.writerow(["Failed Lines", r.failed_lines])
        writer.writerow(["Parse Success Rate", f"{r.parse_success_rate:.2f}%"])
        writer.writerow(["Error Rate", f"{r.error_rate:.2f}%"])
        if r.time_span:
            writer.writerow(["Time Span", str(r.time_span)])
        writer.writerow([])

        # Severity breakdown
        if r.level_counts:
            writer.writerow(["# Severity Breakdown"])
            writer.writerow(["Level", "Count", "Percentage"])
            for level, count in sorted(r.level_counts.items()):
                pct = (count / r.parsed_lines * 100) if r.parsed_lines > 0 else 0
                writer.writerow([level, count, f"{pct:.2f}"])
            writer.writerow([])

        # HTTP Status Codes
        if r.status_codes:
            writer.writerow(["# HTTP Status Codes"])
            writer.writerow(["Code", "Count"])
            for code, count in sorted(r.status_codes.items()):
                writer.writerow([code, count])
            writer.writerow([])

        # Top Errors
        if r.top_errors:
            writer.writerow(["# Top Errors"])
            writer.writerow(["Count", "Message"])
            for msg, count in r.top_errors[:20]:
                writer.writerow([count, msg])
            writer.writerow([])

        # Top Sources
        if r.top_sources:
            writer.writerow(["# Top Sources"])
            writer.writerow(["Source", "Requests"])
            for source, count in r.top_sources[:20]:
                writer.writerow([source, count])
            writer.writerow([])

        # Analytics (if available)
        if r.analytics:
            writer.writerow(["# Analytics"])
            writer.writerow(["Trend", r.analytics.trend_direction])
            writer.writerow(["Peak Period", r.analytics.peak_period or 'N/A'])
            writer.writerow([])

            if r.analytics.hourly_distribution:
                writer.writerow(["# Hourly Distribution"])
                writer.writerow(["Hour", "Count"])
                for hour, count in sorted(r.analytics.hourly_distribution.items()):
                    writer.writerow([f"{hour:02d}:00", count])
                writer.writerow([])

            if r.analytics.temporal_distribution:
                writer.writerow(["# Temporal Distribution"])
                writer.writerow(["Timestamp", "Count"])
                for timestamp, count in sorted(r.analytics.temporal_distribution.items()):
                    writer.writerow([timestamp, count])

        return output.getvalue()

    def to_json(self) -> str:
        """
        Generate a JSON export of analysis results.

        Returns:
            JSON-formatted data string
        """
        import json

        r = self.result

        data = {
            "metadata": {
                "filepath": r.filepath,
                "format": r.detected_format,
                "total_lines": r.total_lines,
                "parsed_lines": r.parsed_lines,
                "failed_lines": r.failed_lines,
                "parse_success_rate": r.parse_success_rate,
                "error_rate": r.error_rate,
                "time_span": str(r.time_span) if r.time_span else None,
                "earliest_timestamp": r.earliest_timestamp.isoformat() if r.earliest_timestamp else None,
                "latest_timestamp": r.latest_timestamp.isoformat() if r.latest_timestamp else None,
            },
            "severity": {
                level: count for level, count in r.level_counts.items()
            },
            "top_errors": [
                {"message": msg, "count": count}
                for msg, count in r.top_errors[:20]
            ],
            "top_sources": [
                {"source": src, "count": count}
                for src, count in r.top_sources[:20]
            ],
        }

        # HTTP Status codes (if present)
        if r.status_codes:
            data["status_codes"] = {str(code): count for code, count in r.status_codes.items()}

        # Analytics (if available)
        if r.analytics:
            data["analytics"] = r.analytics.to_dict()

        return json.dumps(data, indent=2, default=str)

    def save(self, output_path: str, format: str = "markdown") -> None:
        """
        Save report to file.

        Args:
            output_path: Path to save the report
            format: 'markdown', 'html', 'csv', or 'json'
        """
        if format == "html":
            content = self.to_html()
        elif format == "csv":
            content = self.to_csv()
        elif format == "json":
            content = self.to_json()
        else:
            content = self.to_markdown()

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
