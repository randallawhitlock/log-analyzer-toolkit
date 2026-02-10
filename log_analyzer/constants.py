"""
Shared constants for Log Analyzer Toolkit.

This module defines configuration constants used throughout the application
to avoid magic numbers and ensure consistency.
"""

# Display and formatting constants
MAX_MESSAGE_LENGTH = 100  # Maximum length for displaying log messages in CLI
MAX_ERROR_MESSAGE_LENGTH = 80  # Maximum length for error messages in reports
MAX_DISPLAY_ENTRIES = 5  # Default number of top entries to display (errors, sources, etc.)

# File processing limits
DEFAULT_MAX_LINES = 200_000  # Maximum lines to read with read_all() to prevent memory issues
DEFAULT_SAMPLE_SIZE = 100  # Number of lines to sample for format detection
DEFAULT_MAX_ERRORS = 50  # Default maximum errors/warnings to collect during analysis

# Memory optimization limits
MAX_COUNTER_SIZE = 10_000  # Maximum unique items in Counter before pruning (prevents unbounded memory growth)
COUNTER_PRUNE_TO = 5_000  # When pruning Counter, keep only this many most common items

# HTTP status code severity mappings
HTTP_STATUS_ERROR_THRESHOLD = 500  # Status codes >= 500 are considered errors
HTTP_STATUS_WARNING_THRESHOLD = 400  # Status codes >= 400 are considered warnings
HTTP_STATUS_REDIRECT_THRESHOLD = 300  # Status codes >= 300 are considered redirects

# Severity levels (ordered by importance)
SEVERITY_LEVELS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]

# Log level colors for display
LEVEL_COLORS = {
    "CRITICAL": "bold red",
    "ERROR": "red",
    "WARNING": "yellow",
    "INFO": "green",
    "DEBUG": "dim",
}

# Timing and performance
DEFAULT_AI_TIMEOUT = 120.0  # Default timeout for AI provider requests (seconds)
DEFAULT_OLLAMA_TIMEOUT = 300.0  # Ollama may need longer for local inference

# Token estimation (rough approximation)
CHARS_PER_TOKEN = 4  # Approximate characters per token for prompt size estimation
