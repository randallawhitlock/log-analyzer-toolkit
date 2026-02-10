"""
Ollama local LLM provider implementation.

This module provides integration with locally-running Ollama models
for intelligent log analysis and triage with complete privacy.

Privacy Notes:
    - All processing happens locally on your machine
    - No data is sent to external servers
    - Requires Ollama to be installed and running locally
"""

import logging
import time
from typing import Optional

from .base import (
    AIProvider,
    AIResponse,
    AIError,
    ProviderNotAvailableError,
)


logger = logging.getLogger(__name__)


# Recommended models for log analysis
OLLAMA_MODELS = {
    "llama3.3": "llama3.3:latest",           # Best overall for complex analysis
    "llama3.2": "llama3.2:latest",
    "llama3": "llama3:latest",           # Good balance
    "mistral": "mistral:latest",             # Fast and capable
    "mixtral": "mixtral:latest",             # Large mixture of experts model
    "codellama": "codellama:latest",         # Good for technical logs
    "deepseek-r1": "deepseek-r1:latest",     # Reasoning-focused
}

# Default model - llama3.3 offers best quality for log analysis
DEFAULT_MODEL = "llama3"
DEFAULT_HOST = "http://localhost:11434"


class OllamaProvider(AIProvider):
    """
    Ollama local LLM provider.
    
    Uses HTTP API to communicate with locally-running Ollama server.
    Provides complete privacy as all processing happens locally.
    
    Attributes:
        name: Provider identifier ('ollama')
        default_model: Default model to use (llama3.3)
    """
    
    name = "ollama"
    default_model = DEFAULT_MODEL
    
    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
        timeout: float = 300.0,  # Larger timeout for local models
    ):
        """
        Initialize the Ollama provider.
        
        Args:
            model: Model to use. Defaults to llama3.3.
            host: Ollama server URL. Defaults to http://localhost:11434
            timeout: Request timeout in seconds (default: 300)
        """
        self._host = host or DEFAULT_HOST
        self._timeout = timeout
        
        # Resolve model name
        if model:
            self._model = OLLAMA_MODELS.get(model, model)
        else:
            self._model = DEFAULT_MODEL
        
        # Lazily initialize client
        self._client = None
        logger.debug(f"OllamaProvider initialized: host={self._host}, model={self._model}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup."""
        self.close()
        return False  # Don't suppress exceptions

    def __del__(self):
        """
        Cleanup on deletion (fallback).

        Note: Context manager (__enter__/__exit__) is preferred.
        This is a fallback for cases where context manager isn't used.
        """
        self.close()

    def close(self):
        """Close the httpx client and release connections."""
        if self._client is not None:
            try:
                self._client.close()
                logger.debug(f"Ollama client closed successfully")
            except Exception as e:
                logger.warning(f"Error closing Ollama client: {e}")
            finally:
                self._client = None
    
    def _get_client(self):
        """
        Get or create the HTTP client.
        
        Returns:
            Configured httpx client
            
        Raises:
            ProviderNotAvailableError: If httpx is not installed
        """
        if self._client is not None:
            return self._client
        
        try:
            import httpx
        except ImportError:
            raise ProviderNotAvailableError(
                "httpx not installed. Run: pip install httpx"
            )
        
        self._client = httpx.Client(
            base_url=self._host,
            timeout=self._timeout,
        )
        
        return self._client
    
    def is_available(self) -> bool:
        """
        Check if Ollama is available and running.
        
        Returns:
            True if Ollama server is reachable
        """
        try:
            import httpx
        except ImportError:
            return False
        
        try:
            client = self._get_client()
            response = client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    def get_model(self) -> str:
        """
        Get the current model being used.
        
        Returns:
            Model identifier string
        """
        return self._model
    
    def list_local_models(self) -> list[str]:
        """
        List models available in local Ollama installation.
        
        Returns:
            List of model names installed locally
            
        Raises:
            AIError: If unable to fetch model list
        """
        try:
            client = self._get_client()
            response = client.get("/api/tags")
            response.raise_for_status()
            
            data = response.json()
            models = data.get("models", [])
            return [m.get("name", "") for m in models if m.get("name")]
            
        except Exception as e:
            raise AIError(f"Failed to list Ollama models: {e}") from e
    
    def analyze(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """
        Send a prompt to Ollama and get a response.
        
        Args:
            prompt: The user prompt to send
            system_prompt: Optional system prompt for context
            
        Returns:
            AIResponse containing model's response
            
        Raises:
            ProviderNotAvailableError: If Ollama is not running
            AIError: For other errors
        """
        import httpx
        
        client = self._get_client()
        
        start_time = time.perf_counter()
        
        # Build request payload
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,  # Get complete response at once
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = client.post("/api/generate", json=payload)
            
            if response.status_code == 404:
                raise AIError(
                    f"Model '{self._model}' not found. "
                    f"Run: ollama pull {self._model}"
                )
            
            response.raise_for_status()
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            data = response.json()
            
            content = data.get("response", "")
            
            # Build usage info
            usage = {
                "eval_count": data.get("eval_count", 0),
                "prompt_eval_count": data.get("prompt_eval_count", 0),
            }
            
            # Add timing info if available
            if "total_duration" in data:
                usage["total_duration_ns"] = data["total_duration"]
            
            return AIResponse(
                content=content,
                model=data.get("model", self._model),
                provider=self.name,
                usage=usage,
                latency_ms=latency_ms,
                raw_response=data,
            )
            
        except httpx.ConnectError as e:
            raise ProviderNotAvailableError(
                f"Cannot connect to Ollama at {self._host}. "
                "Make sure Ollama is running: ollama serve"
            ) from e
            
        except httpx.TimeoutException as e:
            raise AIError(
                f"Ollama request timed out after {self._timeout}s. "
                "The model may be loading or the prompt too complex."
            ) from e
            
        except httpx.HTTPStatusError as e:
            raise AIError(f"Ollama HTTP error: {e.response.status_code}") from e
            
        except Exception as e:
            raise AIError(f"Unexpected error calling Ollama: {type(e).__name__}") from e
    
    def pull_model(self, model: Optional[str] = None) -> bool:
        """
        Pull a model to local Ollama installation.
        
        Args:
            model: Model to pull. Defaults to the configured model.
            
        Returns:
            True if pull was successful
            
        Note:
            This will stream progress to stdout.
        """
        model = model or self._model
        
        try:
            client = self._get_client()
            
            # Use streaming endpoint to show progress
            with client.stream(
                "POST",
                "/api/pull",
                json={"name": model},
                timeout=None,  # No timeout for pull
            ) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        status = data.get("status", "")
                        if status:
                            print(f"  {status}")
            
            return True
            
        except Exception as e:
            print(f"Failed to pull model: {e}")
            return False
    
    @classmethod
    def list_recommended_models(cls) -> dict[str, str]:
        """
        List recommended models for log analysis.
        
        Returns:
            Dictionary mapping short names to full model IDs
        """
        return OLLAMA_MODELS.copy()
