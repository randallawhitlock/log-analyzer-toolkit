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
- 🧠 **AI-Powered Triage** - Intelligent analysis with Claude, Gemini, or Ollama
- 🔒 **Privacy Options** - Local LLM support via Ollama for sensitive logs

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

## 🧠 AI-Powered Log Triage

The toolkit includes intelligent log analysis using AI providers. Get automated issue detection, severity classification, and actionable recommendations.

### Setup AI Providers

Choose one or more providers:

```bash
# Option 1: Anthropic Claude (recommended for accuracy)
export ANTHROPIC_API_KEY="your-api-key"

# Option 2: Google Gemini (fast and capable)
export GOOGLE_API_KEY="your-api-key"

# Option 3: Ollama (local, privacy-focused)
ollama serve
ollama pull llama3.3
```

### Run AI Triage

```bash
# Auto-detect provider and analyze
python -m log_analyzer triage /var/log/app.log

# Use specific provider
python -m log_analyzer triage --provider ollama /var/log/app.log

# Get JSON output for automation
python -m log_analyzer triage --json /var/log/app.log
```

### Check Provider Status

```bash
python -m log_analyzer configure --show
```

### Supported AI Providers

| Provider | Models | Best For |
|----------|--------|----------|
| **Anthropic** | Claude Sonnet 4.5, Opus 4.5 | Highest accuracy analysis |
| **Gemini** | Gemini 3 Pro, Flash | Fast, capable analysis |
| **Ollama** | llama3.3, mistral, etc. | Privacy, local processing |

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
│   ├── __init__.py        # Package info
│   ├── __main__.py        # CLI entry point
│   ├── analyzer.py        # Core analysis engine
│   ├── cli.py             # Command-line interface
│   ├── config.py          # Configuration management
│   ├── parsers.py         # Log format parsers
│   ├── reader.py          # File reading utilities
│   ├── report.py          # Report generation
│   ├── triage.py          # AI triage engine
│   └── ai_providers/      # AI provider integrations
│       ├── __init__.py
│       ├── base.py        # Base classes and interfaces
│       ├── factory.py     # Provider factory
│       ├── anthropic_provider.py
│       ├── gemini_provider.py
│       └── ollama_provider.py
├── tests/
│   ├── test_analyzer.py
│   ├── test_ai_providers.py
│   ├── test_config.py
│   ├── test_parsers.py
│   └── test_triage.py
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

### AI Triage Usage

```python
from log_analyzer.triage import quick_triage, TriageEngine

# Quick one-liner triage
result = quick_triage("/var/log/app.log")
print(result.summary)
print(f"Severity: {result.overall_severity.value}")

# With specific provider
result = quick_triage("/var/log/app.log", provider="ollama")

# Using TriageEngine for more control
engine = TriageEngine(provider_name="anthropic")
result = engine.triage("/var/log/app.log")

for issue in result.issues:
    print(f"[{issue.severity.value}] {issue.title}")
    print(f"  Recommendation: {issue.recommendation}")
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
