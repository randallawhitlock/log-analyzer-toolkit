"""
AI-powered log triage engine.

This module provides intelligent log analysis using AI providers
to identify issues, categorize severity, and suggest remediation.

The triage engine:
1. Takes log analysis results from LogAnalyzer
2. Constructs optimized prompts for AI analysis
3. Parses AI responses into structured triage results
4. Provides actionable insights and recommendations
"""

import json
import logging
import re
import time
from typing import Optional

from .analyzer import AnalysisResult, LogAnalyzer
from .ai_providers import get_provider, AIProvider
from .ai_providers.base import (
    AIResponse,
    AIError,
    Severity,
    TriageIssue,
    TriageResult,
)


logger = logging.getLogger(__name__)


# System prompt for log triage
TRIAGE_SYSTEM_PROMPT = """You are an expert systems engineer and log analyst. Your role is to analyze log data and provide intelligent triage to help identify and resolve system issues.

When analyzing logs, you should:
1. Identify the most critical issues first
2. Group related errors together
3. Look for root causes, not just symptoms
4. Consider temporal patterns and correlations
5. Provide specific, actionable recommendations

Your analysis should be thorough but concise. Focus on what matters most for system health and stability.

IMPORTANT: You must respond in valid JSON format matching the schema provided."""


TRIAGE_PROMPT_TEMPLATE = """Analyze the following log file summary and provide an intelligent triage assessment.

## Log File Information
- **File**: {filepath}
- **Format**: {format}
- **Total Lines**: {total_lines:,}
- **Parsed Lines**: {parsed_lines:,}
- **Time Range**: {time_range}

## Severity Breakdown
{severity_breakdown}

## Top Errors ({error_count} total)
{top_errors}

## Sample Error Entries
{sample_errors}

---

Please analyze this log data and respond with a JSON object matching this exact schema:

```json
{{
  "summary": "A 1-3 sentence natural language summary of the system's health status",
  "overall_severity": "CRITICAL|HIGH|MEDIUM|LOW|HEALTHY",
  "confidence": 0.0 to 1.0,
  "issues": [
    {{
      "title": "Brief issue title",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "confidence": 0.0 to 1.0,
      "description": "Detailed explanation of the issue",
      "affected_components": ["component1", "component2"],
      "recommendation": "Specific steps to resolve"
    }}
  ]
}}
```

Respond with ONLY the JSON object, no additional text."""


def build_triage_prompt(result: AnalysisResult) -> str:
    """
    Build a prompt for AI triage from analysis results.

    Args:
        result: AnalysisResult from LogAnalyzer

    Returns:
        Formatted prompt string
    """
    logger.debug(f"Building triage prompt for {result.filepath}")

    # Build severity breakdown
    severity_lines = []
    for level in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
        count = result.level_counts.get(level, 0)
        if count > 0:
            pct = (count / result.parsed_lines * 100) if result.parsed_lines > 0 else 0
            severity_lines.append(f"- {level}: {count:,} ({pct:.1f}%)")
    severity_breakdown = "\n".join(severity_lines) or "- No severity levels detected"
    
    # Build top errors list
    top_error_lines = []
    for msg, count in result.top_errors[:10]:
        # Truncate long messages
        truncated = msg[:100] + "..." if len(msg) > 100 else msg
        top_error_lines.append(f"- [{count}x] {truncated}")
    top_errors = "\n".join(top_error_lines) or "- No errors detected"
    
    # Build sample error entries
    sample_error_lines = []
    for entry in result.errors[:5]:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "---"
        msg = entry.message[:200] + "..." if len(entry.message) > 200 else entry.message
        sample_error_lines.append(f"[{ts}] {entry.level}: {msg}")
    sample_errors = "\n".join(sample_error_lines) or "No error samples available"
    
    # Format time range
    if result.time_span:
        time_range = str(result.time_span)
    elif result.earliest_timestamp and result.latest_timestamp:
        time_range = f"{result.earliest_timestamp} to {result.latest_timestamp}"
    else:
        time_range = "Unknown"
    
    # Build the prompt
    prompt = TRIAGE_PROMPT_TEMPLATE.format(
        filepath=result.filepath,
        format=result.detected_format,
        total_lines=result.total_lines,
        parsed_lines=result.parsed_lines,
        time_range=time_range,
        severity_breakdown=severity_breakdown,
        error_count=len(result.errors),
        top_errors=top_errors,
        sample_errors=sample_errors,
    )

    # Estimate token count (rough: 4 chars per token)
    estimated_tokens = len(prompt) // 4
    logger.debug(f"Triage prompt built: {len(prompt)} chars, ~{estimated_tokens} tokens")

    return prompt


def parse_triage_response(response: AIResponse, result: AnalysisResult) -> TriageResult:
    """
    Parse AI response into a TriageResult.

    Args:
        response: AIResponse from AI provider
        result: Original AnalysisResult for context

    Returns:
        Parsed TriageResult
    """
    logger.debug(f"Parsing triage response from {response.provider} "
                f"(latency={response.latency_ms}ms, length={len(response.content)} chars)")

    content = response.content.strip()

    # Try to extract JSON from the response
    # Handle cases where the response includes markdown code blocks
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
    if json_match:
        logger.debug("Extracted JSON from markdown code block")
        content = json_match.group(1)

    # Try to find JSON object in the content
    json_start = content.find('{')
    json_end = content.rfind('}') + 1
    if json_start >= 0 and json_end > json_start:
        content = content[json_start:json_end]

    try:
        data = json.loads(content)
        logger.debug(f"Successfully parsed JSON response with {len(data.get('issues', []))} issues")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.debug(f"Response content: {content[:500]}")
        # Return a fallback result if parsing fails
        return TriageResult(
            summary=f"AI analysis completed but response parsing failed: {e}",
            overall_severity=Severity.MEDIUM,
            confidence=0.3,
            issues=[],
            analyzed_lines=result.parsed_lines,
            error_count=len(result.errors),
            warning_count=len(result.warnings),
            analysis_time_ms=response.latency_ms,
            provider_used=response.provider,
            raw_analysis=response.content,
        )
    
    # Parse issues
    issues = []
    for issue_data in data.get("issues", []):
        try:
            severity_str = issue_data.get("severity", "MEDIUM").upper()
            severity = Severity(severity_str) if severity_str in Severity.__members__ else Severity.MEDIUM
            
            issues.append(TriageIssue(
                title=issue_data.get("title", "Unknown Issue"),
                severity=severity,
                confidence=float(issue_data.get("confidence", 0.5)),
                description=issue_data.get("description", ""),
                affected_components=issue_data.get("affected_components", []),
                sample_logs=issue_data.get("sample_logs", []),
                recommendation=issue_data.get("recommendation", ""),
            ))
        except (ValueError, KeyError) as e:
            # Skip malformed issues
            continue
    
    # Parse overall severity
    overall_severity_str = data.get("overall_severity", "MEDIUM").upper()
    overall_severity = (
        Severity(overall_severity_str)
        if overall_severity_str in Severity.__members__
        else Severity.MEDIUM
    )
    
    return TriageResult(
        summary=data.get("summary", "Analysis completed"),
        overall_severity=overall_severity,
        confidence=float(data.get("confidence", 0.5)),
        issues=issues,
        analyzed_lines=result.parsed_lines,
        error_count=len(result.errors),
        warning_count=len(result.warnings),
        analysis_time_ms=response.latency_ms,
        provider_used=response.provider,
        raw_analysis=response.content,
    )


class TriageEngine:
    """
    AI-powered log triage engine.
    
    Uses AI providers to intelligently analyze log files and
    provide structured triage results with actionable insights.
    
    Example:
        ```python
        engine = TriageEngine()
        result = engine.triage("/var/log/app.log")
        print(result.summary)
        for issue in result.issues:
            print(f"[{issue.severity}] {issue.title}")
        ```
    """
    
    def __init__(
        self,
        provider: Optional[AIProvider] = None,
        provider_name: Optional[str] = None,
    ):
        """
        Initialize the triage engine.
        
        Args:
            provider: Specific AIProvider instance to use
            provider_name: Name of provider to use (anthropic, gemini, ollama)
                          If neither is provided, auto-detects best available.
        """
        self._provider = provider
        self._provider_name = provider_name
        self._analyzer = LogAnalyzer()
    
    def _get_provider(self) -> AIProvider:
        """Get or create the AI provider."""
        if self._provider is not None:
            logger.debug(f"Using cached provider: {self._provider.name}")
            return self._provider

        logger.debug(f"Initializing AI provider: {self._provider_name or 'auto-detect'}")
        self._provider = get_provider(self._provider_name)
        logger.info(f"AI provider initialized: {self._provider.name} ({self._provider.get_model()})")
        return self._provider
    
    def triage(
        self,
        filepath: str,
        parser: Optional[str] = None,
        max_errors: int = 50,
    ) -> TriageResult:
        """
        Perform intelligent triage on a log file.

        Args:
            filepath: Path to the log file to analyze
            parser: Optional parser name to use (auto-detects if not specified)
            max_errors: Maximum error entries to collect for analysis

        Returns:
            TriageResult with AI-powered analysis

        Raises:
            AIError: If AI analysis fails
            ValueError: If log format cannot be detected
            FileNotFoundError: If log file doesn't exist
        """
        logger.info(f"Starting triage for {filepath}")
        logger.debug(f"Parameters: parser={parser}, max_errors={max_errors}")
        start_time = time.time()

        # First, analyze the log file
        logger.debug("Performing log analysis...")
        analysis_result = self._analyzer.analyze(
            filepath,
            parser=parser,
            max_errors=max_errors,
        )

        # Build the prompt
        prompt = build_triage_prompt(analysis_result)

        # Get AI provider and analyze
        provider = self._get_provider()

        # Sanitize the prompt content
        logger.debug("Sanitizing prompt content (PII redaction)")
        prompt = provider.sanitize_log_content(prompt)

        # Send to AI
        logger.debug(f"Sending prompt to AI provider: {provider.name}")
        response = provider.analyze(prompt, system_prompt=TRIAGE_SYSTEM_PROMPT)
        logger.debug(f"Received AI response: {response.latency_ms}ms latency")

        # Parse the response
        triage_result = parse_triage_response(response, analysis_result)

        elapsed = time.time() - start_time
        logger.info(f"Triage completed in {elapsed:.2f}s: "
                   f"{len(triage_result.issues)} issues identified, "
                   f"severity={triage_result.overall_severity.value}, "
                   f"confidence={triage_result.confidence:.2f}")

        return triage_result
    
    def triage_from_result(self, result: AnalysisResult) -> TriageResult:
        """
        Perform triage on an existing AnalysisResult.
        
        Useful when you've already analyzed a log file and want
        to add AI triage without re-parsing.
        
        Args:
            result: Existing AnalysisResult from LogAnalyzer
            
        Returns:
            TriageResult with AI-powered analysis
        """
        # Build the prompt
        prompt = build_triage_prompt(result)
        
        # Get AI provider and analyze
        provider = self._get_provider()
        prompt = provider.sanitize_log_content(prompt)
        response = provider.analyze(prompt, system_prompt=TRIAGE_SYSTEM_PROMPT)
        
        return parse_triage_response(response, result)


def quick_triage(
    filepath: str,
    provider: Optional[str] = None,
) -> TriageResult:
    """
    Convenience function for quick log triage.
    
    Args:
        filepath: Path to log file
        provider: Optional provider name (auto-detects if not specified)
        
    Returns:
        TriageResult with AI analysis
    """
    engine = TriageEngine(provider_name=provider)
    return engine.triage(filepath)
