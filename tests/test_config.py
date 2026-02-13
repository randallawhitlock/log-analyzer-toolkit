"""
Unit tests for configuration module.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from log_analyzer.config import (
    DEFAULT_MODELS,
    Config,
    ProviderConfig,
    check_config_permissions,
    get_config,
    get_provider_status,
    load_config,
    mask_api_key,
    reset_config,
    save_config,
)


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ProviderConfig()

        assert config.enabled is True
        assert config.model is None
        assert config.api_key is None
        assert config.extra == {}

    def test_repr_masks_api_key(self):
        """Test that repr masks API key."""
        config = ProviderConfig(api_key="secret-key-12345")

        repr_str = repr(config)

        assert "secret-key-12345" not in repr_str
        assert "***" in repr_str


class TestConfig:
    """Tests for Config dataclass."""

    def test_default_initialization(self):
        """Test that config initializes with default providers."""
        config = Config()

        assert "anthropic" in config.providers
        assert "gemini" in config.providers
        assert "ollama" in config.providers

    def test_get_provider_config(self):
        """Test getting provider configuration."""
        config = Config()

        anthropic_config = config.get_provider_config("anthropic")

        assert isinstance(anthropic_config, ProviderConfig)
        assert anthropic_config.model == DEFAULT_MODELS["anthropic"]

    def test_get_provider_config_creates_unknown(self):
        """Test that getting unknown provider creates default config."""
        config = Config()

        new_config = config.get_provider_config("new_provider")

        assert isinstance(new_config, ProviderConfig)
        assert "new_provider" in config.providers

    @patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-env-key'})
    def test_get_api_key_from_env(self):
        """Test getting API key from environment variable."""
        config = Config()

        key = config.get_api_key("anthropic")

        assert key == "test-env-key"

    def test_get_api_key_from_runtime(self):
        """Test runtime API key takes precedence."""
        config = Config()
        config.providers["anthropic"].api_key = "runtime-key"

        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-key'}):
            key = config.get_api_key("anthropic")

        assert key == "runtime-key"

    def test_get_model(self):
        """Test getting model for provider."""
        config = Config()

        model = config.get_model("anthropic")

        assert model == DEFAULT_MODELS["anthropic"]

    def test_to_dict_excludes_api_keys(self):
        """Test that to_dict does not include API keys."""
        config = Config()
        config.providers["anthropic"].api_key = "secret-key"

        result = config.to_dict()

        assert "api_key" not in str(result)
        assert "secret-key" not in str(result)


class TestMaskApiKey:
    """Tests for API key masking."""

    def test_mask_none(self):
        """Test masking None key."""
        assert mask_api_key(None) == "(not set)"

    def test_mask_empty(self):
        """Test masking empty key."""
        assert mask_api_key("") == "(not set)"

    def test_mask_short_key(self):
        """Test masking short key."""
        assert mask_api_key("abc") == "***"
        assert mask_api_key("123456789012") == "***"

    def test_mask_long_key(self):
        """Test masking long key shows first and last 4 chars."""
        result = mask_api_key("sk-1234567890abcdef")

        assert result == "sk-1...cdef"


class TestLoadSaveConfig:
    """Tests for loading and saving configuration."""

    def test_load_returns_config(self):
        """Test that load_config returns a Config object."""
        config = load_config(Path("/nonexistent/path.yaml"))

        assert isinstance(config, Config)

    @patch.dict('os.environ', {'LOG_ANALYZER_PROVIDER': 'ollama'})
    def test_load_respects_env_default_provider(self):
        """Test that environment variable sets default provider."""
        reset_config()

        config = load_config()

        assert config.default_provider == "ollama"

    def test_save_and_load_roundtrip(self):
        """Test saving and loading config."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            pytest.skip("pyyaml not installed")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create config
            config = Config(default_provider="gemini")
            config.providers["anthropic"].model = "claude-opus-4-5"

            # Save
            save_config(config, config_path)

            # Verify file exists
            assert config_path.exists()

            # Load
            loaded = load_config(config_path)

            assert loaded.default_provider == "gemini"
            assert loaded.providers["anthropic"].model == "claude-opus-4-5"

    def test_save_creates_directory(self):
        """Test that save creates parent directories."""
        try:
            import yaml  # noqa: F401
        except ImportError:
            pytest.skip("pyyaml not installed")

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "subdir" / "config.yaml"

            config = Config()
            save_config(config, config_path)

            assert config_path.exists()


class TestGetConfig:
    """Tests for global config management."""

    def test_get_config_returns_same_instance(self):
        """Test that get_config returns cached instance."""
        reset_config()

        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_reset_config_clears_cache(self):
        """Test that reset_config clears the cache."""
        config1 = get_config()
        reset_config()
        config2 = get_config()

        assert config1 is not config2


class TestCheckConfigPermissions:
    """Tests for permission checking."""

    def test_nonexistent_file_returns_true(self):
        """Test that nonexistent file is considered secure."""
        result = check_config_permissions(Path("/nonexistent/file.yaml"))

        assert result is True

    def test_secure_permissions(self):
        """Test file with secure permissions."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = Path(f.name)

        try:
            os.chmod(path, 0o600)  # Owner read/write only

            result = check_config_permissions(path)

            assert result is True
        finally:
            path.unlink()


class TestGetProviderStatus:
    """Tests for provider status reporting."""

    def test_returns_all_providers(self):
        """Test that status includes all providers."""
        reset_config()

        status = get_provider_status()

        assert "anthropic" in status
        assert "gemini" in status
        assert "ollama" in status

    def test_status_structure(self):
        """Test that status has expected structure."""
        reset_config()

        status = get_provider_status()

        for _name, info in status.items():
            assert "enabled" in info
            assert "model" in info
            assert "configured" in info
            assert "api_key_display" in info
