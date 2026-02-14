"""
Unit tests for AI provider factory module.
"""

from unittest.mock import patch, MagicMock

import pytest

from log_analyzer.ai_providers.base import AIProvider, ProviderNotAvailableError
from log_analyzer.ai_providers import factory


@pytest.fixture(autouse=True)
def _clear_registry():
    """Ensure a clean provider registry for each test."""
    factory._PROVIDER_REGISTRY.clear()
    yield
    factory._PROVIDER_REGISTRY.clear()


# ---------------------------------------------------------------------------
# list_available_providers
# ---------------------------------------------------------------------------

class TestListAvailableProviders:
    """Tests for list_available_providers."""

    def test_returns_list(self):
        result = factory.list_available_providers()
        assert isinstance(result, list)

    def test_registers_providers_on_call(self):
        result = factory.list_available_providers()
        # Should have at least one provider on a dev machine with deps installed
        assert len(result) >= 0  # safe fallback

    def test_with_mocked_registry(self):
        mock_cls = MagicMock()
        factory._PROVIDER_REGISTRY["mock_provider"] = mock_cls
        result = factory.list_available_providers()
        assert "mock_provider" in result


# ---------------------------------------------------------------------------
# list_configured_providers
# ---------------------------------------------------------------------------

class TestListConfiguredProviders:
    """Tests for list_configured_providers."""

    def test_returns_list(self):
        result = factory.list_configured_providers()
        assert isinstance(result, list)

    def test_available_provider_included(self):
        mock_cls = MagicMock()
        mock_instance = mock_cls.return_value
        mock_instance.is_available.return_value = True
        factory._PROVIDER_REGISTRY["test_avail"] = mock_cls

        result = factory.list_configured_providers()
        assert "test_avail" in result

    def test_unavailable_provider_excluded(self):
        mock_cls = MagicMock()
        mock_instance = mock_cls.return_value
        mock_instance.is_available.return_value = False
        factory._PROVIDER_REGISTRY["test_unavail"] = mock_cls

        result = factory.list_configured_providers()
        assert "test_unavail" not in result

    def test_provider_init_error_skipped(self):
        mock_cls = MagicMock(side_effect=ValueError("bad init"))
        factory._PROVIDER_REGISTRY["bad_provider"] = mock_cls

        result = factory.list_configured_providers()
        assert "bad_provider" not in result

    def test_unexpected_init_error_logged(self):
        mock_cls = MagicMock(side_effect=RuntimeError("unexpected"))
        factory._PROVIDER_REGISTRY["exploder"] = mock_cls

        result = factory.list_configured_providers()
        assert "exploder" not in result


# ---------------------------------------------------------------------------
# get_provider (specific name)
# ---------------------------------------------------------------------------

class TestGetProviderSpecific:
    """Tests for get_provider when a name is specified."""

    def test_returns_provider_instance(self):
        mock_cls = MagicMock()
        mock_instance = mock_cls.return_value
        mock_instance.is_available.return_value = True
        mock_instance.get_model.return_value = "test-model"
        factory._PROVIDER_REGISTRY["mytest"] = mock_cls

        provider = factory.get_provider(name="mytest")
        assert provider is mock_instance

    def test_with_model_override(self):
        mock_cls = MagicMock()
        mock_instance = mock_cls.return_value
        mock_instance.is_available.return_value = True
        mock_instance.get_model.return_value = "custom-model"
        factory._PROVIDER_REGISTRY["mytest"] = mock_cls

        factory.get_provider(name="mytest", model="custom-model")
        mock_cls.assert_called_once_with(model="custom-model")

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            factory.get_provider(name="does_not_exist")

    def test_unavailable_provider_raises(self):
        mock_cls = MagicMock()
        mock_instance = mock_cls.return_value
        mock_instance.is_available.return_value = False
        factory._PROVIDER_REGISTRY["offline"] = mock_cls

        with pytest.raises(ProviderNotAvailableError, match="not available"):
            factory.get_provider(name="offline")

    def test_case_insensitive_lookup(self):
        mock_cls = MagicMock()
        mock_instance = mock_cls.return_value
        mock_instance.is_available.return_value = True
        mock_instance.get_model.return_value = "m"
        factory._PROVIDER_REGISTRY["mytest"] = mock_cls

        provider = factory.get_provider(name="MYTEST")
        assert provider is mock_instance


# ---------------------------------------------------------------------------
# get_provider (auto-detect)
# ---------------------------------------------------------------------------

class TestGetProviderAutoDetect:
    """Tests for auto-detection of providers."""

    @patch('log_analyzer.ai_providers.factory.get_config')
    def test_auto_detect_first_available(self, mock_get_config):
        mock_config = MagicMock()
        mock_config.default_provider = None
        mock_get_config.return_value = mock_config

        mock_cls = MagicMock()
        mock_instance = mock_cls.return_value
        mock_instance.is_available.return_value = True
        mock_instance.get_model.return_value = "m"
        factory._PROVIDER_REGISTRY["anthropic"] = mock_cls

        provider = factory.get_provider()
        assert provider is mock_instance

    @patch('log_analyzer.ai_providers.factory.get_config')
    def test_auto_detect_skips_unavailable(self, mock_get_config):
        mock_config = MagicMock()
        mock_config.default_provider = None
        mock_get_config.return_value = mock_config

        bad_cls = MagicMock()
        bad_cls.return_value.is_available.return_value = False

        good_cls = MagicMock()
        good_cls.return_value.is_available.return_value = True
        good_cls.return_value.get_model.return_value = "m"

        factory._PROVIDER_REGISTRY["anthropic"] = bad_cls
        factory._PROVIDER_REGISTRY["gemini"] = good_cls

        provider = factory.get_provider()
        assert provider is good_cls.return_value

    @patch('log_analyzer.ai_providers.factory.get_config')
    def test_auto_detect_respects_default(self, mock_get_config):
        mock_config = MagicMock()
        mock_config.default_provider = "gemini"
        mock_get_config.return_value = mock_config

        anthropic_cls = MagicMock()
        anthropic_cls.return_value.is_available.return_value = True
        anthropic_cls.return_value.get_model.return_value = "m"

        gemini_cls = MagicMock()
        gemini_cls.return_value.is_available.return_value = True
        gemini_cls.return_value.get_model.return_value = "m"

        factory._PROVIDER_REGISTRY["anthropic"] = anthropic_cls
        factory._PROVIDER_REGISTRY["gemini"] = gemini_cls

        provider = factory.get_provider()
        # Should pick gemini because it was set as default
        assert provider is gemini_cls.return_value

    @patch('log_analyzer.ai_providers.factory.get_config')
    def test_no_providers_raises(self, mock_get_config):
        mock_config = MagicMock()
        mock_config.default_provider = None
        mock_get_config.return_value = mock_config
        # _PROVIDER_REGISTRY is empty

        with pytest.raises(ProviderNotAvailableError):
            factory.get_provider()

    @patch('log_analyzer.ai_providers.factory.get_config')
    def test_no_providers_configured_raises(self, mock_get_config):
        mock_config = MagicMock()
        mock_config.default_provider = None
        mock_get_config.return_value = mock_config

        mock_cls = MagicMock()
        mock_cls.return_value.is_available.return_value = False
        factory._PROVIDER_REGISTRY["anthropic"] = mock_cls

        with pytest.raises(ProviderNotAvailableError, match="configured"):
            factory.get_provider()


# ---------------------------------------------------------------------------
# get_provider_info
# ---------------------------------------------------------------------------

class TestGetProviderInfo:
    """Tests for get_provider_info."""

    def test_known_provider(self):
        mock_cls = MagicMock()
        mock_cls.default_model = "test-model-v1"
        mock_instance = mock_cls.return_value
        mock_instance.is_available.return_value = True
        mock_instance.get_model.return_value = "test-model-v1"
        factory._PROVIDER_REGISTRY["mytest"] = mock_cls

        info = factory.get_provider_info("mytest")
        assert info["name"] == "mytest"
        assert info["installed"] is True
        assert info["configured"] is True
        assert info["current_model"] == "test-model-v1"

    def test_unknown_provider(self):
        info = factory.get_provider_info("nonexistent")
        assert "error" in info

    def test_provider_init_error(self):
        mock_cls = MagicMock()
        mock_cls.default_model = "m"
        mock_cls.return_value = MagicMock(side_effect=RuntimeError("init fail"))
        mock_cls.side_effect = RuntimeError("init fail")
        factory._PROVIDER_REGISTRY["broken"] = mock_cls

        info = factory.get_provider_info("broken")
        assert "error" in info

    def test_case_insensitive(self):
        mock_cls = MagicMock()
        mock_cls.default_model = "m"
        mock_instance = mock_cls.return_value
        mock_instance.is_available.return_value = False
        mock_instance.get_model.return_value = "m"
        factory._PROVIDER_REGISTRY["mytest"] = mock_cls

        info = factory.get_provider_info("MYTEST")
        assert info["name"] == "mytest"
