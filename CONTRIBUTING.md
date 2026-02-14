# Contributing to Log Analyzer Toolkit

Thank you for your interest in contributing! This guide will help you set up your development environment and submit high-quality pull requests.

## 🚀 Quick Start

1.  **Fork and Clone** the repository.
2.  **Install Dependencies**:
    ```bash
    make install
    ```
    This creates a virtual environment, installs dependencies, and sets up pre-commit hooks.

3.  **Activate Virtual Environment**:
    ```bash
    source venv/bin/activate
    ```

## 🛠 Development Workflow

We use `make` to standardize common tasks.

| Command | Description |
| :--- | :--- |
| `make test` | Run the full test suite with coverage reporting. |
| `make lint` | Run code quality checks (Ruff). |
| `make format` | Auto-format code using Ruff. |
| `make run` | Launch the full stack using Docker Compose. |
| `make clean` | Remove build artifacts and cache files. |

## ✅ Code Quality Standards

We enforce strict quality standards to maintain a robust codebase.

1.  **Test Coverage**: All new features must include tests. We enforce **90% coverage**.
2.  **Linting**: We use `ruff` for linting and formatting. Run `make lint` before committing.
3.  **Pre-commit Hooks**: Git hooks will automatically run linter checks on commit.

## 📦 Submitting a Pull Request

1.  Create a branch for your feature: `git checkout -b feat/your-feature-name`.
2.  Write code and add tests.
3.  Ensure all tests pass: `make test`.
4.  Commit your changes using [Conventional Commits](https://www.conventionalcommits.org/).
    - `feat(parser): add support for nginx logs`
    - `fix(core): resolve memory leak in analyzer`
5.  Push to your fork and open a Pull Request.

## 🐳 Docker Support

To test the application in a containerized environment (matching production):

```bash
make run
```

The frontend will be available at `http://localhost:8080` and the API at `http://localhost:8000`.

## Release Process

1.  Update `pyproject.toml` version.
2.  Create a pull request from `chore/release-vX.Y.Z`.
3.  Once merged, create a GitHub release and tag `vX.Y.Z`.
