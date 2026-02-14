"""
Anthropic Claude AI provider implementation.

This module provides integration with Anthropic's Claude models
for intelligent log analysis and triage.

Security Notes:
    - API key is read from ANTHROPIC_API_KEY environment variable
    - API key is never logged or included in error messages
    - Log content is sanitized before sending to API
"""

import os
import time
from typing import Optional

from .base import (
    AIError,
    AIProvider,
    AIResponse,
    AuthenticationError,
    ProviderNotAvailableError,
    RateLimitError,
)

# Latest Claude models as of February 2026
CLAUDE_MODELS = {
    "claude-sonnet-3-5": "claude-3-5-sonnet-latest",  # Best balance of capability and cost
    "claude-opus-3-5": "claude-3-opus-latest",  # Most capable model
    "claude-haiku-3-5": "claude-3-haiku-20240307",  # Fastest, most cost-effective
}

# Default model - Sonnet 3.5 offers best balance for log analysis
DEFAULT_MODEL = CLAUDE_MODELS["claude-sonnet-3-5"]


class AnthropicProvider(AIProvider):
    """
    Anthropic Claude AI provider.

    Uses the Anthropic Python SDK to communicate with Claude models.
    Requires the ANTHROPIC_API_KEY environment variable to be set.

    Attributes:
        name: Provider identifier ('anthropic')
        default_model: Default model to use (Claude Sonnet 3.5)
    """

    name = "anthropic"
    default_model = DEFAULT_MODEL

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ):
        """
        Initialize the Anthropic provider.

        Args:
            model: Model to use. Defaults to Claude Sonnet 4.5.
                   Can be a short name (e.g., 'claude-sonnet-4-5') or
                   full model ID (e.g., 'claude-sonnet-4-5-20250929').
            api_key: API key. If not provided, reads from ANTHROPIC_API_KEY env var.
            max_tokens: Maximum tokens in response (default: 4096)
            timeout: Request timeout in seconds (default: 120)

        Security:
            The api_key parameter should only be used for testing.
            In production, always use the environment variable.
        """
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._max_tokens = max_tokens
        self._timeout = timeout

        # Resolve model name
        if model:
            # Check if it's a short name
            self._model = CLAUDE_MODELS.get(model, model)
        else:
            self._model = DEFAULT_MODEL

        # Lazily initialize client
        self._client = None

    def _get_client(self):
        """
        Get or create the Anthropic client.

        Returns:
            Initialized Anthropic client

        Raises:
            ProviderNotAvailableError: If anthropic package is not installed
            AuthenticationError: If API key is not set
        """
        if self._client is not None:
            return self._client

        if not self._api_key:
            raise AuthenticationError("Anthropic API key not found. " "Set the ANTHROPIC_API_KEY environment variable.")

        try:
            import anthropic
        except ImportError:
            raise ProviderNotAvailableError("Anthropic SDK not installed. Run: pip install anthropic") from None

        self._client = anthropic.Anthropic(
            api_key=self._api_key,
            timeout=self._timeout,
        )

        return self._client

    def is_available(self) -> bool:
        """
        Check if Anthropic provider is available.

        Returns:
            True if SDK is installed and API key is set
        """
        # Check for API key
        if not self._api_key:
            return False

        # Check if SDK is installed
        try:
            import anthropic  # noqa: F401

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
        Send a prompt to Claude and get a response.

        Args:
            prompt: The user prompt to send
            system_prompt: Optional system prompt for context

        Returns:
            AIResponse containing Claude's response

        Raises:
            AuthenticationError: If API key is invalid
            RateLimitError: If rate limits are exceeded
            AIError: For other API errors
        """
        import anthropic

        client = self._get_client()

        start_time = time.perf_counter()

        try:
            # Build messages
            messages = [{"role": "user", "content": prompt}]

            # Make API call
            response = client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system_prompt or "",
                messages=messages,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Extract response content
            content = ""
            if response.content:
                content = response.content[0].text

            # Build usage info
            usage = {}
            if response.usage:
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                }

            return AIResponse(
                content=content,
                model=response.model,
                provider=self.name,
                usage=usage,
                latency_ms=latency_ms,
                raw_response=response,
            )

        except anthropic.AuthenticationError as e:
            raise AuthenticationError("Invalid Anthropic API key. Please check your ANTHROPIC_API_KEY.") from e

        except anthropic.RateLimitError as e:
            # Try to extract retry-after if available
            retry_after = None
            if hasattr(e, "response") and e.response:
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    try:
                        retry_after = float(retry_after)
                    except ValueError:
                        retry_after = None

            raise RateLimitError(
                "Anthropic rate limit exceeded. Please try again later.",
                retry_after=retry_after,
            ) from e

        except anthropic.APIStatusError as e:
            raise AIError(f"Anthropic API error: {e.status_code}") from e

        except anthropic.APIConnectionError as e:
            raise AIError("Failed to connect to Anthropic API. Check your internet connection.") from e

        except Exception as e:
            raise AIError(f"Unexpected error calling Anthropic API: {type(e).__name__}") from e

    @classmethod
    def list_models(cls) -> dict[str, str]:
        """
        List available Claude models.

        Returns:
            Dictionary mapping short names to full model IDs
        """
        return CLAUDE_MODELS.copy()
