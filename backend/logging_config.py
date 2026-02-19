"""
Centralized JSON logging configuration for the backend.

Provides a JSONFormatter that outputs valid JSON log lines and a
setup_logging() helper to wire it into the root logger.
"""

import json
import logging
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Logging formatter that outputs each record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge optional structured extras when provided by callers.
        for key in (
            "request_id",
            "method",
            "path",
            "status",
            "duration_ms",
            "client_ip",
            "user_agent",
            "event",
            "error",
        ):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger with the JSON formatter.

    Call once at application startup.  All loggers obtained via
    ``logging.getLogger(name)`` will inherit this configuration.
    """
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid adding duplicate handlers when called more than once (e.g. tests).
    if any(isinstance(h.formatter, JSONFormatter) for h in root.handlers):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    root.addHandler(handler)
