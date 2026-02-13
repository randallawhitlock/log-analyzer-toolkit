#!/usr/bin/env python3
"""
Demo script showing Phase 3C: Enhanced Reporting in action.

Creates a sample log file and generates reports in all supported formats
with analytics visualization.
"""

import os
import tempfile
from datetime import datetime

from log_analyzer.analyzer import LogAnalyzer
from log_analyzer.report import ReportGenerator


def create_demo_log():
    """Create a demo log file with time-series patterns."""
    print("Creating demo log file with time-series patterns...")

    # Create temp file
    fd, filepath = tempfile.mkstemp(suffix='.log', text=True)

    with os.fdopen(fd, 'w') as f:
        base_time = datetime(2024, 2, 9, 9, 0, 0)

        # Simulate a day of logs with patterns:
        # - Normal activity 9am-12pm (5 logs/hour)
        # - Lunch break 12pm-1pm (2 logs/hour)
        # - Busy afternoon 1pm-3pm (10 logs/hour)
        # - BURST at 3pm (50 errors in one hour!)
        # - Normal evening 4pm-6pm (5 logs/hour)

        hour_patterns = {
            9: 5, 10: 5, 11: 5,              # Morning (normal)
            12: 2,                            # Lunch (quiet)
            13: 10, 14: 10,                   # Afternoon (busy)
            15: 50,                           # BURST (problem!)
            16: 5, 17: 5,                     # Evening (normal)
        }

        for hour, count in hour_patterns.items():
            for i in range(count):
                timestamp = base_time.replace(hour=hour, minute=i % 60)

                # Errors during burst, otherwise mostly info
                if hour == 15:  # Burst hour
                    level = "error"
                    msg = f"Database connection timeout (attempt {i})"
                else:
                    level = "info" if i % 10 != 0 else "warning"
                    msg = f"Processing request {i}"

                # Write JSON format log
                f.write(f'{{"timestamp": "{timestamp.isoformat()}", '
                       f'"level": "{level}", "msg": "{msg}", '
                       f'"source": "app-server-{i % 3}"}}\\n')

    print(f"✓ Created demo log: {filepath}")
    print(f"  Total entries: ~{sum(hour_patterns.values())}")
    print("  Time range: 9am - 6pm")
    print("  Expected burst: 3pm (50 errors)")
    print()

    return filepath


def generate_all_reports(filepath):
    """Generate all report formats with analytics."""
    print("Analyzing with advanced analytics...")
    print("=" * 70)

    analyzer = LogAnalyzer()

    # Analyze with analytics enabled
    result = analyzer.analyze(
        filepath,
        enable_analytics=True,
        analytics_config={
            'time_bucket_size': '1h',
            'enable_time_series': True,
        }
    )

    print("\n📊 Analysis Complete:")
    print(f"  Format: {result.detected_format}")
    print(f"  Total lines: {result.total_lines:,}")
    print(f"  Parsed lines: {result.parsed_lines:,}")
    print(f"  Error rate: {result.error_rate:.1f}%")
    print(f"  Time span: {result.time_span}")

    if result.analytics:
        print("\n📈 Analytics:")
        print(f"  Trend: {result.analytics.trend_direction}")
        print(f"  Peak period: {result.analytics.peak_period}")
        print(f"  Active hours: {len(result.analytics.hourly_distribution)}")

    # Generate all report formats
    print("\n" + "=" * 70)
    print("Generating reports in all formats...")
    print("=" * 70)

    generator = ReportGenerator(result)

    # Markdown report
    print("\n1. Markdown Report (report.md)")
    generator.save('report.md', format='markdown')
    print("   ✓ Generated: report.md")
    print("   → View with: cat report.md | less")

    # HTML report with charts
    print("\n2. HTML Report with Charts (report.html)")
    generator.save('report.html', format='html')
    print("   ✓ Generated: report.html")
    print("   → Open in browser to see interactive Chart.js visualizations")
    print("   → Charts: Time-series line chart + Hourly bar chart")

    # CSV export
    print("\n3. CSV Export (data.csv)")
    generator.save('data.csv', format='csv')
    print("   ✓ Generated: data.csv")
    print("   → Import into Excel, Google Sheets, or other spreadsheet tools")
    print("   → Includes: Metrics, severity breakdown, errors, analytics data")

    # JSON export
    print("\n4. JSON Export (data.json)")
    generator.save('data.json', format='json')
    print("   ✓ Generated: data.json")
    print("   → Use for programmatic access, APIs, or further processing")
    print("   → Includes: Full analysis results + analytics in structured format")

    print("\n" + "=" * 70)
    print("✓ All reports generated successfully!")
    print("=" * 70)

    # Display summary of what was created
    print("\n📁 Generated Files:")
    print("   • report.md    - Markdown report with tables")
    print("   • report.html  - Interactive HTML dashboard with Chart.js")
    print("   • data.csv     - CSV data for spreadsheet analysis")
    print("   • data.json    - JSON data for programmatic processing")

    print("\n🎯 Key Features Demonstrated:")
    print("   ✓ Time-series analytics (trend detection, peak identification)")
    print("   ✓ Hourly distribution analysis")
    print("   ✓ Interactive Chart.js visualizations (HTML only)")
    print("   ✓ Multiple export formats (Markdown, HTML, CSV, JSON)")
    print("   ✓ ASCII bar charts (Markdown)")
    print("   ✓ Zero dependencies (Chart.js via CDN)")

    print("\n💡 Next Steps:")
    print("   1. Open report.html in your browser")
    print("   2. View interactive charts (hover for details)")
    print("   3. Compare Markdown vs HTML presentations")
    print("   4. Import data.csv into a spreadsheet")
    print("   5. Parse data.json with your own tools")

    print()


def main():
    """Main demo execution."""
    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║  Phase 3C: Enhanced Reporting Demo                               ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()

    # Create demo log
    filepath = create_demo_log()

    try:
        # Generate all reports
        generate_all_reports(filepath)

    finally:
        # Clean up demo log file
        if os.path.exists(filepath):
            os.unlink(filepath)
            print(f"✓ Cleaned up demo file: {filepath}")
            print()


if __name__ == "__main__":
    main()
