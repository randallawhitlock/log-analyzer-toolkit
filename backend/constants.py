"""
Shared constants for Backend API.

This module defines configuration constants used throughout the backend
to avoid magic numbers and ensure consistency.
"""

# File upload limits
MAX_UPLOAD_SIZE_BYTES = 100 * 1024 * 1024  # 100MB maximum upload size
MAX_UPLOAD_SIZE_MB = 100  # For display purposes

# Analysis defaults
DEFAULT_MAX_ERRORS = 100  # Default maximum errors to collect during analysis
MAX_ERRORS_LIMIT = 1000  # Hard limit for max_errors parameter
MIN_ERRORS_LIMIT = 1  # Minimum value for max_errors parameter

# Triage defaults
DEFAULT_TRIAGE_MAX_ERRORS = 50  # Default maximum errors to analyze during triage

# Pagination defaults
DEFAULT_PAGE_SIZE = 20  # Default number of results per page
MAX_PAGE_SIZE = 100  # Maximum results per page
MIN_PAGE_SIZE = 1  # Minimum results per page

# Upload directory
UPLOAD_DIRECTORY = "./uploads"  # Directory for uploaded log files
