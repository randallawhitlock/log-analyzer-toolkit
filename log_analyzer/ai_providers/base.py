"""
Base classes and interfaces for AI providers.

This module defines the abstract interface that all AI providers must implement,
along with common data structures for AI responses and errors.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

__all__ = [
    "AIError",
    "ProviderNotAvailableError",
    "RateLimitError",
    "AuthenticationError",
    "Severity",
    "AIResponse",
    "TriageIssue",
    "TriageResult",
    "AIProvider",
]


class AIError(Exception):
    """Base exception for AI provider errors."""

    pass


class ProviderNotAvailableError(AIError):
    """Raised when a provider is not available or configured."""

    pass


class RateLimitError(AIError):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class AuthenticationError(AIError):
    """Raised when authentication fails (invalid API key)."""

    pass


class Severity(str, Enum):
    """Severity levels for triaged issues."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    HEALTHY = "HEALTHY"


@dataclass
class AIResponse:
    """
    Represents a response from an AI provider.

    Attributes:
        content: The main text response from the AI
        model: The model that generated the response
        provider: Name of the provider (anthropic, gemini, ollama)
        usage: Token usage statistics (if available)
        latency_ms: Response latency in milliseconds
        timestamp: When the response was received
        raw_response: Original response object for debugging
    """

    content: str
    model: str
    provider: str
    usage: dict = field(default_factory=dict)
    latency_ms: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)
    raw_response: Optional[Any] = None

    def __repr__(self) -> str:
        """Return string representation without sensitive raw_response data."""
        return (
            f"AIResponse(content='{self.content[:50]}{'...' if len(self.content) > 50 else ''}', "
            f"model='{self.model}', provider='{self.provider}', "
            f"latency_ms={self.latency_ms})"
        )


@dataclass
class TriageIssue:
    """
    Represents a single triaged issue.

    Attributes:
        title: Brief description of the issue
        severity: Issue severity level
        confidence: AI's confidence in this assessment (0.0 to 1.0)
        description: Detailed explanation of the issue
        affected_components: List of affected system components
        sample_logs: Representative log entries for this issue
        recommendation: Suggested remediation steps
        root_cause_analysis: Detailed root cause with evidence from log patterns
        category: Issue category (error_spike, connection_failure, auth_failure, etc.)
        evidence: Specific log patterns or entries supporting this finding
    """

    title: str
    severity: Severity
    confidence: float
    description: str
    affected_components: list[str] = field(default_factory=list)
    sample_logs: list[str] = field(default_factory=list)
    recommendation: str = ""
    git_actions: Optional[dict] = None  # { "commit_message": str, "pr_description": str }
    root_cause_analysis: str = ""
    category: str = "unknown"
    evidence: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate confidence is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")


@dataclass
class TriageResult:
    """
    Complete triage analysis result.

    Attributes:
        summary: Human-readable summary of system health
        overall_severity: Overall system health severity
        confidence: Overall confidence in the analysis
        issues: List of identified issues
        analyzed_lines: Number of log lines analyzed
        error_count: Total errors found in logs
        warning_count: Total warnings found in logs
        analysis_time_ms: Time taken for AI analysis
        provider_used: Which AI provider generated this result
        raw_analysis: Full AI response for transparency
    """

    summary: str
    overall_severity: Severity
    confidence: float
    issues: list[TriageIssue] = field(default_factory=list)
    analyzed_lines: int = 0
    error_count: int = 0
    warning_count: int = 0
    analysis_time_ms: Optional[float] = None
    provider_used: str = ""
    raw_analysis: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "summary": self.summary,
            "overall_severity": self.overall_severity.value,
            "confidence": self.confidence,
            "issues": [
                {
                    "title": issue.title,
                    "severity": issue.severity.value,
                    "confidence": issue.confidence,
                    "description": issue.description,
                    "affected_components": issue.affected_components,
                    "sample_logs": issue.sample_logs,
                    "recommendation": issue.recommendation,
                    "git_actions": issue.git_actions,
                    "root_cause_analysis": issue.root_cause_analysis,
                    "category": issue.category,
                    "evidence": issue.evidence,
                }
                for issue in self.issues
            ],
            "analyzed_lines": self.analyzed_lines,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "analysis_time_ms": self.analysis_time_ms,
            "provider_used": self.provider_used,
        }


class AIProvider(ABC):
    """
    Abstract base class for AI providers.

    All AI providers must implement this interface to ensure
    consistent behavior across different backends.

    Security Notes:
        - API keys should NEVER be logged or included in error messages
        - Log content should be sanitized before sending to cloud providers
        - Implement rate limiting to avoid excessive API costs
    """

    # Provider identifier (must be set by subclasses)
    name: str = "base"

    # Default model to use
    default_model: str = ""

    @abstractmethod
    def analyze(self, prompt: str, system_prompt: Optional[str] = None) -> AIResponse:
        """
        Send a prompt to the AI and get a response.

        Args:
            prompt: The user prompt/question to send
            system_prompt: Optional system prompt for context

        Returns:
            AIResponse containing the AI's response

        Raises:
            ProviderNotAvailableError: If provider is not configured
            AuthenticationError: If API key is invalid
            RateLimitError: If rate limits are exceeded
            AIError: For other AI-related errors
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if this provider is available and configured.

        Returns:
            True if the provider can be used, False otherwise
        """
        pass

    @abstractmethod
    def get_model(self) -> str:
        """
        Get the current model being used.

        Returns:
            Model identifier string
        """
        pass

    def sanitize_log_content(self, content: str, max_length: int = 50000) -> str:
        """
        Sanitize log content before sending to AI provider.

        This helps prevent:
        - Prompt injection attacks
        - Excessive token usage
        - Sending overly sensitive data

        Args:
            content: Raw log content
            max_length: Maximum characters to include

        Returns:
            Sanitized content safe for AI analysis
        """
        if not content:
            return ""

        # Redact PII (Emails, IPv4, and IPv6)
        # Note: These are basic patterns and may not catch all edge cases

        # Email: basic alphanumeric + @ + domain
        content = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]", content)

        # IPv4: 4 groups of digits separated by dots
        content = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[IP_REDACTED]", content)

        # IPv6: Full and compressed formats
        content = re.sub(
            r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b",  # Full
            "[IP_REDACTED]",
            content,
        )
        content = re.sub(
            r"\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b",  # Compressed end
            "[IP_REDACTED]",
            content,
        )
        content = re.sub(
            r"\b::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}\b",  # Compressed start
            "[IP_REDACTED]",
            content,
        )

        # Truncate if too long
        if len(content) > max_length:
            content = content[:max_length] + f"\n\n[... truncated, {len(content) - max_length} more characters ...]"

        # Remove potential prompt injection patterns
        # This is a basic safeguard - more sophisticated filtering may be needed
        dangerous_patterns = [
            "ignore previous instructions",
            "disregard all prior",
            "forget everything",
            "new instructions:",
            "system prompt:",
        ]

        content_lower = content.lower()
        for pattern in dangerous_patterns:
            if pattern in content_lower:
                # Don't remove, but wrap in a way that makes injection less likely
                content = f"[LOG DATA START]\n{content}\n[LOG DATA END]"
                break

        return content

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.get_model()})"
