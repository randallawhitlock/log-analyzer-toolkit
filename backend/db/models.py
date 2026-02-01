"""
SQLAlchemy database models for log analysis.

Models:
    - Analysis: Stores log file analysis results
    - Triage: Stores AI-powered triage results
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from .database import Base


class Analysis(Base):
    """
    Stores log file analysis results.

    Represents the output from LogAnalyzer.analyze(), persisted to database.
    """
    __tablename__ = "analyses"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # File metadata
    filename = Column(String, nullable=False, index=True)
    detected_format = Column(String, index=True)
    file_path = Column(String)  # Path to uploaded file on disk

    # Parsing statistics
    total_lines = Column(Integer, nullable=False, default=0)
    parsed_lines = Column(Integer, nullable=False, default=0)
    failed_lines = Column(Integer, nullable=False, default=0)
    parse_success_rate = Column(Float)  # Percentage
    error_rate = Column(Float)  # Percentage of ERROR + CRITICAL

    # Analysis results (stored as JSON)
    level_counts = Column(JSON)  # {"ERROR": 10, "WARNING": 5, ...}
    top_errors = Column(JSON)  # [[message, count], ...]
    top_sources = Column(JSON)  # [[source, count], ...]
    status_codes = Column(JSON)  # {200: 1000, 404: 50, ...} for HTTP logs

    # Time range
    earliest_timestamp = Column(DateTime, nullable=True)
    latest_timestamp = Column(DateTime, nullable=True)
    time_span = Column(String, nullable=True)  # Duration as string

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    triages = relationship(
        "Triage",
        back_populates="analysis",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Analysis(id={self.id}, filename={self.filename}, format={self.detected_format})>"


class Triage(Base):
    """
    Stores AI-powered triage results.

    Represents the output from TriageEngine.triage(), linked to an Analysis.
    """
    __tablename__ = "triages"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key to analysis
    analysis_id = Column(
        String,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Triage results
    summary = Column(Text, nullable=False)
    overall_severity = Column(String, nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW, HEALTHY
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0

    # Detailed issues (stored as JSON array)
    issues = Column(JSON)  # [{"title": "...", "severity": "...", ...}, ...]

    # AI metadata
    provider_used = Column(String, nullable=False)  # anthropic, gemini, ollama
    analysis_time_ms = Column(Float)  # Time taken for AI analysis
    raw_analysis = Column(Text, nullable=True)  # Full raw AI response

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    analysis = relationship("Analysis", back_populates="triages")

    def __repr__(self):
        return f"<Triage(id={self.id}, analysis_id={self.analysis_id}, severity={self.overall_severity})>"
