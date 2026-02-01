"""
AI Provider factory for creating and managing provider instances.

This module provides functions to instantiate AI providers based on
configuration and auto-detect available providers.
"""

import os
from typing import Optional

from .base import AIProvider, ProviderNotAvailableError


# Registry of available provider classes (populated on import)
_PROVIDER_REGISTRY: dict[str, type] = {}


def _register_providers():
    """
    Lazily register available providers.
    
    This allows providers to be imported only when needed,
    avoiding import errors if a provider's SDK is not installed.
    """
    global _PROVIDER_REGISTRY
    
    if _PROVIDER_REGISTRY:
        return  # Already registered
    
    # Try to import each provider
    try:
        from .anthropic_provider import AnthropicProvider
        _PROVIDER_REGISTRY["anthropic"] = AnthropicProvider
    except ImportError:
        pass  # anthropic SDK not installed
    
    try:
        from .gemini_provider import GeminiProvider
        _PROVIDER_REGISTRY["gemini"] = GeminiProvider
    except ImportError:
        pass  # google-generativeai SDK not installed
    
    try:
        from .ollama_provider import OllamaProvider
        _PROVIDER_REGISTRY["ollama"] = OllamaProvider
    except ImportError:
        pass  # httpx not installed


def list_available_providers() -> list[str]:
    """
    List all providers that have their dependencies installed.
    
    Returns:
        List of provider names that can be instantiated
    """
    _register_providers()
    return list(_PROVIDER_REGISTRY.keys())


def list_configured_providers() -> list[str]:
    """
    List providers that are both installed and configured.
    
    A provider is considered configured if it has necessary
    credentials (API keys) or can connect (Ollama).
    
    Returns:
        List of provider names ready for use
    """
    _register_providers()
    configured = []
    
    for name, provider_class in _PROVIDER_REGISTRY.items():
        try:
            provider = provider_class()
            if provider.is_available():
                configured.append(name)
        except Exception:
            pass  # Provider failed to initialize
    
    return configured


def get_provider(
    name: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> AIProvider:
    """
    Get an AI provider instance.
    
    If no name is specified, attempts to auto-detect the best
    available provider in order of preference:
    1. Anthropic (if ANTHROPIC_API_KEY is set)
    2. Gemini (if GOOGLE_API_KEY is set)
    3. Ollama (if server is running locally)
    
    Args:
        name: Provider name ('anthropic', 'gemini', 'ollama')
              If None, auto-detects best available.
        model: Optional model override
        **kwargs: Additional provider-specific arguments
        
    Returns:
        Configured AIProvider instance
        
    Raises:
        ProviderNotAvailableError: If no provider is available
        ValueError: If specified provider is unknown
    """
    _register_providers()
    
    if name:
        # Specific provider requested
        name = name.lower()
        if name not in _PROVIDER_REGISTRY:
            available = list(_PROVIDER_REGISTRY.keys())
            raise ValueError(
                f"Unknown provider '{name}'. "
                f"Available providers: {available}"
            )
        
        provider_class = _PROVIDER_REGISTRY[name]
        provider = provider_class(model=model, **kwargs) if model else provider_class(**kwargs)
        
        if not provider.is_available():
            raise ProviderNotAvailableError(
                f"Provider '{name}' is not available. "
                f"Check that required API keys are set or service is running."
            )
        
        return provider
    
    # Auto-detect best available provider
    # Priority: Anthropic > Gemini > Ollama
    priority_order = ["anthropic", "gemini", "ollama"]
    
    for provider_name in priority_order:
        if provider_name not in _PROVIDER_REGISTRY:
            continue
        
        try:
            provider_class = _PROVIDER_REGISTRY[provider_name]
            provider = provider_class(model=model, **kwargs) if model else provider_class(**kwargs)
            
            if provider.is_available():
                return provider
        except Exception:
            continue  # Try next provider
    
    # No provider available
    installed = list_available_providers()
    if not installed:
        raise ProviderNotAvailableError(
            "No AI providers installed. Install one of:\n"
            "  pip install anthropic        # For Claude\n"
            "  pip install google-generativeai  # For Gemini\n"
            "  pip install httpx            # For Ollama"
        )
    
    raise ProviderNotAvailableError(
        f"No AI providers configured. Installed: {installed}\n"
        "Configure one of:\n"
        "  export ANTHROPIC_API_KEY=your-key\n"
        "  export GOOGLE_API_KEY=your-key\n"
        "  Or start Ollama: ollama serve"
    )


def get_provider_info(name: str) -> dict:
    """
    Get information about a specific provider.
    
    Args:
        name: Provider name
        
    Returns:
        Dictionary with provider details
    """
    _register_providers()
    
    name = name.lower()
    if name not in _PROVIDER_REGISTRY:
        return {"error": f"Unknown provider: {name}"}
    
    provider_class = _PROVIDER_REGISTRY[name]
    
    info = {
        "name": name,
        "installed": True,
        "configured": False,
        "default_model": provider_class.default_model if hasattr(provider_class, 'default_model') else "unknown",
    }
    
    try:
        provider = provider_class()
        info["configured"] = provider.is_available()
        info["current_model"] = provider.get_model()
    except Exception as e:
        info["error"] = str(e)
    
    return info
