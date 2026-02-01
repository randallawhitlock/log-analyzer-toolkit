# ⚡️ Quickstart Guide

## 1. Install
```bash
git clone https://github.com/randallawhitlock/log-analyzer-toolkit.git
cd log-analyzer-toolkit
pip install -e .
```

## 2. Configure AI (One-time)
```bash
# For Anthropic (Best)
export ANTHROPIC_API_KEY="sk-ant-..."

# OR for Gemini (Fast)
export GOOGLE_API_KEY="AIza..."

# OR for Ollama (Free/Local)
ollama serve
```

## 3. Run Commands

**Analyze a Log (Stats)**
```bash
python -m log_analyzer analyze /var/log/app.log
```

**Diagnose Issues (AI)**
```bash
python -m log_analyzer triage /var/log/app.log
```

**View Config**
```bash
python -m log_analyzer configure --show
```
