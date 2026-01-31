"""
Command-line interface for Log Analyzer Toolkit.

Provides user-friendly commands for analyzing log files with
beautiful terminal output using the Rich library.
"""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from .analyzer import LogAnalyzer, AnalysisResult
from .parsers import AVAILABLE_PARSERS


console = Console()


def format_level(level: str) -> Text:
    """Format log level with appropriate color."""
    colors = {
        'CRITICAL': 'bold red',
        'ERROR': 'red',
        'WARNING': 'yellow',
        'INFO': 'green',
        'DEBUG': 'dim',
    }
    return Text(level, style=colors.get(level, 'white'))


def format_count(count: int, total: int) -> Text:
    """Format a count with percentage."""
    pct = (count / total * 100) if total > 0 else 0
    return Text(f"{count:,} ({pct:.1f}%)")


@click.group()
@click.version_option(version='0.1.0')
def cli():
    """
    Log Analyzer Toolkit - Parse and analyze log files.
    
    A powerful tool for troubleshooting and analyzing logs from
    various sources including Apache, nginx, JSON, and syslog formats.
    """
    pass


@cli.command()
@click.argument('filepath', type=click.Path(exists=True))
@click.option('--format', '-f', 'log_format', 
              type=click.Choice(['auto', 'apache_access', 'apache_error', 
                                'nginx_access', 'json', 'syslog']),
              default='auto', help='Log format (default: auto-detect)')
@click.option('--max-errors', '-e', default=50, 
              help='Maximum errors to display')
def analyze(filepath: str, log_format: str, max_errors: int):
    """
    Analyze a log file and display summary statistics.
    
    FILEPATH is the path to the log file to analyze.
    """
    console.print()
    
    with console.status("[bold blue]Analyzing log file..."):
        analyzer = LogAnalyzer()
        
        # Get parser
        parser = None
        if log_format != 'auto':
            for p in AVAILABLE_PARSERS:
                if p.name == log_format:
                    parser = p
                    break
        
        try:
            result = analyzer.analyze(filepath, parser=parser, max_errors=max_errors)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
        except FileNotFoundError as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)
    
    _display_analysis(result)


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
        
        for msg, count in result.top_errors[:5]:
            truncated = msg[:80] + "..." if len(msg) > 80 else msg
            errors.add_row(str(count), truncated)
        
        console.print(errors)
        console.print()
    
    # Top Sources
    if result.top_sources:
        sources = Table(title="Top Sources", box=box.ROUNDED)
        sources.add_column("Source", style="cyan")
        sources.add_column("Requests", justify="right")
        
        for source, count in result.top_sources[:5]:
            sources.add_row(source, f"{count:,}")
        
        console.print(sources)


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
            console.print(entry.message[:100])
            
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
        'apache_access': 'Apache Combined Log Format (access.log)',
        'apache_error': 'Apache Error Log Format (error.log)',
        'nginx_access': 'nginx Access Log Format',
        'json': 'JSON structured logging (various apps)',
        'syslog': 'Syslog format (RFC 3164 & RFC 5424)',
    }
    
    for parser in AVAILABLE_PARSERS:
        table.add_row(parser.name, descriptions.get(parser.name, ""))
    
    console.print(table)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == '__main__':
    main()
