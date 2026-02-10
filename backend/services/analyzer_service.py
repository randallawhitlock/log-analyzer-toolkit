"""
Service layer for log analysis.

Wraps the existing LogAnalyzer from CLI tool and adapts it for API use.
"""

import logging
import os
import uuid
import aiofiles
from typing import Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session

from log_analyzer.analyzer import LogAnalyzer, AnalysisResult
from backend.db import crud, models
from backend.api import schemas
from backend.constants import DEFAULT_MAX_ERRORS, UPLOAD_DIRECTORY


logger = logging.getLogger(__name__)


# Directory for uploaded files
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)


class AnalyzerService:
    """
    Service for analyzing log files.

    Wraps LogAnalyzer and provides async file handling and database persistence.
    """

    def __init__(self):
        """Initialize analyzer service."""
        self.analyzer = LogAnalyzer()

    async def save_uploaded_file(self, file: UploadFile) -> str:
        """
        Save uploaded file to disk.

        Args:
            file: FastAPI UploadFile

        Returns:
            str: Path to saved file
        """
        logger.debug(f"Saving uploaded file: {file.filename}")

        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1] or ".log"
        file_path = os.path.join(UPLOAD_DIRECTORY, f"{file_id}{file_extension}")

        # Save file asynchronously
        async with aiofiles.open(file_path, 'wb') as out_file:
            content = await file.read()
            file_size = len(content)
            await out_file.write(content)

        logger.info(f"Saved file {file.filename} ({file_size:,} bytes) to {file_path}")
        return file_path

    def analyze_file(
        self,
        file_path: str,
        max_errors: int = DEFAULT_MAX_ERRORS
    ) -> AnalysisResult:
        """
        Analyze a log file using LogAnalyzer.

        Args:
            file_path: Path to log file
            max_errors: Maximum errors to collect

        Returns:
            AnalysisResult: Analysis results

        Raises:
            ValueError: If log format cannot be detected
        """
        logger.info(f"Starting analysis of {file_path} (max_errors={max_errors})")

        result = self.analyzer.analyze(
            file_path,
            max_errors=max_errors,
            use_fallback=True
        )

        logger.info(f"Analysis complete: {result.parsed_lines:,} lines parsed, "
                   f"format={result.detected_format}, error_rate={result.error_rate:.1f}%")

        return result

    def analysis_result_to_dict(
        self,
        result: AnalysisResult,
        file_path: str,
        original_filename: str
    ) -> dict:
        """
        Convert AnalysisResult to dictionary for database storage.

        Args:
            result: AnalysisResult from LogAnalyzer
            file_path: Path where file was saved
            original_filename: Original uploaded filename

        Returns:
            dict: Data ready for database insertion
        """
        return {
            "filename": original_filename,
            "detected_format": result.detected_format,
            "total_lines": result.total_lines,
            "parsed_lines": result.parsed_lines,
            "failed_lines": result.failed_lines,
            "parse_success_rate": result.parse_success_rate,
            "error_rate": result.error_rate,
            "level_counts": result.level_counts,
            "top_errors": result.top_errors,
            "top_sources": result.top_sources,
            "status_codes": result.status_codes,
            "earliest_timestamp": result.earliest_timestamp,
            "latest_timestamp": result.latest_timestamp,
            "time_span": str(result.time_span) if result.time_span else None,
            "file_path": file_path
        }

    async def analyze_uploaded_file(
        self,
        file: UploadFile,
        db: Session,
        max_errors: int = DEFAULT_MAX_ERRORS,
        log_format: str = "auto"
    ) -> models.Analysis:
        """
        Complete workflow: save file, analyze, store results.

        Args:
            file: Uploaded log file
            db: Database session
            max_errors: Maximum errors to collect
            log_format: Log format (currently only 'auto' supported)

        Returns:
            models.Analysis: Created analysis record

        Raises:
            ValueError: If log format cannot be detected or file is invalid
        """
        logger.info(f"Processing uploaded file: {file.filename} (format={log_format})")

        # Save uploaded file
        file_path = await self.save_uploaded_file(file)

        try:
            # Analyze the file
            result = self.analyze_file(file_path, max_errors=max_errors)

            # Convert to dict
            analysis_data = self.analysis_result_to_dict(
                result,
                file_path,
                file.filename
            )

            # Store in database
            analysis = crud.create_analysis(db, analysis_data)
            logger.info(f"Created analysis record: {analysis.id} for {file.filename}")

            return analysis

        except ValueError as e:
            logger.error(f"Analysis failed for {file.filename}: {e}")
            # Clean up file if analysis fails
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up file: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error analyzing {file.filename}: {e}", exc_info=True)
            # Clean up file if analysis fails
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up file: {file_path}")
            raise

    def delete_file(self, file_path: str) -> bool:
        """
        Delete a log file from disk.

        Args:
            file_path: Path to file

        Returns:
            bool: True if deleted, False if file doesn't exist
        """
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Deleted file: {file_path}")
                return True
            except OSError as e:
                logger.error(f"Failed to delete file {file_path}: {e}")
                raise
        else:
            logger.warning(f"File not found for deletion: {file_path}")
            return False
