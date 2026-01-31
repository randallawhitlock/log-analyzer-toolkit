# Log Analyzer Toolkit

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful command-line tool for parsing, analyzing, and troubleshooting log files from various sources. Built to help support engineers quickly identify issues and patterns in logs.

## ✨ Features

- 🔍 **Multi-format Support** - Parse Apache, nginx, JSON, and syslog formats
- 🎯 **Auto-Detection** - Automatically identifies log format
- ⚠️ **Error Detection** - Identify errors, warnings, and anomalies
- 📊 **Rich Statistics** - Generate comprehensive analysis reports
- 📈 **Pattern Analysis** - Detect recurring issues and top error sources
- 📄 **Export Reports** - Export findings to Markdown or HTML
- 🎨 **Beautiful CLI** - Color-coded terminal output with Rich

## 🚀 Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/log-analyzer-toolkit.git
cd log-analyzer-toolkit

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

## 📖 Quick Start

### Analyze a Log File

```bash
# Auto-detect format and analyze
python -m log_analyzer analyze /var/log/apache2/access.log

# Specify format manually
python -m log_analyzer analyze --format nginx /var/log/nginx/access.log
```

### Detect Log Format

```bash
python -m log_analyzer detect /path/to/logfile.log
```

### View Errors Only

```bash
# Show errors and above
python -m log_analyzer errors /var/log/app.log

# Show warnings and above, limit to 50 entries
python -m log_analyzer errors --level WARNING --limit 50 /var/log/app.log
```

### List Supported Formats

```bash
python -m log_analyzer formats
```

## 📊 Example Output

```
╭──────────────────────── 📊 Log Analysis Report ────────────────────────╮
│ access.log                                                              │
│ Format: apache_access                                                   │
╰─────────────────────────────────────────────────────────────────────────╯

┌──────────────────┬────────────┐
│ Metric           │      Value │
├──────────────────┼────────────┤
│ Total Lines      │     15,234 │
│ Parsed Lines     │     15,230 │
│ Parse Success    │      99.9% │
│ Error Rate       │       2.3% │
│ Time Span        │   24:00:00 │
└──────────────────┴────────────┘

┌───────────┬───────┬────────────┐
│ Level     │ Count │ Percentage │
├───────────┼───────┼────────────┤
│ ERROR     │   350 │       2.3% │
│ WARNING   │   892 │       5.9% │
│ INFO      │ 13988 │      91.8% │
└───────────┴───────┴────────────┘
```

## 📝 Supported Log Formats

| Format | Description | Auto-Detect |
|--------|-------------|-------------|
| `apache_access` | Apache Combined Log Format | ✅ |
| `apache_error` | Apache Error Log | ✅ |
| `nginx_access` | nginx Access Log | ✅ |
| `json` | JSON structured logging | ✅ |
| `syslog` | RFC 3164 & RFC 5424 | ✅ |

## 🧪 Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=log_analyzer
```

## 📁 Project Structure

```
log-analyzer-toolkit/
├── log_analyzer/
│   ├── __init__.py      # Package info
│   ├── __main__.py      # CLI entry point
│   ├── analyzer.py      # Core analysis engine
│   ├── cli.py           # Command-line interface
│   ├── parsers.py       # Log format parsers
│   ├── reader.py        # File reading utilities
│   └── report.py        # Report generation
├── tests/
│   ├── test_analyzer.py
│   └── test_parsers.py
├── examples/
│   ├── sample_access.log
│   └── sample_json.log
├── pyproject.toml
├── requirements.txt
└── README.md
```

## 🔧 Programmatic Usage

```python
from log_analyzer.analyzer import LogAnalyzer
from log_analyzer.report import ReportGenerator

# Analyze a log file
analyzer = LogAnalyzer()
result = analyzer.analyze("/var/log/app.log")

# Print summary
print(f"Total lines: {result.total_lines}")
print(f"Error rate: {result.error_rate:.1f}%")
print(f"Top errors: {result.top_errors[:5]}")

# Generate a report
report = ReportGenerator(result)
report.save("analysis_report.md", format="markdown")
report.save("analysis_report.html", format="html")
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [Click](https://click.palletsprojects.com/) for CLI framework
