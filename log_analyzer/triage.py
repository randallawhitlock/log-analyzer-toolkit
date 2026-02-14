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

from .ai_providers import AIProvider, get_provider
from .ai_providers.base import (
    AIResponse,
    Severity,
    TriageIssue,
    TriageResult,
)
from .analyzer import AnalysisResult, LogAnalyzer
from .constants import (
    CHARS_PER_TOKEN,
    DEFAULT_MAX_ERRORS,
    MAX_DISPLAY_ENTRIES,
    MAX_MESSAGE_LENGTH,
)

logger = logging.getLogger(__name__)


# System prompt for log triage
TRIAGE_SYSTEM_PROMPT = """<system_instructions>
<role>
You are Claude Code - Senior Logic Analyst. Your goal is to provide rigorous, technical log analysis with the precision of a Principal Systems Engineer.
</role>

<tone_override>
Maintain a strictly **Technical, Objective, and Concise** tone. Avoid conversational fillers, warm pleasantries, or natural language padding. Focus purely on data, logic, and solutions.
</tone_override>

<standards>
1. **Adaptive Thinking**: Assess the complexity of the log pattern. If the issue is complex, dynamically check deep root causes.
2. **Atomic Atomicity**: Recommended fixes MUST be the smallest possible self-contained change. Avoid "rewrite" suggestions.
3. **Regression Safety**: Explicitly verify that the proposed fix matches the specific error signature and introduces NO new side effects.
4. **Error Handling**: Anticipate potential failures. Ensure recommended code handles null states, timeouts, and exceptions gracefully.
5. **Evidence-Based**: Do not hallucinate. If the log data is insufficient, state "Insufficient Evidence" clearly.
</standards>

<thinking_process>
Before generating the JSON output, you MUST perform the following adaptive reasoning steps in a <thinking> block:
1. **Complexity Assessment**: Determine if this is a simple error or a complex system failure.
2. **Pattern Analysis**: Deconstruct the log lines.
3. **Root Cause Hypothesis**: Formulate 2-3 hypotheses.
4. **Disproof & Verification**: Attempt to disprove your own hypotheses using the log data.
5. **Edge Case Scan**: Explicitly scan for race conditions, timeouts, or rare states.
6. **Solution Engineering**: Design a fix that follows the <standards> (Atomic, Verified).
</thinking_process>

<output_format>
You must respond with a VALID JSON object matching the requested schema, wrapped in a markdown code block, preceded STRICTLY by your <thinking> block.
</output_format>
</system_instructions>"""


TRIAGE_PROMPT_TEMPLATE = """Analyze the following log file summary and provide an intelligent triage assessment with root cause analysis.

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

## Top Warnings ({warning_count} total)
{top_warnings}

## Error Sources (components generating errors)
{error_sources}

## HTTP Status Codes
{status_codes}

## Temporal Patterns
{temporal_patterns}

## Sample Error Entries
{sample_errors}

## Sample Warning Entries
{sample_warnings}

---

Perform a thorough evaluation of the errors AND warnings. For each issue you identify:
1. **Categorize** the issue type (e.g., connection_failure, auth_failure, resource_exhaustion, timeout, error_spike, data_corruption, configuration, dependency)
2. **Analyze root cause** — correlate error patterns with source components, temporal clusters, and warning signals that preceded errors
3. **Cite evidence** — reference specific log patterns, error messages, or temporal data that support your finding

Respond with a JSON object matching this exact schema:

```json
{{
  "summary": "A 1-3 sentence natural language summary of the system's health status",
  "overall_severity": "CRITICAL|HIGH|MEDIUM|LOW|HEALTHY",
  "confidence": 0.0 to 1.0,
  "issues": [
    {{
      "title": "Brief issue title",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "category": "error_spike|connection_failure|auth_failure|resource_exhaustion|timeout|data_corruption|configuration|dependency|unknown",
      "confidence": 0.0 to 1.0,
      "description": "Detailed explanation of the issue",
      "root_cause_analysis": "In-depth root cause analysis correlating error patterns, warning signals, source components, and temporal data. Explain WHY this is happening, not just WHAT.",
      "evidence": ["Specific log pattern or entry 1", "Temporal correlation 2", "Warning signal 3"],
      "affected_components": ["component1", "component2"],
      "recommendation": "Specific, actionable steps to resolve — smallest possible fix",
      "git_actions": {{
        "commit_message": "Conventional commit message (e.g. fix: handle null pointer...)",
        "pr_description": "Markdown description for a Pull Request"
      }}
    }}
  ]
}}
```

Respond with the valid JSON object wrapped in a code block, preceded by your <thinking> block."""


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
        truncated = msg[:MAX_MESSAGE_LENGTH] + "..." if len(msg) > MAX_MESSAGE_LENGTH else msg
        top_error_lines.append(f"- [{count}x] {truncated}")
    top_errors = "\n".join(top_error_lines) or "- No errors detected"

    # Build top warnings list
    top_warning_msgs = {}
    for entry in result.warnings[:50]:
        msg = entry.message[:MAX_MESSAGE_LENGTH]
        top_warning_msgs[msg] = top_warning_msgs.get(msg, 0) + 1
    top_warning_lines = []
    for msg, count in sorted(top_warning_msgs.items(), key=lambda x: x[1], reverse=True)[:10]:
        top_warning_lines.append(f"- [{count}x] {msg}")
    top_warnings = "\n".join(top_warning_lines) or "- No warnings detected"

    # Build error sources — correlate sources to error counts
    error_source_lines = []
    if result.top_sources:
        for source, count in result.top_sources[:10]:
            error_source_lines.append(f"- {source}: {count:,} entries")
    error_sources = "\n".join(error_source_lines) or "- No source data available"

    # Build HTTP status codes
    status_code_lines = []
    if result.status_codes:
        for code, count in sorted(result.status_codes.items(),
                                   key=lambda x: x[1], reverse=True)[:10]:
            indicator = "⚠️" if str(code).startswith(('4', '5')) else "✓"
            status_code_lines.append(f"- {indicator} HTTP {code}: {count:,}")
    status_codes = "\n".join(status_code_lines) or "- No HTTP status code data"

    # Build temporal patterns from analytics
    temporal_lines = []
    if result.analytics:
        analytics = result.analytics
        if hasattr(analytics, 'error_rate_trend') and analytics.error_rate_trend:
            temporal_lines.append(f"- Error rate trend: {analytics.error_rate_trend}")
        if hasattr(analytics, 'temporal_distribution') and analytics.temporal_distribution:
            # Show top time buckets with most activity
            sorted_buckets = sorted(
                analytics.temporal_distribution.items(),
                key=lambda x: x[1], reverse=True
            )[:5]
            for ts, count in sorted_buckets:
                temporal_lines.append(f"- {ts}: {count:,} entries")
        if hasattr(analytics, 'hourly_distribution') and analytics.hourly_distribution:
            # Find peak hours
            peak_hours = sorted(
                analytics.hourly_distribution.items(),
                key=lambda x: x[1], reverse=True
            )[:3]
            for hour, count in peak_hours:
                temporal_lines.append(f"- Peak hour {hour}:00: {count:,} entries")
    temporal_patterns = "\n".join(temporal_lines) or "- No temporal data available"

    # Build sample error entries
    sample_error_lines = []
    for entry in result.errors[:MAX_DISPLAY_ENTRIES]:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "---"
        msg = entry.message[:200] + "..." if len(entry.message) > 200 else entry.message
        source = f" ({entry.source})" if entry.source else ""
        sample_error_lines.append(f"[{ts}] {entry.level}{source}: {msg}")
    sample_errors = "\n".join(sample_error_lines) or "No error samples available"

    # Build sample warning entries
    sample_warning_lines = []
    for entry in result.warnings[:MAX_DISPLAY_ENTRIES]:
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S") if entry.timestamp else "---"
        msg = entry.message[:200] + "..." if len(entry.message) > 200 else entry.message
        source = f" ({entry.source})" if entry.source else ""
        sample_warning_lines.append(f"[{ts}] {entry.level}{source}: {msg}")
    sample_warnings = "\n".join(sample_warning_lines) or "No warning samples available"

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
        warning_count=len(result.warnings),
        top_warnings=top_warnings,
        error_sources=error_sources,
        status_codes=status_codes,
        temporal_patterns=temporal_patterns,
        sample_errors=sample_errors,
        sample_warnings=sample_warnings,
    )

    # Estimate token count
    estimated_tokens = len(prompt) // CHARS_PER_TOKEN
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
                git_actions=issue_data.get("git_actions"),
                root_cause_analysis=issue_data.get("root_cause_analysis", ""),
                category=issue_data.get("category", "unknown"),
                evidence=issue_data.get("evidence", []),
            ))
        except (ValueError, KeyError):
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
        max_errors: int = DEFAULT_MAX_ERRORS,
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
