.PHONY: install test lint format run clean docker-build help

PYTHON := python3
VENV := venv
BIN := $(VENV)/bin

help:
	@echo "Log Analyzer Toolkit - Developer Commands"
	@echo "========================================="
	@echo "make install      - Create venv and install dependencies"
	@echo "make test         - Run tests with coverage"
	@echo "make lint         - Run linting (ruff)"
	@echo "make format       - Run formatting (ruff)"
	@echo "make run          - Run application via Docker"
	@echo "make clean        - Remove build artifacts"

install:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install -e ".[dev]"
	$(BIN)/pip install pre-commit
	$(BIN)/pre-commit install

test:
	$(BIN)/pytest

lint:
	$(BIN)/ruff check .

format:
	$(BIN)/ruff format .

run:
	docker-compose up --build

clean:
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
