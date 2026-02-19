"""
Shared constants for Backend API.

Values are sourced from the unified Settings object so they can be
overridden via environment variables or .env file, while keeping
backward-compatible module-level names.
"""

from backend.config import settings

# File upload limits
MAX_UPLOAD_SIZE_BYTES = settings.max_upload_size_bytes
MAX_UPLOAD_SIZE_MB = settings.max_upload_size_mb

# Analysis defaults
DEFAULT_MAX_ERRORS = settings.default_max_errors
MAX_ERRORS_LIMIT = settings.max_errors_limit
MIN_ERRORS_LIMIT = settings.min_errors_limit

# Triage defaults
DEFAULT_TRIAGE_MAX_ERRORS = settings.default_triage_max_errors

# Pagination defaults
DEFAULT_PAGE_SIZE = settings.default_page_size
MAX_PAGE_SIZE = settings.max_page_size
MIN_PAGE_SIZE = settings.min_page_size

# Upload directory
UPLOAD_DIRECTORY = settings.upload_directory

# Authentication
LOG_ANALYZER_API_KEY = "LOG_ANALYZER_API_KEY"  # Env var name for API key
