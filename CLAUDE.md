# Log Analyzer Toolkit

CLI + web application for parsing, analyzing, and AI-powered troubleshooting of log files.

- **Version**: 1.0.2
- **Repo**: https://github.com/randallawhitlock/log-analyzer-toolkit
- **License**: MIT
- **Python**: 3.9+ (targets 3.10+)

## Architecture

### `log_analyzer/` — Python CLI Package
Entry point: `log_analyzer.cli:main` (Click + Rich). Core modules:
- `parsers.py` — all log format parsers (syslog, nginx, apache, JSON, etc.)
- `analyzer.py` — core analysis engine
- `triage.py` — AI-powered triage orchestration
- `report.py` — report generation
- `analytics.py` — analytics engine
- `charts.py` — chart generation
- `config.py` — YAML-based config (`~/.log-analyzer/config.yaml`), dataclass singleton via `get_config()`
- `ai_providers/` — provider abstraction (ABC in `base.py`, factory in `factory.py`)

### `backend/` — FastAPI REST API
Entry: `backend.main:app`. Routes under `/api/v1/` in `backend/api/routes.py`.
- DB: SQLAlchemy 2.0 (`DeclarativeBase`) + Alembic migrations. SQLite for dev, PostgreSQL for prod.
- Auth: API key via `X-API-Key` header (empty = dev mode, no auth required)
- Config: pydantic-settings `BaseSettings` in `backend/config.py`, singleton `settings`
- Rate limiting: slowapi (`60/minute` default)
- API docs: `/docs` (Swagger) and `/redoc`

### `frontend/` — Vue 3 SPA
Vite 7 build, Vue Router. Views: Home, Upload, Analyses, AnalysisDetail.
- Components in `src/components/`, views in `src/views/`
- HTTP client: axios. Markdown rendering: marked + DOMPurify.
- Tests: Vitest + jsdom + @vue/test-utils

### AI Providers
Factory pattern with lazy registration (avoids import errors when SDKs missing).
Auto-detection priority: **Anthropic Claude > Google Gemini > Ollama**.
All providers implement `AIProvider` ABC: `analyze()`, `is_available()`, `get_model()`.
Content sanitization (PII redaction, prompt injection defense) in `AIProvider.sanitize_log_content()`.

## Development Commands

| Command | Description |
|---------|-------------|
| `make install` | Create `.venv`, install `.[dev]`, set up pre-commit hooks |
| `make test` | `pytest tests/ backend/tests/` with coverage |
| `make lint` | `ruff check .` |
| `make format` | `ruff format .` |
| `make dev` | Run `run_dev.sh` (backend :8000 + frontend :5173) |
| `make run` | `docker compose up --build` (dev) |
| `make prod` | `docker compose -f docker-compose.prod.yml up --build -d` |
| `make clean` | Remove `.venv`, caches, build artifacts |
| `make release v=X.Y.Z` | Run `scripts/release.sh` |

Manual commands:
- Backend: `uvicorn backend.main:app --reload --port 8000`
- Frontend: `cd frontend && npm run dev`
- Frontend tests: `cd frontend && npm run test`

## Coding Standards

### Python (ruff)
- **Line length**: 120
- **Target**: Python 3.9
- **Rules**: `E` `F` `W` `I` (isort) `UP` (pyupgrade) `B` (bugbear) `SIM` (simplify)
- **Ignored**: `E501` (formatter handles line length), `B008` (FastAPI `Depends()`), `SIM108` (ternary readability)
- **isort first-party**: `log_analyzer`, `backend`
- **Excluded**: `venv`, `.venv`, `__pycache__`, `migrations`, `*.egg-info`

### Python (mypy)
- Target Python 3.10, **permissive** (`disallow_untyped_defs = false`)
- `check_untyped_defs = true` — checks bodies of untyped functions
- Ignores missing imports for: `rich`, `click`, `anthropic`, `google.generativeai`, `httpx`

### Frontend (ESLint)
- ESLint v10 with `eslint-plugin-vue`

### Pre-commit Hooks
- `trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`
- `ruff --fix`, `ruff-format`

## Git Workflow

Follow **`~/.gemini/workflows/git-commit.md`** for ALL commits.

- **Never** commit directly to `main` or `dev`
- Branch from `dev` using prefixes: `feat/`, `fix/`, `chore/`, `test/`, `refactor/`, `docs/`
- Commit format: **Conventional Commits** — `<type>(<scope>): <description>`
- Merges: always `--no-ff`
- Version bump after merging to `dev`, tag after merging to `main`

## Version Bump Checklist

All four files must be updated in sync:

1. **`pyproject.toml`** — `version = "X.Y.Z"` (line 7)
2. **`backend/config.py`** — `app_version: str = "X.Y.Z"` (line 22)
3. **`frontend/package.json`** — `"version": "X.Y.Z"` (line 3)
4. **`frontend/src/App.vue`** — footer text `Log Analyzer Toolkit vX.Y.Z`

Commit: `chore: bump version to X.Y.Z`
SemVer: PATCH for fixes, MINOR for features, MAJOR for breaking changes.

## Key Patterns & Gotchas

### B008 Ignore — Do Not "Fix"
Ruff rule `B008` is intentionally ignored. FastAPI uses `Depends()` calls in function signatures:
```python
def endpoint(db: Session = Depends(get_db)):  # This is correct
```

### backend/main.py Import Order — Intentional
`dotenv.load_dotenv()` MUST run before all other imports. All subsequent imports use `# noqa: E402`. **Do not rearrange or remove these comments.**

### Pydantic v2 Patterns
- ORM serialization: `model_config = ConfigDict(from_attributes=True)`
- Separate `Create`, `Response`, and `Request` schemas in `backend/api/schemas.py`

### AI Provider Extension
To add a new provider:
1. Create class extending `AIProvider` ABC from `log_analyzer/ai_providers/base.py`
2. Implement `analyze()`, `is_available()`, `get_model()`
3. Register in `factory.py` using lazy import (import inside function, not at module level)

### Settings — Two Systems
- **CLI**: `log_analyzer/config.py` — YAML-based `dataclass`, lazy singleton via `get_config()`
- **Backend**: `backend/config.py` — pydantic-settings `BaseSettings` with `.env`, singleton `settings`
- **Constants**: `backend/constants.py` derives values from `settings` for module-level access

### Database Conventions
- SQLAlchemy 2.0 `DeclarativeBase` (not legacy `declarative_base()`)
- UUID primary keys: `lambda: str(uuid.uuid4())`
- Timezone-aware datetimes: `datetime.now(timezone.utc)`
- Cascade deletes from Analysis to Triage
- FastAPI DB sessions via `Depends(get_db)`

### Test Patterns
- **CLI/core**: `tests/test_*.py` (27 files) with `conftest.py` fixtures
- **Backend API**: `backend/tests/test_*.py` — `TestClient`, temp SQLite DB, `app.dependency_overrides`
- **Frontend**: `frontend/src/*/__tests__/*.spec.js` — Vitest + `@vue/test-utils` + jsdom

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./log_analyzer.db` |
| `LOG_ANALYZER_API_KEY` | API auth (empty = dev mode) | `""` |
| `ANTHROPIC_API_KEY` | Claude AI triage | — |
| `GOOGLE_API_KEY` | Gemini AI triage | — |
| `OLLAMA_HOST` | Local Ollama endpoint | — |
| `VITE_API_URL` | Frontend API endpoint | `http://localhost:8000` |

See `.env.example` for full list including PostgreSQL, Redis, MinIO, RabbitMQ, and Elasticsearch config.

## Agent Mapping

| Agent | Use For |
|-------|---------|
| **Archon** | Architecture decisions, cross-cutting concerns |
| **Forge** | Python: CLI (`log_analyzer/`), backend, parsers, AI providers |
| **Prism** | Frontend: Vue components, views, Vite config, Vue Router |
| **Conduit** | API design: endpoints, schemas, REST patterns |
| **Nexus** | Database: SQLAlchemy models, Alembic migrations, queries |
| **Aegis** | Testing: pytest fixtures, coverage, Vitest specs |
| **Atlas** | Docker, CI/CD, deployment |
| **Sentinel** | Auth: API key handling, rate limiting, PII sanitization |
| **Pixel** | UI/UX: CSS custom properties, responsive design |
| **Scribe** | Documentation: README, docstrings, API docs |

*Oxide (Rust/C/C++) is not applicable to this project.*

## CI/CD Pipeline

Triggers on push/PR to `main` or `dev`. All jobs must pass before merge.

| Job | What it checks |
|-----|----------------|
| `backend-lint` | `ruff check .` on Python 3.10 |
| `backend-test` | `pytest tests/ backend/tests/` on Python 3.10 + 3.11 |
| `frontend-ci` | `npm run lint`, `npm run test`, `npm run build` on Node 22 |
