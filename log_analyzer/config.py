"""
Configuration management for Log Analyzer Toolkit.

This module provides centralized configuration for AI providers,
supporting both environment variables and configuration files.

Configuration Priority (highest to lowest):
1. Explicit parameters passed to functions
2. Environment variables
3. Configuration file (~/.log-analyzer/config.yaml)
4. Default values

Security Notes:
    - Config file permissions are checked on load
    - API keys are never logged or displayed in full
    - Sensitive values are masked in string representations
"""

import logging
import os
import stat
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any

# Try to import yaml, but make it optional
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


logger = logging.getLogger(__name__)


# Default configuration directory and file
DEFAULT_CONFIG_DIR = Path.home() / ".log-analyzer"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"


# Environment variable names
ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "ollama_host": "OLLAMA_HOST",
    "default_provider": "LOG_ANALYZER_PROVIDER",
    "max_workers": "LOG_ANALYZER_MAX_WORKERS",
}


# Default model configurations (latest as of Feb 2026)
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5-20250929",
    "gemini": "gemini-2.5-flash",
    "ollama": "llama3",
}


__all__ = [
    "ProviderConfig",
    "Config",
    "mask_api_key",
    "check_config_permissions",
    "load_config",
    "save_config",
    "get_config",
    "reset_config",
    "get_provider_status",
]


@dataclass
class ProviderConfig:
    """Configuration for a single AI provider."""
    
    enabled: bool = True
    model: Optional[str] = None
    api_key: Optional[str] = None  # Only for runtime use, never persisted
    extra: dict = field(default_factory=dict)
    
    def __repr__(self) -> str:
        """Mask API key in string representation."""
        key_display = "***" if self.api_key else None
        return (
            f"ProviderConfig(enabled={self.enabled}, "
            f"model={self.model!r}, api_key={key_display})"
        )


@dataclass
class Config:
    """
    Main configuration class for Log Analyzer Toolkit.

    Attributes:
        default_provider: Preferred AI provider (anthropic, gemini, ollama)
        providers: Provider-specific configurations
        config_file: Path to the configuration file (if loaded)
        max_workers: Maximum number of worker threads for parallel processing
    """

    default_provider: Optional[str] = None
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    config_file: Optional[Path] = None
    max_workers: Optional[int] = None  # None means use CPU count
    
    def __post_init__(self):
        """Initialize default provider configs if not provided."""
        for provider in ["anthropic", "gemini", "ollama"]:
            if provider not in self.providers:
                self.providers[provider] = ProviderConfig(
                    model=DEFAULT_MODELS.get(provider)
                )
    
    def get_provider_config(self, provider: str) -> ProviderConfig:
        """
        Get configuration for a specific provider.
        
        Args:
            provider: Provider name (anthropic, gemini, ollama)
            
        Returns:
            ProviderConfig for the provider
        """
        if provider not in self.providers:
            self.providers[provider] = ProviderConfig(
                model=DEFAULT_MODELS.get(provider)
            )
        return self.providers[provider]
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a provider, checking config then environment.
        
        Priority:
        1. ProviderConfig.api_key (if set at runtime)
        2. Environment variable
        
        Args:
            provider: Provider name
            
        Returns:
            API key if found, None otherwise
        """
        # Check runtime config first
        config = self.get_provider_config(provider)
        if config.api_key:
            return config.api_key
        
        # Check environment variable
        env_var = ENV_VARS.get(provider)
        if env_var:
            return os.environ.get(env_var)
        
        return None
    
    def get_model(self, provider: str) -> str:
        """
        Get model for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Model identifier
        """
        config = self.get_provider_config(provider)
        return config.model or DEFAULT_MODELS.get(provider, "")
    
    def to_dict(self) -> dict:
        """
        Convert config to dictionary for YAML serialization.

        Note: API keys are NOT included in the output.
        """
        result = {
            "default_provider": self.default_provider,
            "providers": {
                name: {
                    "enabled": cfg.enabled,
                    "model": cfg.model,
                    **cfg.extra,
                }
                for name, cfg in self.providers.items()
            },
        }
        if self.max_workers is not None:
            result["max_workers"] = self.max_workers
        return result


def mask_api_key(key: Optional[str]) -> str:
    """
    Mask an API key for safe display.
    
    Args:
        key: API key to mask
        
    Returns:
        Masked string showing only first 4 and last 4 characters
    """
    if not key:
        return "(not set)"
    if len(key) <= 12:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def check_config_permissions(path: Path) -> bool:
    """
    Check if config file has secure permissions.
    
    Warnings are issued if the file is readable by others.
    
    Args:
        path: Path to config file
        
    Returns:
        True if permissions are secure, False otherwise
    """
    if not path.exists():
        return True
    
    try:
        mode = path.stat().st_mode
        
        # Check if group or others can read
        if mode & (stat.S_IRGRP | stat.S_IROTH):
            warnings.warn(
                f"Config file {path} is readable by others. "
                "Consider running: chmod 600 {path}",
                UserWarning,
            )
            return False
        
        return True
    except OSError:
        return True  # Can't check, assume OK


def load_config(path: Optional[Path] = None) -> Config:
    """
    Load configuration from file and environment.

    Args:
        path: Path to config file. Defaults to ~/.log-analyzer/config.yaml

    Returns:
        Loaded Config object
    """
    logger.debug(f"Loading configuration from {path or DEFAULT_CONFIG_FILE}")
    config = Config()
    config_path = path or DEFAULT_CONFIG_FILE

    # Load from file if it exists and YAML is available
    if config_path.exists() and YAML_AVAILABLE:
        logger.debug(f"Config file exists: {config_path}")
        check_config_permissions(config_path)

        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}

            config.config_file = config_path
            config.default_provider = data.get("default_provider")
            config.max_workers = data.get("max_workers")

            # Load provider configs
            providers_data = data.get("providers", {})
            for name, prov_data in providers_data.items():
                if isinstance(prov_data, dict):
                    config.providers[name] = ProviderConfig(
                        enabled=prov_data.get("enabled", True),
                        model=prov_data.get("model"),
                        extra={
                            k: v for k, v in prov_data.items()
                            if k not in ("enabled", "model", "api_key")
                        },
                    )

            logger.info(f"Loaded configuration from {config_path}: "
                       f"default_provider={config.default_provider}, "
                       f"providers={list(providers_data.keys())}")
        except (OSError, IOError) as e:
            logger.error(f"Failed to read config file {config_path}: {e}")
            warnings.warn(f"Error loading config from {config_path}: {e}")
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in config file {config_path}: {e}")
            warnings.warn(f"Invalid YAML in {config_path}: {e}")
        except Exception as e:
            logger.error(f"Unexpected error loading config from {config_path}: {e}", exc_info=True)
            warnings.warn(f"Error loading config from {config_path}: {e}")
    elif config_path.exists() and not YAML_AVAILABLE:
        logger.warning(f"Config file exists but PyYAML not installed: {config_path}")
    else:
        logger.debug(f"No config file found at {config_path}, using defaults")

    # Override default_provider from environment if set
    env_provider = os.environ.get(ENV_VARS["default_provider"])
    if env_provider:
        logger.debug(f"Overriding default_provider from environment: {env_provider}")
        config.default_provider = env_provider

    # Override max_workers from environment if set
    env_max_workers = os.environ.get(ENV_VARS["max_workers"])
    if env_max_workers:
        try:
            config.max_workers = int(env_max_workers)
            logger.debug(f"Overriding max_workers from environment: {config.max_workers}")
        except ValueError:
            logger.warning(f"Invalid max_workers value in environment: {env_max_workers}")

    return config


def save_config(config: Config, path: Optional[Path] = None) -> Path:
    """
    Save configuration to file.

    Note: API keys are NOT saved to the file.

    Args:
        config: Config object to save
        path: Path to save to. Defaults to ~/.log-analyzer/config.yaml

    Returns:
        Path where config was saved

    Raises:
        ImportError: If PyYAML is not installed
    """
    if not YAML_AVAILABLE:
        logger.error("Attempted to save config but PyYAML not installed")
        raise ImportError(
            "PyYAML is required to save config. Run: pip install pyyaml"
        )

    config_path = path or DEFAULT_CONFIG_FILE
    logger.info(f"Saving configuration to {config_path}")

    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write config
    with open(config_path, "w") as f:
        yaml.safe_dump(config.to_dict(), f, default_flow_style=False)

    logger.debug(f"Configuration written to {config_path}")

    # Set secure permissions (owner read/write only)
    try:
        config_path.chmod(0o600)
        logger.debug(f"Set secure permissions (600) on {config_path}")
    except OSError as e:
        logger.warning(f"Could not set secure permissions on {config_path}: {e}")
        # Ignore permission errors (e.g., on Windows)

    return config_path


def get_config() -> Config:
    """
    Get the current configuration.

    This is the main entry point for getting configuration.
    Loads from file and environment on first call.

    Returns:
        Current Config object
    """
    global _config
    if _config is None:
        logger.debug("First call to get_config(), loading configuration")
        _config = load_config()
    return _config


def reset_config():
    """Reset the global config (useful for testing)."""
    global _config
    _config = None


# Global config instance (lazy loaded)
_config: Optional[Config] = None


def get_provider_status() -> dict[str, dict]:
    """
    Get status of all known providers.

    Returns:
        Dictionary with provider status information
    """
    logger.debug("Getting status of all providers")
    config = get_config()
    status = {}

    for provider in ["anthropic", "gemini", "ollama"]:
        provider_config = config.get_provider_config(provider)
        api_key = config.get_api_key(provider)

        status[provider] = {
            "enabled": provider_config.enabled,
            "model": config.get_model(provider),
            "configured": bool(api_key) if provider != "ollama" else True,
            "api_key_display": mask_api_key(api_key) if provider != "ollama" else "N/A",
        }

        # For Ollama, check if server is reachable
        if provider == "ollama":
            try:
                from .ai_providers.ollama_provider import OllamaProvider
                ollama = OllamaProvider()
                status[provider]["server_available"] = ollama.is_available()
                logger.debug(f"Ollama server availability: {status[provider]['server_available']}")
            except ImportError as e:
                logger.debug(f"Ollama provider not available (import error): {e}")
                status[provider]["server_available"] = False
            except Exception as e:
                logger.debug(f"Error checking Ollama availability: {e}")
                status[provider]["server_available"] = False

    logger.debug(f"Provider status: {[(k, v['configured']) for k, v in status.items()]}")
    return status
