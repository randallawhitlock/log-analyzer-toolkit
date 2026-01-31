# Log Analyzer Toolkit

A powerful command-line tool for parsing, analyzing, and troubleshooting log files from various sources. Built to help support engineers quickly identify issues and patterns in logs.

## Features

- 🔍 **Multi-format Support** - Parse Apache, nginx, JSON, and syslog formats
- ⚠️ **Error Detection** - Automatically identify errors, warnings, and anomalies
- 📊 **Pattern Analysis** - Detect recurring issues and trends
- 📈 **Statistics** - Generate summary statistics and timelines
- 📄 **Report Export** - Export findings to Markdown or HTML

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```bash
# Analyze a single log file
python -m log_analyzer analyze /path/to/access.log

# Analyze with specific format
python -m log_analyzer analyze --format nginx /path/to/access.log

# Generate a report
python -m log_analyzer report /path/to/error.log --output report.md
```

## Supported Log Formats

| Format | File Types | Auto-Detection |
|--------|-----------|----------------|
| Apache | access.log, error.log | ✅ |
| nginx | access.log, error.log | ✅ |
| JSON | *.json, *.log | ✅ |
| Syslog | /var/log/syslog, messages | ✅ |

## Usage Examples

See the [examples](./examples/) directory for sample log files and usage patterns.

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## License

MIT License - see [LICENSE](./LICENSE) for details.
