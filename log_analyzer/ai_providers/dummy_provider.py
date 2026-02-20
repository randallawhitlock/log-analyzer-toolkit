"""
Dummy AI Provider for demonstration and testing purposes.

Requires no API keys or local services to run.
"""

import json
import logging
import random
import time
from typing import Dict, Any, List

from .base import AIProvider, AIError

logger = logging.getLogger(__name__)


class DummyProvider(AIProvider):
    """
    Dummy AI provider that returns simulated responses.
    Useful for testing the UI without burning API credits.
    """

    default_model = "dummy-demomodel-v1"

    def __init__(self, model: str = None, **kwargs):
        """Initialize dummy provider."""
        self.model = model or self.default_model
        logger.debug(f"Initialized DummyProvider (model={self.model})")

    def is_available(self) -> bool:
        """Dummy provider is always available."""
        return True

    def get_model(self) -> str:
        """Get the current model name."""
        return self.model

    def analyze(self, prompt: str, system_prompt: str = None) -> str:
        """
        Simulate an AI analysis by returning a hardcoded payload.

        Args:
            prompt: The user prompt containing log context
            system_prompt: Optional system instruction

        Returns:
            JSON string simulating the expected Log Analyzer output
        """
        # Simulate network latency and "thinking" time
        logger.info(f"DummyProvider processing request (prompt length: {len(prompt)})")
        time.sleep(random.uniform(1.0, 2.5))

        # Check if this is a deep dive
        if "deep-dive analysis" in prompt or "deep dive" in prompt.lower():
            return self._generate_deep_dive_response()
            
        return self._generate_triage_response()

    def _generate_triage_response(self) -> str:
        """Generate a realistic JSON triage response."""
        response = {
            "summary": "This is a simulated analysis from the Demo Provider. The uploaded logs show a pattern of client-side request failures (404s) alongside a backend database connection timeout. The system appears to be under intermittent load causing the connection pool to exhaust.",
            "overall_severity": "ERROR",
            "confidence": 0.92,
            "issues": [
                {
                    "title": "Database Connection Pool Exhaustion",
                    "severity": "CRITICAL",
                    "confidence": 0.95,
                    "description": "Multiple requests failed with 'Connection pool exhausted' errors originating from the worker nodes. This indicates the backend cannot keep up with the incoming request volume or queries are taking too long.",
                    "affected_components": ["PostgreSQL Database", "API Worker Nodes"],
                    "recommendation": "1. Increase the maximum connection pool size. 2. Investigate long-running queries in the database.",
                    "root_cause_analysis": "The system experienced a burst of traffic which exhausted the available database connections, causing cascading failures for subsequent requests.",
                    "category": "performance",
                    "evidence": "ERROR: sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached"
                },
                {
                    "title": "Missing Static Assets (404s)",
                    "severity": "WARNING",
                    "confidence": 0.99,
                    "description": "Numerous requests for /favicon.ico and /assets/legacy-style.css returned 404 Not Found.",
                    "affected_components": ["Nginx Web Server", "Frontend Client"],
                    "recommendation": "Ensure all required static assets are correctly built and deployed to the CDN or web server root.",
                    "root_cause_analysis": "Likely a deployment artifact issue where some static files were not copied over during the last CI/CD run.",
                    "category": "configuration",
                    "evidence": "GET /favicon.ico HTTP/1.1 404 153"
                }
            ]
        }
        return json.dumps(response, indent=2)
        
    def _generate_deep_dive_response(self) -> str:
        """Generate a realistic JSON deep dive response."""
        response = {
            "detailed_analysis": "Upon deeper simulated inspection, the connection pool exhaustion is specifically tied to the `GET /api/v1/reports` endpoint doing full table scans. \n\n1. **Query Inspection**: The logs indicate slow query times averaging 4.2 seconds right before the timeouts.\n2. **Resource Starvation**: Once all 15 connections in the pool are locked waiting for the slow query to return, all entirely unrelated API paths start failing instantly.\n\n### Resolution Steps\n- Add a compound index on the `reports` table covering `tenant_id` and `created_at`.\n- Implement pagination on the endpoint to limit the max rows returned from 5000 to 50.\n- Implement a circuit breaker pattern in the application tier to fail fast.",
            "root_cause": "Unindexed database query on a high-traffic reporting endpoint causing connection starvation."
        }
        return json.dumps(response, indent=2)
