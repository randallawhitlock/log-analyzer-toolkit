"""
Pydantic schemas for API request/response validation.

These schemas define the structure of data sent to and returned from API endpoints.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ==================== Analysis Schemas ====================

class AnalysisBase(BaseModel):
    """Base schema with common analysis fields."""
    filename: str
    detected_format: str
    total_lines: int
    parsed_lines: int
    failed_lines: int
    parse_success_rate: float
    error_rate: float


class AnalysisCreate(BaseModel):
    """Schema for creating an analysis (used internally)."""
    filename: str
    detected_format: str
    total_lines: int
    parsed_lines: int
    failed_lines: int
    parse_success_rate: float
    error_rate: float
    level_counts: Dict[str, int]
    top_errors: List[List[Any]]
    top_sources: List[List[Any]]
    status_codes: Dict[int, int]
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None
    time_span: Optional[str] = None
    file_path: str


class AnalysisResponse(BaseModel):
    """Schema for analysis API response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    detected_format: str
    total_lines: int
    parsed_lines: int
    failed_lines: int
    parse_success_rate: float
    error_rate: float
    level_counts: Dict[str, int]
    top_errors: List[List[Any]]
    top_sources: List[List[Any]]
    status_codes: Dict[int, int]
    earliest_timestamp: Optional[datetime] = None
    latest_timestamp: Optional[datetime] = None
    time_span: Optional[str] = None
    created_at: datetime


class AnalysisListResponse(BaseModel):
    """Schema for paginated analysis list response."""
    analyses: List[AnalysisResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


# ==================== Triage Schemas ====================

class TriageIssue(BaseModel):
    """Schema for a single triage issue."""
    title: str
    severity: str
    confidence: float
    description: str
    affected_components: List[str]
    recommendation: str


class TriageCreate(BaseModel):
    """Schema for creating a triage."""
    analysis_id: str
    summary: str
    overall_severity: str
    confidence: float
    issues: List[Dict[str, Any]]
    provider_used: str
    analysis_time_ms: float
    raw_analysis: Optional[str] = None


class TriageRequest(BaseModel):
    """Schema for triage request."""
    analysis_id: str
    provider: Optional[str] = Field(
        None,
        description="AI provider to use (anthropic, gemini, ollama). Auto-selects if not provided."
    )


class TriageResponse(BaseModel):
    """Schema for triage API response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    analysis_id: str
    summary: str
    overall_severity: str
    confidence: float
    issues: List[Dict[str, Any]]
    provider_used: str
    analysis_time_ms: float
    created_at: datetime


# ==================== General Response Schemas ====================

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str
    error_type: Optional[str] = None


class SuccessResponse(BaseModel):
    """Schema for simple success responses."""
    message: str


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    version: str
    timestamp: datetime


class FormatsResponse(BaseModel):
    """Schema for supported formats response."""
    formats: List[Dict[str, str]]
    total: int
