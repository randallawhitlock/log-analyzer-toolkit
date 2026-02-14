"""
Service layer for AI-powered log triage.

Wraps the existing TriageEngine from CLI tool and adapts it for API use.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from backend.constants import DEFAULT_TRIAGE_MAX_ERRORS
from backend.db import crud, models
from log_analyzer.ai_providers.base import Severity
from log_analyzer.triage import TriageEngine, TriageResult

logger = logging.getLogger(__name__)


class TriageService:
    """
    Service for AI-powered log triage.

    Wraps TriageEngine and provides database persistence.
    """

    def __init__(self, provider_name: Optional[str] = None):
        """
        Initialize triage service.

        Args:
            provider_name: AI provider to use (anthropic, gemini, ollama)
                          Auto-selects if not provided
        """
        logger.debug(f"Initializing TriageService with provider: {provider_name or 'auto'}")
        self.engine = TriageEngine(provider_name=provider_name)
        logger.info(f"TriageService initialized with provider: {self.engine._get_provider().name}")

    def triage_file(self, file_path: str, max_errors: int = DEFAULT_TRIAGE_MAX_ERRORS) -> TriageResult:
        """
        Run AI triage on a log file.

        Args:
            file_path: Path to log file
            max_errors: Maximum errors to analyze

        Returns:
            TriageResult: Triage results from AI

        Raises:
            AIError: If AI analysis fails
            ValueError: If log file cannot be processed
        """
        return self.engine.triage(
            file_path,
            max_errors=max_errors
        )

    def triage_result_to_dict(
        self,
        result: TriageResult,
        analysis_id: str
    ) -> dict:
        """
        Convert TriageResult to dictionary for database storage.

        Args:
            result: TriageResult from TriageEngine
            analysis_id: ID of the analysis this triage is for

        Returns:
            dict: Data ready for database insertion
        """
        # Convert issues to dict format
        issues_data = []
        for issue in result.issues:
            issues_data.append({
                "title": issue.title,
                "severity": issue.severity.value if isinstance(issue.severity, Severity) else issue.severity,
                "confidence": issue.confidence,
                "description": issue.description,
                "affected_components": issue.affected_components,
                "recommendation": issue.recommendation,
                "root_cause_analysis": issue.root_cause_analysis,
                "category": issue.category,
                "evidence": issue.evidence,
            })

        return {
            "analysis_id": analysis_id,
            "summary": result.summary,
            "overall_severity": result.overall_severity.value if isinstance(result.overall_severity, Severity) else result.overall_severity,
            "confidence": result.confidence,
            "issues": issues_data,
            "provider_used": result.provider_used,
            "analysis_time_ms": result.analysis_time_ms,
            "raw_analysis": result.raw_analysis
        }

    def run_triage_on_analysis(
        self,
        db: Session,
        analysis_id: str,
        provider_name: Optional[str] = None
    ) -> models.Triage:
        """
        Run AI triage on an existing analysis.

        Args:
            db: Database session
            analysis_id: Analysis ID to triage
            provider_name: Optional AI provider override

        Returns:
            models.Triage: Created triage record

        Raises:
            ValueError: If analysis not found
            AIError: If AI analysis fails
        """
        logger.info(f"Running triage on analysis: {analysis_id} (provider={provider_name or 'default'})")

        # Get the analysis
        analysis = crud.get_analysis(db, analysis_id)
        if not analysis:
            logger.error(f"Analysis not found: {analysis_id}")
            raise ValueError(f"Analysis {analysis_id} not found")

        logger.debug(f"Found analysis: {analysis.filename} ({analysis.detected_format})")

        # Create triage engine with specified provider
        if provider_name:
            logger.debug(f"Creating new engine with provider: {provider_name}")
            engine = TriageEngine(provider_name=provider_name)
        else:
            engine = self.engine

        # Run triage
        result = engine.triage(
            analysis.file_path,
            max_errors=DEFAULT_TRIAGE_MAX_ERRORS
        )

        logger.info(f"Triage completed: {len(result.issues)} issues found, "
                   f"severity={result.overall_severity.value}, "
                   f"confidence={result.confidence:.2f}, "
                   f"time={result.analysis_time_ms}ms")

        # Convert to dict
        triage_data = self.triage_result_to_dict(result, analysis_id)

        # Store in database
        triage = crud.create_triage(db, triage_data)
        logger.info(f"Created triage record: {triage.id} for analysis {analysis_id}")

        return triage

    def deep_dive_issue(
        self,
        db: Session,
        analysis_id: str,
        issue_title: str,
        issue_description: str,
        issue_severity: str,
        issue_recommendation: str,
        affected_components: list[str],
        provider_name: Optional[str] = None,
    ) -> dict:
        """
        Perform a deep dive analysis on a specific triage issue.

        Sends the issue context back to the LLM for detailed
        resolution steps and root cause analysis.

        Args:
            db: Database session
            analysis_id: Analysis ID for context
            issue_title: Title of the issue to deep dive
            issue_description: Original issue description
            issue_severity: Issue severity level
            issue_recommendation: Original recommendation
            affected_components: List of affected components
            provider_name: Optional AI provider override

        Returns:
            dict with detailed_analysis, provider_used, model_used, analysis_time_ms
        """
        import time

        logger.info(f"Deep dive requested for issue: {issue_title}")

        # Get analysis context
        analysis = crud.get_analysis(db, analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        # Build deep dive prompt
        components_str = ", ".join(affected_components) if affected_components else "Unknown"
        prompt = f"""You are an expert systems engineer performing a deep-dive analysis on a specific issue found during log analysis.

## Original Issue Context
- **Issue Title**: {issue_title}
- **Severity**: {issue_severity}
- **Affected Components**: {components_str}
- **Description**: {issue_description}
- **Initial Recommendation**: {issue_recommendation}

## Log File Context
- **File**: {analysis.filename}
- **Format**: {analysis.detected_format}
- **Total Lines**: {analysis.total_lines:,}

---

Please provide a comprehensive deep-dive analysis following the **Claude Opus 4.6 Agentic Workflow**.

First, begin with a **Reasoning & Verification** section where you:
1. **Assess Task Complexity**: Determine the depth of reasoning required.
2. **Deconstruct Context**: Analyze the provided issue details against the log evidence.
3. **Brainstorm Root Causes**: Generate multiple hypotheses and rule them out.
4. **Edge Case Analysis**: List at least 3 specific edge cases (race conditions, state desync, etc.).
5. **Agentic Planning**: Plan a multi-step verification strategy.
6. **Reflexion (Self-Correction)**:
    - Critique your own plan. Identify 3 potential failure modes or security risks.
    - Refine the plan to address these weaknesses.
7. **Deployment Strategy**:
    - If a code fix is required, draft a **Git Commit Message** following **Conventional Commits** (e.g., `fix(auth): handle null token in validation`).
    - Draft a **Pull Request Description** with sections: 'Summary', 'Test Plan', and 'Risk Assessment'.
    - Ensure the PR strategy favors **Atomic Commits** (small, focused changes).

Then, provide the structured response with the following sections logic:

### Root Cause Analysis
Explain the most likely root cause(s) of this issue in detail, referencing specific evidence. **Use Chain of Density**: Start with a high-level summary, then iteratively add technical details and exact code references to increase information density without adding fluff.

### Agentic Resolution Plan
Provide exact, actionable steps to fix this issue. Break down the fix into atomic units if complex.

### Verification Steps (Test Plan)
How to verify the fix worked. Include commands to run, logs to check, or metrics to monitor.
**MANDATORY**: Confirm that new tests cover the fixed logic (Goal: 100% patch coverage).

### Prevention Strategies
How to prevent this issue from recurring. Include monitoring recommendations, alerting thresholds, or architectural improvements.

### Related Issues
Note any other issues that might be caused by or related to this problem.

Format your response in clean markdown with headers, bullet points, and code blocks where appropriate."""

        # Get AI provider
        from log_analyzer.ai_providers import get_provider
        engine_provider = get_provider(provider_name)

        start_time = time.time()
        response = engine_provider.analyze(prompt)
        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(f"Deep dive completed in {elapsed_ms:.0f}ms for: {issue_title}")

        return {
            "issue_title": issue_title,
            "detailed_analysis": response.content,
            "provider_used": response.provider,
            "model_used": response.model,
            "analysis_time_ms": elapsed_ms,
        }

