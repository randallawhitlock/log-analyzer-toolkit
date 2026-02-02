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


# Default configuration directory and file
DEFAULT_CONFIG_DIR = Path.home() / ".log-analyzer"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.yaml"


# Environment variable names
ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "ollama_host": "OLLAMA_HOST",
    "default_provider": "LOG_ANALYZER_PROVIDER",
}


# Default model configurations (latest as of Feb 2026)
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-5-20250929",
    "gemini": "gemini-3-pro-preview",
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
    """
    
    default_provider: Optional[str] = None
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    config_file: Optional[Path] = None
    
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
        return {
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
    config = Config()
    config_path = path or DEFAULT_CONFIG_FILE
    
    # Load from file if it exists and YAML is available
    if config_path.exists() and YAML_AVAILABLE:
        check_config_permissions(config_path)
        
        try:
            with open(config_path) as f:
                data = yaml.safe_load(f) or {}
            
            config.config_file = config_path
            config.default_provider = data.get("default_provider")
            
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
        except Exception as e:
            warnings.warn(f"Error loading config from {config_path}: {e}")
    
    # Override default_provider from environment if set
    env_provider = os.environ.get(ENV_VARS["default_provider"])
    if env_provider:
        config.default_provider = env_provider
    
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
        raise ImportError(
            "PyYAML is required to save config. Run: pip install pyyaml"
        )
    
    config_path = path or DEFAULT_CONFIG_FILE
    
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write config
    with open(config_path, "w") as f:
        yaml.safe_dump(config.to_dict(), f, default_flow_style=False)
    
    # Set secure permissions (owner read/write only)
    try:
        config_path.chmod(0o600)
    except OSError:
        pass  # Ignore permission errors (e.g., on Windows)
    
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
            except Exception:
                status[provider]["server_available"] = False
    
    return status
