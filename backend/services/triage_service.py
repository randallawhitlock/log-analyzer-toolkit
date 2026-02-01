"""
Service layer for AI-powered log triage.

Wraps the existing TriageEngine from CLI tool and adapts it for API use.
"""

from typing import Optional
from sqlalchemy.orm import Session

from log_analyzer.triage import TriageEngine, TriageResult
from log_analyzer.ai_providers.base import Severity
from backend.db import crud, models


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
        self.engine = TriageEngine(provider_name=provider_name)

    def triage_file(self, file_path: str, max_errors: int = 50) -> TriageResult:
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
                "recommendation": issue.recommendation
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
        # Get the analysis
        analysis = crud.get_analysis(db, analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        # Create triage engine with specified provider
        if provider_name:
            engine = TriageEngine(provider_name=provider_name)
        else:
            engine = self.engine

        # Run triage
        result = engine.triage(
            analysis.file_path,
            max_errors=50
        )

        # Convert to dict
        triage_data = self.triage_result_to_dict(result, analysis_id)

        # Store in database
        triage = crud.create_triage(db, triage_data)

        return triage
