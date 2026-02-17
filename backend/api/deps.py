import logging
import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from backend.constants import LOG_ANALYZER_API_KEY

logger = logging.getLogger(__name__)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validate API Key from X-API-Key header.

    If LOG_ANALYZER_API_KEY is not set in env, allow access (development mode).
    If set, require valid key.
    """
    expected_key = os.getenv(LOG_ANALYZER_API_KEY)

    if not expected_key:
        # No key configured = development mode, allow access
        return None

    if api_key_header and api_key_header == expected_key:
        return api_key_header

    logger.warning("Invalid API Key attempt")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials",
    )
