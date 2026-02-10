"""
Command-line interface for Log Analyzer Toolkit.

Provides user-friendly commands for analyzing log files with
beautiful terminal output using the Rich library.
"""

import logging
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TaskProgressColumn
from rich import box

from .analyzer import LogAnalyzer, AnalysisResult, AVAILABLE_PARSERS
from .constants import (
    LEVEL_COLORS,
    MAX_MESSAGE_LENGTH,
    MAX_DISPLAY_ENTRIES,
    DEFAULT_MAX_ERRORS,
)


console = Console()
logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False, log_file: str = None):
    """Configure logging based on user preferences."""
    # Set level based on verbosity
    level = logging.DEBUG if verbose else logging.INFO

    # Configure format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Configure handlers
    handlers = []

    # Always add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(file_handler)

    # Add console handler only if verbose
    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(log_format))
        handlers.append(console_handler)

    # Configure root logger
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=handlers if handlers else [logging.NullHandler()]
    )


def format_level(level: str) -> Text:
    """Format log level with appropriate color."""
    return Text(level, style=LEVEL_COLORS.get(level, 'white'))


def format_count(count: int, total: int) -> Text:
    """Format a count with percentage."""
    pct = (count / total * 100) if total > 0 else 0
    return Text(f"{count:,} ({pct:.1f}%)")


@click.group()
@click.version_option(version='0.1.0')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging output')
@click.option('--log-file', type=click.Path(), help='Write logs to a file')
@click.pass_context
def cli(ctx, verbose: bool, log_file: str):
    """
    Log Analyzer Toolkit - Parse and analyze log files.

    A powerful tool for troubleshooting and analyzing logs from
    various sources including Apache, nginx, JSON, and syslog formats.
    """
    # Setup logging based on user preferences
    setup_logging(verbose=verbose, log_file=log_file)

    # Store config in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['log_file'] = log_file

    logger.debug(f"CLI initialized with verbose={verbose}, log_file={log_file}")


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--format', '-f', 'log_format',
              type=click.Choice(['auto', 'apache_access', 'apache_error',
                                'nginx_access', 'json', 'syslog']),
              default='auto', help='Log format (default: auto-detect)')
@click.option('--max-errors', '-e', default=DEFAULT_MAX_ERRORS,
              help='Maximum errors to display')
@click.option('--workers', '-w', 'max_workers', type=int,
              help='Number of worker threads (default: CPU count)')
@click.option('--no-threading', is_flag=True,
              help='Disable multithreaded processing')
@click.option('--enable-analytics', is_flag=True,
              help='Enable advanced analytics (time-series, pattern analysis)')
@click.option('--time-bucket', default='1h',
              type=click.Choice(['5min', '15min', '1h', '1day']),
              help='Time bucket size for temporal analysis (default: 1h)')
@click.option('--report', type=click.Choice(['markdown', 'html', 'csv', 'json']),
              help='Generate report in specified format')
@click.option('--output', '-o', type=click.Path(),
              help='Output file path for report')
def analyze(filepath: str, log_format: str, max_errors: int, max_workers: int, no_threading: bool,
            enable_analytics: bool, time_bucket: str, report: str, output: str):
    """
    Analyze a log file and display summary statistics.

    FILEPATH is the path to the log file to analyze.
    """
    logger.info(f"Starting analysis of {filepath}")
    logger.debug(f"Parameters: log_format={log_format}, max_errors={max_errors}, "
                f"max_workers={max_workers}, no_threading={no_threading}")

    console.print()

    analyzer = LogAnalyzer(max_workers=max_workers)

    # Get parser
    parser = None
    if log_format != 'auto':
        for p in AVAILABLE_PARSERS:
            if p.name == log_format:
                parser = p
                logger.debug(f"Using parser: {parser.name}")
                break

    try:
        # Count lines for progress tracking
        from .reader import LogReader
        with console.status("[dim]Counting lines..."):
            reader = LogReader(filepath)
            total_lines = reader.count_lines()
            logger.debug(f"File has {total_lines:,} lines")

        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            console=console,
            transient=False,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Analyzing {Path(filepath).name}...",
                total=total_lines
            )

            # Create a simple progress updater
            class ProgressUpdater:
                def __init__(self, progress_obj, task_id):
                    self.progress = progress_obj
                    self.task_id = task_id

                def update(self, advance=1):
                    self.progress.update(self.task_id, advance=advance)

            # Build analytics config
            analytics_config = {
                'time_bucket_size': time_bucket,
                'enable_time_series': True,
            }

            result = analyzer.analyze(
                filepath,
                parser=parser,
                max_errors=max_errors,
                progress_callback=ProgressUpdater(progress, task),
                use_threading=not no_threading,
                enable_analytics=enable_analytics,
                analytics_config=analytics_config if enable_analytics else None
            )

        logger.info(f"Analysis completed: {result.parsed_lines} lines parsed, "
                   f"{result.failed_lines} failed, error_rate={result.error_rate:.1f}%")

    except KeyboardInterrupt:
        logger.info("Analysis cancelled by user")
        console.print("\n[yellow]Analysis cancelled by user.[/yellow]")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except ValueError as e:
        logger.error(f"ValueError during analysis: {e}")
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
        console.print(f"[red]Unexpected error:[/red] {e}")
        sys.exit(1)

    # Display results in terminal (unless only generating a report)
    if not report or not output:
        _display_analysis(result)

    # Generate report if requested
    if report:
        from .report import ReportGenerator

        console.print()
        with console.status(f"[bold blue]Generating {report.upper()} report..."):
            generator = ReportGenerator(result)

            if report == 'markdown':
                content = generator.to_markdown()
            elif report == 'html':
                content = generator.to_html()
            elif report == 'csv':
                content = generator.to_csv()
            elif report == 'json':
                content = generator.to_json()
            else:
                content = generator.to_markdown()

        if output:
            with open(output, 'w', encoding='utf-8') as f:
                f.write(content)
            console.print(f"[green]✓ Report saved to {output}[/green]")
        else:
            # Output to console if no output file specified
            console.print()
            console.print(content)


def _display_analysis(result: AnalysisResult):
    """Display analysis results in a formatted layout."""
    
    # Header
    console.print(Panel(
        f"[bold]{Path(result.filepath).name}[/bold]\n"
        f"Format: [cyan]{result.detected_format}[/cyan]",
        title="📊 Log Analysis Report",
        border_style="blue"
    ))
    console.print()
    
    # Overview table
    overview = Table(title="Overview", box=box.ROUNDED, show_header=False)
    overview.add_column("Metric", style="bold")
    overview.add_column("Value", justify="right")
    
    overview.add_row("Total Lines", f"{result.total_lines:,}")
    overview.add_row("Parsed Lines", f"{result.parsed_lines:,}")
    overview.add_row("Failed Lines", f"{result.failed_lines:,}")
    overview.add_row("Parse Success", f"{result.parse_success_rate:.1f}%")
    overview.add_row("Error Rate", f"{result.error_rate:.1f}%")
    
    if result.time_span:
        overview.add_row("Time Span", str(result.time_span))
    if result.earliest_timestamp:
        overview.add_row("First Entry", result.earliest_timestamp.strftime("%Y-%m-%d %H:%M:%S"))
    if result.latest_timestamp:
        overview.add_row("Last Entry", result.latest_timestamp.strftime("%Y-%m-%d %H:%M:%S"))
    
    console.print(overview)
    console.print()
    
    # Severity breakdown
    if result.level_counts:
        severity = Table(title="Severity Breakdown", box=box.ROUNDED)
        severity.add_column("Level", style="bold")
        severity.add_column("Count", justify="right")
        severity.add_column("Percentage", justify="right")
        
        for level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']:
            count = result.level_counts.get(level, 0)
            if count > 0:
                pct = (count / result.parsed_lines * 100) if result.parsed_lines > 0 else 0
                severity.add_row(
                    format_level(level),
                    f"{count:,}",
                    f"{pct:.1f}%"
                )
        
        console.print(severity)
        console.print()
    
    # HTTP Status codes (for access logs)
    if result.status_codes:
        status = Table(title="HTTP Status Codes", box=box.ROUNDED)
        status.add_column("Code", style="bold")
        status.add_column("Count", justify="right")
        status.add_column("Category")
        
        categories = {
            2: ("2xx Success", "green"),
            3: ("3xx Redirect", "yellow"),
            4: ("4xx Client Error", "orange1"),
            5: ("5xx Server Error", "red"),
        }
        
        for code in sorted(result.status_codes.keys()):
            count = result.status_codes[code]
            cat_key = code // 100
            cat_name, cat_style = categories.get(cat_key, ("Unknown", "dim"))
            status.add_row(
                str(code),
                f"{count:,}",
                Text(cat_name, style=cat_style)
            )
        
        console.print(status)
        console.print()
    
    # Top Error Messages
    if result.top_errors:
        errors = Table(title="Top Error Messages", box=box.ROUNDED)
        errors.add_column("Count", justify="right", style="red")
        errors.add_column("Message")

        for msg, count in result.top_errors[:MAX_DISPLAY_ENTRIES]:
            truncated = msg[:MAX_MESSAGE_LENGTH] + "..." if len(msg) > MAX_MESSAGE_LENGTH else msg
            errors.add_row(str(count), truncated)
        
        console.print(errors)
        console.print()
    
    # Top Sources
    if result.top_sources:
        sources = Table(title="Top Sources", box=box.ROUNDED)
        sources.add_column("Source", style="cyan")
        sources.add_column("Requests", justify="right")

        for source, count in result.top_sources[:MAX_DISPLAY_ENTRIES]:
            sources.add_row(source, f"{count:,}")

        console.print(sources)

    # Analytics (if enabled)
    if result.analytics:
        console.print()
        _display_analytics(result.analytics, console)


def _display_analytics(analytics, console: Console):
    """Display analytics data in terminal."""
    # Import here to avoid circular dependency
    from .stats_models import AnalyticsData

    # Time-Series Summary Panel
    console.print(Panel(
        f"Trend: [cyan]{analytics.trend_direction}[/cyan]\n"
        f"Peak Period: [yellow]{analytics.peak_period or 'N/A'}[/yellow]\n"
        f"Active Hours: [green]{len(analytics.hourly_distribution)}[/green]",
        title="📈 Time-Series Analytics",
        border_style="cyan"
    ))
    console.print()

    # Hourly Distribution Bar Chart (ASCII)
    if analytics.hourly_distribution:
        _display_hourly_chart(analytics.hourly_distribution, console)
        console.print()

    # Temporal Distribution (recent buckets)
    if analytics.temporal_distribution:
        _display_temporal_table(analytics.temporal_distribution, console)


def _display_hourly_chart(hourly_dist: dict, console: Console):
    """Display hourly distribution as ASCII bar chart."""
    if not hourly_dist:
        return

    max_count = max(hourly_dist.values())

    table = Table(title="Hourly Distribution (24-hour)", box=box.ROUNDED)
    table.add_column("Hour", justify="right", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Activity", width=40)

    for hour in range(24):
        count = hourly_dist.get(hour, 0)
        if count > 0:
            bar_width = int((count / max_count) * 40) if max_count > 0 else 0
            bar = "█" * bar_width
            table.add_row(f"{hour:02d}:00", f"{count:,}", bar)

    console.print(table)


def _display_temporal_table(temporal_dist: dict, console: Console):
    """Display temporal distribution table (showing recent buckets)."""
    if not temporal_dist:
        return

    # Sort by timestamp and show last 10 buckets
    sorted_buckets = sorted(temporal_dist.items())[-10:]

    table = Table(title="Recent Activity (Time Buckets)", box=box.ROUNDED)
    table.add_column("Time Period", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Activity", width=30)

    max_count = max(count for _, count in sorted_buckets) if sorted_buckets else 1

    for timestamp_str, count in sorted_buckets:
        # Format timestamp for display (show just the time portion)
        try:
            # Extract time portion from ISO format
            if 'T' in timestamp_str:
                time_part = timestamp_str.split('T')[1][:5]  # HH:MM
                date_part = timestamp_str.split('T')[0][5:]  # MM-DD
                display_time = f"{date_part} {time_part}"
            else:
                display_time = timestamp_str[:16]
        except (IndexError, ValueError):
            display_time = timestamp_str

        bar_width = int((count / max_count) * 30) if max_count > 0 else 0
        bar = "█" * bar_width

        table.add_row(display_time, f"{count:,}", bar)

    console.print(table)


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
def detect(filepath: str):
    """
    Detect the log format of a file.
    
    FILEPATH is the path to the log file to analyze.
    """
    analyzer = LogAnalyzer()
    parser = analyzer.detect_format(filepath)
    
    if parser:
        console.print(f"[green]Detected format:[/green] [bold]{parser.name}[/bold]")
    else:
        console.print("[yellow]Could not determine log format[/yellow]")
        sys.exit(1)


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--level', '-l', 
              type=click.Choice(['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']),
              default='ERROR', help='Minimum level to show')
@click.option('--limit', '-n', default=20, help='Maximum entries to show')
def errors(filepath: str, level: str, limit: int):
    """
    Show errors and warnings from a log file.
    
    FILEPATH is the path to the log file to analyze.
    """
    level_order = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    min_level_idx = level_order.index(level)
    
    analyzer = LogAnalyzer()
    count = 0
    
    console.print(f"[bold]Errors from {Path(filepath).name}[/bold]")
    console.print()
    
    for entry in analyzer.parse_file(filepath):
        if entry.level and level_order.index(entry.level) >= min_level_idx:
            ts = entry.timestamp.strftime("%H:%M:%S") if entry.timestamp else "---"
            console.print(f"[dim]{ts}[/dim] ", end="")
            console.print(format_level(entry.level), end=" ")
            console.print(entry.message[:MAX_MESSAGE_LENGTH])
            
            count += 1
            if count >= limit:
                console.print(f"\n[dim]... showing first {limit} matches[/dim]")
                break
    
    if count == 0:
        console.print(f"[green]No entries at {level} level or above[/green]")


@cli.command()
def formats():
    """List all supported log formats."""
    table = Table(title="Supported Log Formats", box=box.ROUNDED)
    table.add_column("Format Name", style="cyan bold")
    table.add_column("Description")
    
    descriptions = {
        'aws_cloudwatch': 'AWS CloudWatch Logs (JSON and plain text)',
        'gcp_logging': 'Google Cloud Logging (Stackdriver format)',
        'azure_monitor': 'Azure Monitor and Application Insights logs',
        'docker_json': 'Docker container logs (JSON format)',
        'kubernetes': 'Kubernetes pod logs with metadata',
        'containerd': 'containerd CRI logs',
        'apache_access': 'Apache Combined Log Format (access.log)',
        'apache_error': 'Apache Error Log Format (error.log)',
        'nginx_access': 'nginx Access Log Format',
        'json': 'JSON structured logging (various apps)',
        'syslog': 'Syslog format (RFC 3164 & RFC 5424)',
    }
    
    for parser in AVAILABLE_PARSERS:
        table.add_row(parser.name, descriptions.get(parser.name, ""))
    
    console.print(table)


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--provider', '-p',
              type=click.Choice(['anthropic', 'gemini', 'ollama', 'auto']),
              default='auto', help='AI provider to use (default: auto-detect)')
@click.option('--format', '-f', 'log_format',
              type=click.Choice(['auto', 'apache_access', 'apache_error',
                                'nginx_access', 'json', 'syslog']),
              default='auto', help='Log format (default: auto-detect)')
@click.option('--json', 'output_json', is_flag=True,
              help='Output results as JSON')
def triage(filepath: str, provider: str, log_format: str, output_json: bool):
    """
    AI-powered intelligent log triage.
    
    Analyzes FILEPATH using AI to identify issues, assess severity,
    and provide actionable recommendations.
    
    Examples:
    
        log_analyzer triage /var/log/app.log
        
        log_analyzer triage --provider ollama /var/log/app.log
        
        log_analyzer triage --json /var/log/app.log
    """
    import json as json_module
    
    from .triage import TriageEngine
    from .ai_providers import get_provider, ProviderNotAvailableError
    from .ai_providers.base import Severity
    
    logger.info(f"Starting AI triage of {filepath}")
    logger.debug(f"Parameters: provider={provider}, log_format={log_format}, output_json={output_json}")

    console.print()

    # Get provider name (None means auto-detect)
    provider_name = None if provider == 'auto' else provider

    try:
        with console.status("[bold blue]Initializing AI provider..."):
            engine = TriageEngine(provider_name=provider_name)
            ai_provider = engine._get_provider()
            logger.info(f"AI provider initialized: {ai_provider.name} ({ai_provider.get_model()})")

        console.print(f"[dim]Using provider:[/dim] [cyan]{ai_provider.name}[/cyan] "
                     f"([dim]{ai_provider.get_model()}[/dim])")
        console.print()

        with console.status("[bold blue]Analyzing log file..."):
            # Get parser if specified
            parser = None
            if log_format != 'auto':
                for p in AVAILABLE_PARSERS:
                    if p.name == log_format:
                        parser = p.name
                        logger.debug(f"Using parser: {parser}")
                        break

            result = engine.triage(filepath, parser=parser)
            logger.info(f"Triage completed: {len(result.issues)} issues identified, "
                       f"overall_severity={result.overall_severity.value}, "
                       f"confidence={result.confidence:.2f}")

    except KeyboardInterrupt:
        logger.info("Triage cancelled by user")
        console.print("\n[yellow]Triage cancelled by user.[/yellow]")
        sys.exit(130)  # Standard exit code for Ctrl+C
    except ProviderNotAvailableError as e:
        logger.error(f"Provider not available: {e}")
        console.print(f"[red]Error:[/red] {e}")
        console.print()
        console.print("[yellow]To configure a provider:[/yellow]")
        console.print("  • Set ANTHROPIC_API_KEY environment variable")
        console.print("  • Set GOOGLE_API_KEY environment variable")
        console.print("  • Start Ollama locally: ollama serve")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"ValueError during triage: {e}")
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during triage: {e}", exc_info=True)
        console.print(f"[red]Error during analysis:[/red] {e}")
        sys.exit(1)
    
    # Output as JSON if requested
    if output_json:
        console.print(json_module.dumps(result.to_dict(), indent=2))
        return
    
    # Display rich triage results
    _display_triage(result, filepath)


def _display_triage(result, filepath: str):
    """Display triage results in a formatted layout."""
    from .ai_providers.base import Severity
    
    # Severity colors
    severity_colors = {
        Severity.CRITICAL: 'bold red',
        Severity.HIGH: 'red',
        Severity.MEDIUM: 'yellow',
        Severity.LOW: 'blue',
        Severity.HEALTHY: 'green',
    }
    
    # Header panel
    severity_text = Text(result.overall_severity.value, 
                        style=severity_colors.get(result.overall_severity, 'white'))
    
    header_content = (
        f"[bold]{Path(filepath).name}[/bold]\n"
        f"Provider: [cyan]{result.provider_used}[/cyan] • "
        f"Confidence: [cyan]{result.confidence:.0%}[/cyan]"
    )
    
    console.print(Panel(
        header_content,
        title=f"🧠 AI Triage Report - {severity_text}",
        border_style=severity_colors.get(result.overall_severity, 'blue')
    ))
    console.print()
    
    # Summary
    console.print(Panel(result.summary, title="📋 Summary", border_style="blue"))
    console.print()
    
    # Statistics
    stats = Table(title="📊 Statistics", box=box.ROUNDED, show_header=False)
    stats.add_column("Metric", style="bold")
    stats.add_column("Value", justify="right")
    
    stats.add_row("Lines Analyzed", f"{result.analyzed_lines:,}")
    stats.add_row("Errors Found", f"{result.error_count:,}")
    stats.add_row("Warnings Found", f"{result.warning_count:,}")
    if result.analysis_time_ms:
        stats.add_row("Analysis Time", f"{result.analysis_time_ms:.0f}ms")
    
    console.print(stats)
    console.print()
    
    # Issues
    if result.issues:
        console.print(f"[bold]🔍 Identified Issues ({len(result.issues)})[/bold]")
        console.print()
        
        for i, issue in enumerate(result.issues, 1):
            issue_color = severity_colors.get(issue.severity, 'white')
            
            # Issue header
            console.print(Panel(
                f"[bold]{issue.title}[/bold]\n\n"
                f"{issue.description}\n\n"
                f"[bold]Recommendation:[/bold] {issue.recommendation}",
                title=f"Issue {i} - {Text(issue.severity.value, style=issue_color)} "
                      f"(Confidence: {issue.confidence:.0%})",
                border_style=issue_color,
            ))
            console.print()
    else:
        console.print("[green]✅ No significant issues identified[/green]")
        console.print()


@cli.command()
@click.option('--provider', '-p',
              type=click.Choice(['anthropic', 'gemini', 'ollama']),
              help='Configure a specific provider')
@click.option('--show', '-s', is_flag=True,
              help='Show current configuration')
def configure(provider: str, show: bool):
    """
    Configure AI providers for log triage.
    
    Shows the current configuration status or helps set up providers.
    
    Examples:
    
        log_analyzer configure --show
        
        log_analyzer configure --provider anthropic
    """
    from .config import get_provider_status, get_config, mask_api_key
    
    if show or (not provider):
        # Show current configuration
        console.print()
        console.print(Panel("AI Provider Configuration", border_style="blue"))
        console.print()
        
        status = get_provider_status()
        
        table = Table(box=box.ROUNDED)
        table.add_column("Provider", style="cyan bold")
        table.add_column("Status")
        table.add_column("Model")
        table.add_column("API Key")
        
        for name, info in status.items():
            if info["configured"]:
                status_icon = "[green]✅ Ready[/green]"
            else:
                status_icon = "[yellow]⚠️ Not configured[/yellow]"
            
            # For Ollama, show server status
            if name == "ollama":
                if info.get("server_available"):
                    status_icon = "[green]✅ Server running[/green]"
                else:
                    status_icon = "[yellow]⚠️ Server not running[/yellow]"
            
            table.add_row(
                name.capitalize(),
                status_icon,
                info["model"],
                info["api_key_display"],
            )
        
        console.print(table)
        console.print()
        
        # Show setup instructions
        console.print("[bold]Setup Instructions:[/bold]")
        console.print()
        console.print("[cyan]Anthropic Claude:[/cyan]")
        console.print("  export ANTHROPIC_API_KEY='your-api-key'")
        console.print()
        console.print("[cyan]Google Gemini:[/cyan]")
        console.print("  export GOOGLE_API_KEY='your-api-key'")
        console.print()
        console.print("[cyan]Ollama (local):[/cyan]")
        console.print("  ollama serve")
        console.print("  ollama pull llama3.3")
        console.print()
        
        return
    
    # Provider-specific configuration
    if provider == "anthropic":
        _configure_anthropic()
    elif provider == "gemini":
        _configure_gemini()
    elif provider == "ollama":
        _configure_ollama()


def _configure_anthropic():
    """Help configure Anthropic provider."""
    import os
    
    console.print()
    console.print(Panel("Anthropic Claude Configuration", border_style="blue"))
    console.print()
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        from .config import mask_api_key
        console.print(f"[green]✅ API key found:[/green] {mask_api_key(api_key)}")
    else:
        console.print("[yellow]⚠️ ANTHROPIC_API_KEY not set[/yellow]")
        console.print()
        console.print("To configure:")
        console.print("1. Get an API key from https://console.anthropic.com/")
        console.print("2. Set the environment variable:")
        console.print("   [cyan]export ANTHROPIC_API_KEY='your-key'[/cyan]")
    
    console.print()


def _configure_gemini():
    """Help configure Gemini provider."""
    import os
    
    console.print()
    console.print(Panel("Google Gemini Configuration", border_style="blue"))
    console.print()
    
    api_key = os.environ.get("GOOGLE_API_KEY")
    if api_key:
        from .config import mask_api_key
        console.print(f"[green]✅ API key found:[/green] {mask_api_key(api_key)}")
    else:
        console.print("[yellow]⚠️ GOOGLE_API_KEY not set[/yellow]")
        console.print()
        console.print("To configure:")
        console.print("1. Get an API key from https://aistudio.google.com/apikey")
        console.print("2. Set the environment variable:")
        console.print("   [cyan]export GOOGLE_API_KEY='your-key'[/cyan]")
    
    console.print()


def _configure_ollama():
    """Help configure Ollama provider."""
    console.print()
    console.print(Panel("Ollama Local Configuration", border_style="blue"))
    console.print()
    
    try:
        from .ai_providers.ollama_provider import OllamaProvider
        ollama = OllamaProvider()
        
        if ollama.is_available():
            console.print("[green]✅ Ollama server is running[/green]")
            console.print()
            
            # List available models
            try:
                models = ollama.list_local_models()
                if models:
                    console.print("[bold]Installed models:[/bold]")
                    for model in models[:10]:
                        console.print(f"  • {model}")
                else:
                    console.print("[yellow]No models installed[/yellow]")
                    console.print("Run: [cyan]ollama pull llama3.3[/cyan]")
            except Exception:
                pass
        else:
            console.print("[yellow]⚠️ Ollama server not running[/yellow]")
            console.print()
            console.print("To start Ollama:")
            console.print("1. Install from https://ollama.ai")
            console.print("2. Start the server: [cyan]ollama serve[/cyan]")
            console.print("3. Pull a model: [cyan]ollama pull llama3.3[/cyan]")
    except Exception as e:
        console.print(f"[red]Error checking Ollama:[/red] {e}")
    
    console.print()


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()

