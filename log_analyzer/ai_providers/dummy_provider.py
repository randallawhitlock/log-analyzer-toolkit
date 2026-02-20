"""
Dummy AI Provider for demonstration and testing purposes.

Requires no API keys or local services to run.
"""

import json
import logging
import random
import time
from typing import Dict, Any, List

from .base import AIProvider, AIError, AIResponse

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

    def analyze(self, prompt: str, system_prompt: str = None) -> AIResponse:
        """
        Simulate an AI analysis by returning a hardcoded payload.

        Args:
            prompt: The user prompt containing log context
            system_prompt: Optional system instruction

        Returns:
            AIResponse simulating the expected Log Analyzer output
        """
        # Simulate network latency and "thinking" time
        logger.info(f"DummyProvider processing request (prompt length: {len(prompt)})")
        latency_seconds = random.uniform(1.0, 2.5)
        time.sleep(latency_seconds)

        # Check if this is a deep dive
        if "deep-dive analysis" in prompt or "deep dive" in prompt.lower():
            content = self._generate_deep_dive_response()
        else:
            content = self._generate_triage_response()
            
        return AIResponse(
            content=content,
            model=self.model,
            provider="dummy",
            latency_ms=latency_seconds * 1000
        )

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
                    "evidence": [
                        "ERROR: sqlalchemy.exc.TimeoutError: QueuePool limit of size 5 overflow 10 reached",
                        "WARNING: Connection pool nearing capacity (14/15 active)",
                        "Correlated with traffic spike at 14:30-14:45 UTC"
                    ]
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
                    "evidence": [
                        "GET /favicon.ico HTTP/1.1 404 153",
                        "GET /assets/legacy-style.css HTTP/1.1 404 162"
                    ]
                }
            ]
        }
        return json.dumps(response, indent=2)
        
    def _generate_deep_dive_response(self) -> str:
        """Generate a realistic markdown deep dive response (matches real AI provider output)."""
        return """## Root Cause Analysis

Upon deeper inspection, the connection pool exhaustion is specifically tied to the `GET /api/v1/reports` endpoint performing **full table scans** on the `reports` table without proper indexing.

**Evidence:**
- Slow query logs show average query times of **4.2 seconds** immediately before the pool timeouts
- Once all 15 connections are locked waiting for the slow query, all unrelated API paths begin failing instantly
- The `reports` table contains ~2.3M rows with no index on `tenant_id` or `created_at`

## Agentic Resolution Plan

1. **Add compound index** on `reports(tenant_id, created_at DESC)` — this covers the most common query pattern
2. **Implement pagination** — cap the endpoint at 50 rows per request (currently unbounded, returning up to 5,000)
3. **Add circuit breaker** — fail fast after 3 consecutive pool exhaustion errors
4. **Connection pool tuning** — increase `pool_size` from 5 to 20 and `max_overflow` from 10 to 30

```sql
CREATE INDEX CONCURRENTLY idx_reports_tenant_created
ON reports (tenant_id, created_at DESC);
```

## Verification Steps

1. Run `EXPLAIN ANALYZE` on the reports query before and after indexing
2. Load test with 50 concurrent users hitting `/api/v1/reports`
3. Monitor connection pool metrics via `/health` endpoint
4. Verify no 503 errors in the next 24-hour window

## Prevention Strategies

- **Alerting**: Set up alerts for connection pool utilization > 80%
- **Query review**: All new queries must include `EXPLAIN ANALYZE` output in PR
- **Load testing**: Add `/api/v1/reports` to the CI load test suite
- **Connection pooling**: Use PgBouncer in production for connection multiplexing

## Related Issues

- The `Missing Static Assets (404s)` issue may be masking additional 503 errors — users seeing a broken page may not realize the backend is also degraded
- Consider auditing all endpoints for unbounded `SELECT` queries"""

