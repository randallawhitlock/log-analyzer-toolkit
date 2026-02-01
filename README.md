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

## 📚 Comprehensive Implementation Guide

Follow these steps to deploy and use the Log Analyzer Toolkit in your environment.

### Step 1: Installation

Install the package directly from source or via pip.

```bash
# Clone the repository
git clone https://github.com/yourusername/log-analyzer-toolkit.git
cd log-analyzer-toolkit

# Install standard dependencies
pip install -e .

# Optional: Install development tools (for running tests)
pip install -e ".[dev]"
```

### Step 2: Configuration & AI Setup

To unlock intelligent features, configure your preferred AI provider.

**Option A: Anthropic Claude (Recommended)**
Best for high-accuracy reasoning and complex root cause analysis.
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Option B: Google Gemini**
Fast and cost-effective analysis.
```bash
export GOOGLE_API_KEY="AIza..."
```

**Option C: local Ollama (Privacy-Focused)**
Run completely offline with local models (requires [Ollama](https://ollama.com/)).
```bash
ollama serve
ollama pull llama3.3
```

**Verify Configuration:**
```bash
python -m log_analyzer configure --show
```

### Step 3: Running Analysis (CLI)

The Command Line Interface (CLI) is the primary way to interact with the toolkit.

**Basic Static Analysis (No AI required)**
Get statistics, error rates, and traffic sources.
```bash
# Auto-detect format
python -m log_analyzer analyze /var/log/application.log

# Force specific format
python -m log_analyzer analyze --format nginx /var/log/nginx/access.log
```

**AI-Powered Triage**
Ask the AI to diagnose issues, explain errors, and suggest fixes.
```bash
# Standard triage (uses configured provider)
python -m log_analyzer triage /var/log/error.log

# Output JSON for CI/CD pipelines
python -m log_analyzer triage /var/log/error.log --json

# Force a specific provider (e.g., use local llm for sensitive logs)
python -m log_analyzer triage /var/log/secure.log --provider ollama
```

### Step 4: Python Integration

Integrate the analyzer directly into your monitoring scripts or dashboards.

**Static Analysis API:**
```python
from log_analyzer.analyzer import LogAnalyzer

analyzer = LogAnalyzer()
result = analyzer.analyze("/var/log/app.log")

print(f"Error Rate: {result.error_rate}%")
print(f"Total Lines: {result.total_lines}")
```

**AI Triage API:**
```python
from log_analyzer.triage import quick_triage

# Run diagnosis
diagnosis = quick_triage("/var/log/app.log", provider="anthropic")

print(f"Severity: {diagnosis.overall_severity.value}")
print(f"Summary: {diagnosis.summary}")

for issue in diagnosis.issues:
    print(f"Found: {issue.title}")
    print(f"Fix: {issue.recommendation}")
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
