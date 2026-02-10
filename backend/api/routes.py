"""
API routes for log analyzer endpoints.

Provides REST API endpoints for log analysis and triage.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session

from log_analyzer.analyzer import AVAILABLE_PARSERS
from log_analyzer.ai_providers.base import ProviderNotAvailableError
from backend.db.database import get_db
from backend.db import crud
from backend.api import schemas
from backend.services.analyzer_service import AnalyzerService
from backend.services.triage_service import TriageService
from backend.constants import (
    DEFAULT_MAX_ERRORS,
    MAX_ERRORS_LIMIT,
    MIN_ERRORS_LIMIT,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
)


logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/v1", tags=["Log Analysis"])


# ==================== Analysis Endpoints ====================

@router.post("/analyze", response_model=schemas.AnalysisResponse, status_code=201)
async def analyze_log_file(
    file: UploadFile = File(..., description="Log file to analyze"),
    format: str = Query("auto", description="Log format (currently only 'auto' supported)"),
    max_errors: int = Query(DEFAULT_MAX_ERRORS, ge=MIN_ERRORS_LIMIT, le=MAX_ERRORS_LIMIT, description=f"Maximum errors to collect ({MIN_ERRORS_LIMIT}-{MAX_ERRORS_LIMIT})"),
    db: Session = Depends(get_db)
):
    """
    Upload and analyze a log file.

    **Parameters:**
    - **file**: Log file to upload (multipart/form-data)
    - **format**: Log format detection mode (default: 'auto')
    - **max_errors**: Maximum number of errors/warnings to collect (1-1000)

    **Returns:**
    - Analysis results with statistics, errors, and metadata
    """
    logger.info(f"POST /api/v1/analyze - file={file.filename}, format={format}, max_errors={max_errors}")

    try:
        service = AnalyzerService()
        analysis = await service.analyze_uploaded_file(
            file,
            db,
            max_errors=max_errors,
            log_format=format
        )
        logger.info(f"Analysis created successfully: {analysis.id}")
        return analysis

    except ValueError as e:
        logger.warning(f"Invalid request for {file.filename}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        logger.error(f"File not found during analysis of {file.filename}: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis failed for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/analyses", response_model=schemas.AnalysisListResponse)
def list_analyses(
    skip: int = Query(0, ge=0, description="Number of records to skip (offset)"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE, description=f"Maximum records to return ({MIN_PAGE_SIZE}-{MAX_PAGE_SIZE})"),
    format: Optional[str] = Query(None, description="Filter by log format"),
    db: Session = Depends(get_db)
):
    """
    List all analyses with pagination.

    **Parameters:**
    - **skip**: Offset for pagination
    - **limit**: Number of results per page (max 100)
    - **format**: Optional filter by log format

    **Returns:**
    - Paginated list of analyses with metadata
    """
    analyses = crud.get_analyses(db, skip=skip, limit=limit, format_filter=format)
    total = crud.get_analyses_count(db, format_filter=format)

    return schemas.AnalysisListResponse(
        analyses=analyses,
        total=total,
        page=(skip // limit) + 1,
        per_page=limit,
        total_pages=(total + limit - 1) // limit
    )


@router.get("/analysis/{analysis_id}", response_model=schemas.AnalysisResponse)
def get_analysis(
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific analysis by ID.

    **Parameters:**
    - **analysis_id**: UUID of the analysis

    **Returns:**
    - Complete analysis details
    """
    analysis = crud.get_analysis(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
    return analysis


@router.delete("/analysis/{analysis_id}", response_model=schemas.SuccessResponse)
def delete_analysis(
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete an analysis and its associated file.

    **Parameters:**
    - **analysis_id**: UUID of the analysis to delete

    **Returns:**
    - Success message

    **Note:** This also deletes all associated triages (cascade delete)
    """
    # Get analysis to find file path
    analysis = crud.get_analysis(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    # Delete file from disk
    service = AnalyzerService()
    service.delete_file(analysis.file_path)

    # Delete from database
    crud.delete_analysis(db, analysis_id)

    return schemas.SuccessResponse(message=f"Analysis {analysis_id} deleted successfully")


# ==================== Triage Endpoints ====================

@router.post("/triage", response_model=schemas.TriageResponse, status_code=201)
def run_triage(
    request: schemas.TriageRequest,
    db: Session = Depends(get_db)
):
    """
    Run AI-powered triage on an analysis.

    **Parameters:**
    - **analysis_id**: UUID of the analysis to triage
    - **provider**: Optional AI provider (anthropic, gemini, ollama)

    **Returns:**
    - Triage results with issues, severity, and recommendations

    **Note:** Requires AI provider API keys to be configured
    """
    logger.info(f"POST /api/v1/triage - analysis_id={request.analysis_id}, provider={request.provider or 'auto'}")

    try:
        service = TriageService(provider_name=request.provider)
        triage = service.run_triage_on_analysis(
            db,
            request.analysis_id,
            provider_name=request.provider
        )
        logger.info(f"Triage created successfully: {triage.id}")
        return triage

    except ValueError as e:
        logger.warning(f"Invalid triage request: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except ProviderNotAvailableError as e:
        logger.error(f"AI provider not available: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"AI Service Unavailable: {str(e)}. Please configure API keys or start Ollama."
        )
    except Exception as e:
        logger.error(f"Triage failed for analysis {request.analysis_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Triage failed: {str(e)}")


@router.get("/triage/{triage_id}", response_model=schemas.TriageResponse)
def get_triage(
    triage_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific triage result by ID.

    **Parameters:**
    - **triage_id**: UUID of the triage

    **Returns:**
    - Complete triage details with issues and recommendations
    """
    triage = crud.get_triage(db, triage_id)
    if not triage:
        raise HTTPException(status_code=404, detail=f"Triage {triage_id} not found")
    return triage


@router.get("/analysis/{analysis_id}/triages", response_model=list[schemas.TriageResponse])
def get_triages_for_analysis(
    analysis_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all triages for a specific analysis.

    **Parameters:**
    - **analysis_id**: UUID of the analysis

    **Returns:**
    - List of all triage results for this analysis
    """
    # Verify analysis exists
    analysis = crud.get_analysis(db, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")

    triages = crud.get_triages_by_analysis(db, analysis_id)
    return triages


# ==================== Utility Endpoints ====================

@router.get("/formats", response_model=schemas.FormatsResponse)
def list_formats():
    """
    Get list of supported log formats.

    **Returns:**
    - List of all supported log formats with descriptions
    """
    formats = []
    for parser in AVAILABLE_PARSERS:
        formats.append({
            "name": parser.name,
            "description": parser.__class__.__doc__ or f"{parser.name} format parser"
        })

    # Add universal fallback
    formats.append({
        "name": "universal",
        "description": "Universal fallback parser for unknown formats"
    })

    return schemas.FormatsResponse(
        formats=formats,
        total=len(formats)
    )
