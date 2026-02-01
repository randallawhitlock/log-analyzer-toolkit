"""
Google Gemini AI provider implementation.

This module provides integration with Google's Gemini models
for intelligent log analysis and triage.

Security Notes:
    - API key is read from GOOGLE_API_KEY environment variable
    - API key is never logged or included in error messages
    - Log content is sanitized before sending to API
"""

import os
import time
from typing import Optional

from .base import (
    AIProvider,
    AIResponse,
    AIError,
    AuthenticationError,
    ProviderNotAvailableError,
    RateLimitError,
)


# Latest Gemini models as of February 2026
GEMINI_MODELS = {
    "gemini-3-pro": "gemini-3-pro",           # Most capable model
    "gemini-3-flash": "gemini-3-flash",       # Fast and efficient
    "gemini-3-flash-lite": "gemini-3-flash-lite",  # Most cost-effective
}

# Default model - Gemini 3 Pro for best log analysis quality
DEFAULT_MODEL = GEMINI_MODELS["gemini-3-pro"]


class GeminiProvider(AIProvider):
    """
    Google Gemini AI provider.
    
    Uses the Google Generative AI SDK to communicate with Gemini models.
    Requires the GOOGLE_API_KEY environment variable to be set.
    
    Attributes:
        name: Provider identifier ('gemini')
        default_model: Default model to use (Gemini 3 Pro)
    """
    
    name = "gemini"
    default_model = DEFAULT_MODEL
    
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_output_tokens: int = 4096,
        timeout: float = 120.0,
    ):
        """
        Initialize the Gemini provider.
        
        Args:
            model: Model to use. Defaults to Gemini 3 Pro.
            api_key: API key. If not provided, reads from GOOGLE_API_KEY env var.
            max_output_tokens: Maximum tokens in response (default: 4096)
            timeout: Request timeout in seconds (default: 120)
            
        Security:
            The api_key parameter should only be used for testing.
            In production, always use the environment variable.
        """
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self._max_output_tokens = max_output_tokens
        self._timeout = timeout
        
        # Resolve model name
        if model:
            self._model = GEMINI_MODELS.get(model, model)
        else:
            self._model = DEFAULT_MODEL
        
        # Lazily initialize client
        self._client = None
        self._configured = False
    
    def _configure(self):
        """
        Configure the Gemini SDK with API key.
        
        Raises:
            ProviderNotAvailableError: If SDK is not installed
            AuthenticationError: If API key is not set
        """
        if self._configured:
            return
        
        if not self._api_key:
            raise AuthenticationError(
                "Google API key not found. "
                "Set the GOOGLE_API_KEY environment variable."
            )
        
        try:
            import google.generativeai as genai
        except ImportError:
            raise ProviderNotAvailableError(
                "Google Generative AI SDK not installed. "
                "Run: pip install google-generativeai"
            )
        
        genai.configure(api_key=self._api_key)
        self._configured = True
    
    def _get_model(self, system_instruction: Optional[str] = None):
        """
        Get or create the Gemini model instance.
        
        Args:
            system_instruction: Optional system instruction for the model
        
        Returns:
            Configured GenerativeModel instance
        """
        # Create new model instance if system instruction changed
        if self._client is not None and system_instruction is None:
            return self._client
        
        self._configure()
        
        import google.generativeai as genai
        
        # Configure generation settings
        generation_config = genai.GenerationConfig(
            max_output_tokens=self._max_output_tokens,
        )
        
        # Build model with optional system instruction
        model_kwargs = {
            "model_name": self._model,
            "generation_config": generation_config,
        }
        
        if system_instruction:
            model_kwargs["system_instruction"] = system_instruction
        
        model = genai.GenerativeModel(**model_kwargs)
        
        # Only cache if no system instruction (default model)
        if system_instruction is None:
            self._client = model
        
        return model
    
    def is_available(self) -> bool:
        """
        Check if Gemini provider is available.
        
        Returns:
            True if SDK is installed and API key is set
        """
        # Check for API key
        if not self._api_key:
            return False
        
        # Check if SDK is installed
        try:
            import google.generativeai
            return True
        except ImportError:
            return False
    
    def get_model(self) -> str:
        """
        Get the current model being used.
        
        Returns:
            Model identifier string
        """
        return self._model
    
    def analyze(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """
        Send a prompt to Gemini and get a response.
        
        Args:
            prompt: The user prompt to send
            system_prompt: Optional system prompt for context
            
        Returns:
            AIResponse containing Gemini's response
            
        Raises:
            AuthenticationError: If API key is invalid
            RateLimitError: If rate limits are exceeded
            AIError: For other API errors
        """
        import google.generativeai as genai
        from google.api_core import exceptions as google_exceptions
        
        # Get model with system instruction if provided
        model = self._get_model(system_instruction=system_prompt)
        
        start_time = time.perf_counter()
        
        try:
            # Make API call (system prompt is now part of model config)
            response = model.generate_content(prompt)
            
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            # Extract response content
            content = ""
            if response.text:
                content = response.text
            
            # Build usage info if available
            usage = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = {
                    "prompt_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                    "candidates_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                    "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0),
                }
            
            return AIResponse(
                content=content,
                model=self._model,
                provider=self.name,
                usage=usage,
                latency_ms=latency_ms,
                raw_response=response,
            )
            
        except google_exceptions.InvalidArgument as e:
            if "API key" in str(e).lower():
                raise AuthenticationError(
                    "Invalid Google API key. Please check your GOOGLE_API_KEY."
                ) from e
            raise AIError(f"Invalid request to Gemini API: {e}") from e
            
        except google_exceptions.ResourceExhausted as e:
            raise RateLimitError(
                "Gemini rate limit exceeded. Please try again later."
            ) from e
            
        except google_exceptions.PermissionDenied as e:
            raise AuthenticationError(
                "Permission denied. Check your Google API key permissions."
            ) from e
            
        except google_exceptions.GoogleAPIError as e:
            raise AIError(f"Gemini API error: {e}") from e
            
        except Exception as e:
            raise AIError(f"Unexpected error calling Gemini API: {type(e).__name__}") from e
    
    @classmethod
    def list_models(cls) -> dict[str, str]:
        """
        List available Gemini models.
        
        Returns:
            Dictionary mapping short names to full model IDs
        """
        return GEMINI_MODELS.copy()
