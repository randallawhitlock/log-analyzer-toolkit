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
DEFAULT_SAMPLE_SIZE = 100  # Number of lines to sample for format detection
DEFAULT_MAX_ERRORS = 50  # Default maximum errors/warnings to collect during analysis

# Memory optimization limits
MAX_COUNTER_SIZE = 10_000  # Maximum unique items in Counter before pruning (prevents unbounded memory growth)
COUNTER_PRUNE_TO = 5_000  # When pruning Counter, keep only this many most common items

# Log level colors for display
LEVEL_COLORS = {
    "CRITICAL": "bold red",
    "ERROR": "red",
    "WARNING": "yellow",
    "INFO": "green",
    "DEBUG": "dim",
}

# Token estimation (rough approximation)
CHARS_PER_TOKEN = 4  # Approximate characters per token for prompt size estimation

# Analytics configuration
DEFAULT_TIME_BUCKET_SIZE = "1h"  # Default time bucket size: '5min', '15min', '1h', '1day'
