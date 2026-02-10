#!/usr/bin/env python3
"""
Demo script showing Phase 3B.1: Time-Series Analysis in action.

Creates a sample log file and analyzes it with analytics enabled.
"""

import tempfile
import os
from datetime import datetime, timedelta
from log_analyzer.analyzer import LogAnalyzer


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
                       f'"source": "app-server-{i % 3}"}}\n')

    print(f"✓ Created demo log: {filepath}")
    print(f"  Total entries: ~{sum(hour_patterns.values())}")
    print(f"  Time range: 9am - 6pm")
    print(f"  Expected burst: 3pm (50 errors)")
    print()

    return filepath


def analyze_with_analytics(filepath):
    """Analyze log file with analytics enabled."""
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

    # Display results
    print(f"\n📊 Basic Analysis Results:")
    print(f"  Format: {result.detected_format}")
    print(f"  Total lines: {result.total_lines:,}")
    print(f"  Parsed lines: {result.parsed_lines:,}")
    print(f"  Error rate: {result.error_rate:.1f}%")
    print(f"  Time span: {result.time_span}")

    # Display analytics
    if result.analytics:
        print(f"\n📈 Time-Series Analytics:")
        print(f"  Trend: {result.analytics.trend_direction}")
        print(f"  Peak period: {result.analytics.peak_period}")

        print(f"\n⏰ Hourly Distribution:")
        for hour, count in sorted(result.analytics.hourly_distribution.items()):
            bar = '█' * (count // 2)  # Simple bar chart
            print(f"    {hour:02d}:00 | {count:3d} | {bar}")

        print(f"\n📅 Temporal Distribution (1-hour buckets):")
        for timestamp, count in sorted(result.analytics.temporal_distribution.items()):
            time_str = timestamp.split('T')[1][:5]  # Extract HH:MM
            bar = '█' * (count // 2)
            indicator = " ← PEAK" if timestamp == result.analytics.peak_period else ""
            print(f"    {time_str} | {count:3d} | {bar}{indicator}")

        print()
        print("=" * 70)
        print("✓ Analysis complete!")
        print()
        print("🔍 Key Findings:")
        print(f"  • Detected {result.analytics.trend_direction} trend")
        print(f"  • Peak activity at {result.analytics.peak_period}")
        print(f"  • {len(result.analytics.hourly_distribution)} hours of activity")
        print(f"  • {len(result.analytics.temporal_distribution)} time buckets")

    else:
        print("\n⚠️  Analytics not available")


def main():
    """Main demo execution."""
    print()
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║  Phase 3B.1: Time-Series Analysis Demo                           ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()

    # Create demo log
    filepath = create_demo_log()

    try:
        # Analyze with analytics
        analyze_with_analytics(filepath)

    finally:
        # Clean up
        if os.path.exists(filepath):
            os.unlink(filepath)
            print(f"\n✓ Cleaned up demo file: {filepath}")
            print()


if __name__ == "__main__":
    main()
