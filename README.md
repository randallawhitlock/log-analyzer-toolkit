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
export ANTHROPIC_API_KEY="sk-ant-..."
export LOG_ANALYZER_PROVIDER="anthropic"  # Optional: Force this provider
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

#### ⚠️ Hardware Constraints & Model Selection
Running local LLMs requires sufficient RAM. Using a model too large for your system will cause performance degradation.

| System RAM | Recommended Max Model | Best Choices |
| :--- | :--- | :--- |
| **8GB** | < 7B Params | `phi3`, `mistral`, `gemma2:2b` |
| **16GB** (e.g., M2/M4 Air) | 7B - 14B Params | `llama3.3`, `qwen2.5-coder:14b`* |
| **32GB+** | 30B+ Params | `qwen2.5-coder:32b`, `mixtral` |

**Recommendation for 16GB Macs:**
For the best balance, use **Llama 3.3 (8B)** (default).
If you need specialized coding capabilities, you can try **Qwen 2.5 Coder (14B)**, but be aware it uses ~9GB RAM, leaving less for your OS.

**To use Qwen 2.5 Coder:**
```bash
ollama pull qwen2.5-coder:14b
# Then update ~/.log-analyzer/config.yaml to use this model
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

We welcome contributions to the Log Analyzer Toolkit! Whether it's bug fixes, new parsers, or AI enhancements, here's how to get started.

### Development Setup

1.  **Fork and Clone**
    ```bash
    git clone https://github.com/your-username/log-analyzer-toolkit.git
    cd log-analyzer-toolkit
    ```

2.  **Install Safe Dependencies**
    We recommend using a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows
    python -m venv venv
    source venv/bin/activate  # or venv\Scripts\activate on Windows
    pip install -e "."
    # If using Ollama, ensure httpx is installed
    pip install httpx
    ```

3.  **Run Tests**
    Ensure everything is working before you start:
    ```bash
    pytest
    ```

### Contribution Workflow

1.  **Create a Branch**: Use a descriptive name (e.g., `feature/custom-parser` or `fix/syslog-regex`).
2.  **Make Changes**: Write clean, documented code.
3.  **Add Tests**: New features must include unit tests. Fixes must include regression tests.
    - Run `pytest` to ensure all 60+ tests pass.
4.  **Linting**: Ensure your code follows Python best practices (PEP 8).
5.  **Submit PR**: Open a Pull Request against the `main` branch.

### Code Style Guide

- **Type Hints**: Use type hints for all function arguments and return values.
- **Docstrings**: Include clear docstrings for all modules, classes, and methods.
- **Dataclasses**: Use `@dataclass` for data structures.
- **Modularity**: Keep parsers in `parsers.py`, analytics in `analyzer.py`, etc.

### Reporting Issues

Found a bug? Open an issue with:
1.  Command run
2.  Log sample (anonymized)
3.  Expected vs actual output
4.  Error traceback (if any)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- [Click](https://click.palletsprojects.com/) for CLI framework
