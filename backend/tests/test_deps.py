"""
Tests for backend/api/deps.py - dependency injection functions.

Covers:
- get_analyzer_service returns AnalyzerService instance
- get_api_key in dev mode (no env var set)
- get_api_key with valid key
- get_api_key with invalid key (403)
- get_api_key with missing header when key is configured (403)
"""

import pytest
from fastapi import HTTPException

from backend.api.deps import get_analyzer_service, get_api_key
from backend.constants import LOG_ANALYZER_API_KEY
from backend.services.analyzer_service import AnalyzerService


class TestGetAnalyzerService:
    """Tests for the get_analyzer_service dependency."""

    def test_returns_analyzer_service_instance(self):
        """get_analyzer_service should return an AnalyzerService instance."""
        service = get_analyzer_service()
        assert isinstance(service, AnalyzerService)

    def test_returns_new_instance_each_call(self):
        """Each call should return a fresh instance (not a singleton)."""
        service1 = get_analyzer_service()
        service2 = get_analyzer_service()
        assert service1 is not service2


class TestGetApiKeyDevMode:
    """Tests for get_api_key when no API key is configured (dev mode)."""

    @pytest.mark.asyncio
    async def test_no_env_key_returns_none(self, monkeypatch):
        """When LOG_ANALYZER_API_KEY env var is not set, return None (dev mode)."""
        monkeypatch.delenv(LOG_ANALYZER_API_KEY, raising=False)
        result = await get_api_key(api_key_header=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_env_key_with_header_still_returns_none(self, monkeypatch):
        """Even with a header provided, if no env key is set, return None."""
        monkeypatch.delenv(LOG_ANALYZER_API_KEY, raising=False)
        result = await get_api_key(api_key_header="some-random-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_env_key_returns_none(self, monkeypatch):
        """An empty string env var is treated as unset (dev mode)."""
        monkeypatch.setenv(LOG_ANALYZER_API_KEY, "")
        result = await get_api_key(api_key_header=None)
        assert result is None


class TestGetApiKeyAuthenticated:
    """Tests for get_api_key when an API key is configured."""

    @pytest.mark.asyncio
    async def test_valid_key_returns_key(self, monkeypatch):
        """When header matches the configured key, return the key."""
        monkeypatch.setenv(LOG_ANALYZER_API_KEY, "test-secret-key-123")
        result = await get_api_key(api_key_header="test-secret-key-123")
        assert result == "test-secret-key-123"

    @pytest.mark.asyncio
    async def test_invalid_key_raises_403(self, monkeypatch):
        """When header does not match the configured key, raise 403."""
        monkeypatch.setenv(LOG_ANALYZER_API_KEY, "correct-key")
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(api_key_header="wrong-key")
        assert exc_info.value.status_code == 403
        assert "credentials" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_missing_header_raises_403(self, monkeypatch):
        """When key is configured but no header is provided, raise 403."""
        monkeypatch.setenv(LOG_ANALYZER_API_KEY, "configured-key")
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(api_key_header=None)
        assert exc_info.value.status_code == 403
        assert "credentials" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_empty_header_raises_403(self, monkeypatch):
        """When key is configured but header is empty string, raise 403."""
        monkeypatch.setenv(LOG_ANALYZER_API_KEY, "configured-key")
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(api_key_header="")
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_exception_detail_message(self, monkeypatch):
        """Verify the exact error detail message on 403."""
        monkeypatch.setenv(LOG_ANALYZER_API_KEY, "my-key")
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key(api_key_header="bad-key")
        assert exc_info.value.detail == "Could not validate credentials"
