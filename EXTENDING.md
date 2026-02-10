# Extending the Log Analyzer

This guide explains how to add custom log format parsers to the Log Analyzer Toolkit.

## Quick Start

```python
from log_analyzer.parsers import BaseParser, LogEntry, CustomParserRegistry

class MyCompanyLogParser(BaseParser):
    """Parser for MyCompany internal log format."""
    
    name = "mycompany"
    
    def can_parse(self, line: str) -> bool:
        """Return True if this line matches your format."""
        return line.startswith('[MYCO]')
    
    def parse(self, line: str) -> LogEntry | None:
        """Parse the line and return a LogEntry, or None if parsing fails."""
        # Extract fields from the line
        # Example: [MYCO] 2024-01-15 ERROR Database connection failed
        parts = line.split(' ', 4)
        
        return LogEntry(
            raw=line,
            timestamp=None,
            level=parts[2] if len(parts) > 2 else 'INFO',
            message=parts[4] if len(parts) > 4 else line,
            source='mycompany',
            metadata={'custom_field': 'value'}
        )

# Register your parser
CustomParserRegistry.register(MyCompanyLogParser)
```

## Using Custom Parsers

After registration, get all parsers including yours:

```python
from log_analyzer.parsers import CustomParserRegistry
from log_analyzer.analyzer import LogAnalyzer

# Get all parsers (built-in + custom + fallback)
all_parsers = CustomParserRegistry.get_all_parsers()

# Use with analyzer
analyzer = LogAnalyzer(parsers=all_parsers)
result = analyzer.analyze('/path/to/logs.log')
```

## Parser Requirements

Your parser class must:
1. Extend `BaseParser`
2. Define a unique `name` attribute
3. Implement `can_parse(line: str) -> bool`
4. Implement `parse(line: str) -> Optional[LogEntry]`

## LogEntry Fields

| Field | Type | Description |
|-------|------|-------------|
| `raw` | str | Original log line |
| `timestamp` | datetime | Parsed timestamp (or None) |
| `level` | str | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `message` | str | Main message content |
| `source` | str | Source identifier (IP, hostname, component) |
| `metadata` | dict | Additional parsed fields |

## Fallback Behavior

When no specific parser matches a log format, the `UniversalFallbackParser` is used. It:
- Attempts to extract timestamps using common patterns
- Detects log levels from keywords
- Marks entries with `metadata['parser_type'] = 'fallback'`

To disable fallback:
```python
result = analyzer.analyze('/path/to/logs.log', use_fallback=False)
```
