"""
CRUD (Create, Read, Update, Delete) operations for database models.

Provides helper functions for database operations.
"""


from sqlalchemy import desc
from sqlalchemy.orm import Session

from . import models

# ==================== Analysis CRUD ====================

def create_analysis(db: Session, analysis_data: dict) -> models.Analysis:
    """
    Create a new analysis record.

    Args:
        db: Database session
        analysis_data: Dictionary with analysis fields

    Returns:
        Created Analysis model instance
    """
    analysis = models.Analysis(**analysis_data)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def get_analysis(db: Session, analysis_id: str) -> models.Analysis | None:
    """
    Get analysis by ID.

    Args:
        db: Database session
        analysis_id: Analysis UUID

    Returns:
        Analysis model instance or None if not found
    """
    return db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()


def get_analyses(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    format_filter: str | None = None
) -> list[models.Analysis]:
    """
    Get list of analyses with pagination and optional filtering.

    Args:
        db: Database session
        skip: Number of records to skip (offset)
        limit: Maximum number of records to return
        format_filter: Optional log format filter

    Returns:
        List of Analysis model instances
    """
    query = db.query(models.Analysis)

    if format_filter:
        query = query.filter(models.Analysis.detected_format == format_filter)

    return query.order_by(desc(models.Analysis.created_at)).offset(skip).limit(limit).all()


def get_analyses_count(db: Session, format_filter: str | None = None) -> int:
    """
    Get total count of analyses.

    Args:
        db: Database session
        format_filter: Optional log format filter

    Returns:
        Total count of analyses
    """
    query = db.query(models.Analysis)

    if format_filter:
        query = query.filter(models.Analysis.detected_format == format_filter)

    return query.count()


def delete_analysis(db: Session, analysis_id: str) -> bool:
    """
    Delete analysis by ID.

    Args:
        db: Database session
        analysis_id: Analysis UUID

    Returns:
        True if deleted, False if not found
    """
    analysis = get_analysis(db, analysis_id)
    if analysis:
        db.delete(analysis)
        db.commit()
        return True
    return False


# ==================== Triage CRUD ====================

def create_triage(db: Session, triage_data: dict) -> models.Triage:
    """
    Create a new triage record.

    Args:
        db: Database session
        triage_data: Dictionary with triage fields

    Returns:
        Created Triage model instance
    """
    triage = models.Triage(**triage_data)
    db.add(triage)
    db.commit()
    db.refresh(triage)
    return triage


def get_triage(db: Session, triage_id: str) -> models.Triage | None:
    """
    Get triage by ID.

    Args:
        db: Database session
        triage_id: Triage UUID

    Returns:
        Triage model instance or None if not found
    """
    return db.query(models.Triage).filter(models.Triage.id == triage_id).first()


def get_triages_by_analysis(db: Session, analysis_id: str) -> list[models.Triage]:
    """
    Get all triages for a specific analysis.

    Args:
        db: Database session
        analysis_id: Analysis UUID

    Returns:
        List of Triage model instances
    """
    return (
        db.query(models.Triage)
        .filter(models.Triage.analysis_id == analysis_id)
        .order_by(desc(models.Triage.created_at))
        .all()
    )


def delete_triage(db: Session, triage_id: str) -> bool:
    """
    Delete triage by ID.

    Args:
        db: Database session
        triage_id: Triage UUID

    Returns:
        True if deleted, False if not found
    """
    triage = get_triage(db, triage_id)
    if triage:
        db.delete(triage)
        db.commit()
        return True
    return False
