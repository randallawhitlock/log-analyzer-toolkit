# User Stories & Acceptance Criteria — Log Analyzer Toolkit

## Context

The Log Analyzer Toolkit is a full-stack application with three surfaces: a **CLI tool** (Python/Click), a **REST API** (FastAPI), and a **Vue.js frontend**. This document defines comprehensive user stories with acceptance criteria to serve as a living backlog. Stories are organized by epic and cover happy paths, edge cases, error handling, and security.

---

## Epic 1: File Upload & Analysis

### US-1.1: Upload a log file via the web UI
**As a** user, **I want to** upload a log file through drag-and-drop or file picker **so that** I can get it analyzed automatically.

**Acceptance Criteria:**
- [ ] Drag-and-drop onto the drop zone triggers upload
- [ ] File picker opens when "Choose File" is clicked and accepts `.log`, `.txt`, `.json`
- [ ] Progress indicator shows during upload/analysis
- [ ] On success, user is redirected to the analysis detail view
- [ ] File size limit (100 MB) is enforced client-side AND server-side
- [ ] Files exceeding 100 MB show a clear error message (not a generic 413)

### US-1.2: Upload a log file via the API
**As an** API consumer, **I want to** POST a log file to `/api/v1/analyze` **so that** I can integrate analysis into my automation.

**Acceptance Criteria:**
- [ ] `POST /api/v1/analyze` with `multipart/form-data` returns 201 (sync) or 202 (async)
- [ ] `?sync=true` returns completed analysis inline
- [ ] `?sync=false` (default) returns a pending record with `detected_format="pending"`
- [ ] `?max_errors=N` is respected (range 1–1000)
- [ ] Missing file field returns 422 with descriptive validation error
- [ ] Malformed multipart body returns 422 (not 500)
- [ ] Files > 100 MB return 413 with `"File too large. Maximum size is 100MB"`

### US-1.3: Handle the "422 Unprocessable Entity" upload error
**As a** user, **I want to** see a clear, actionable error when my upload fails with 422 **so that** I know how to fix it.

**Acceptance Criteria:**
- [ ] Frontend catches 422 responses and displays the specific validation error (e.g., "No file provided", "Invalid file type")
- [ ] The raw FastAPI validation detail (`{"detail": [{"loc":..., "msg":...}]}`) is parsed into a human-readable message
- [ ] The error is dismissible and the upload zone resets to accept a new file
- [ ] Binary/non-text files that slip past client validation produce a meaningful error (not a raw stack trace)

### US-1.4: Upload unsupported or malformed files gracefully
**As a** user, **I want** the system to handle garbage input without crashing **so that** I don't lose trust in the tool.

**Acceptance Criteria:**
- [ ] Binary files (images, executables) return an analysis with 0 parsed lines and fallback format, not a 500 error
- [ ] Empty files (0 bytes) return an analysis with `total_lines=0` and appropriate messaging
- [ ] Files with mixed encodings (UTF-8 + Latin-1) are handled via `errors="replace"` — no UnicodeDecodeError
- [ ] Very long lines (>1 MB single line) don't cause OOM — the parser handles them gracefully

### US-1.5: Analyze a log file via the CLI
**As a** developer, **I want to** run `log-analyzer analyze myfile.log` from my terminal **so that** I can quickly inspect logs without a browser.

**Acceptance Criteria:**
- [ ] `log-analyzer analyze <file>` auto-detects format and prints a Rich-formatted summary
- [ ] `--format` flag allows explicit format selection (`apache_access`, `nginx_access`, `json`, `syslog`, etc.)
- [ ] `--max-errors N` limits the error list
- [ ] `--workers N` and `--no-threading` control parallelism
- [ ] `--report markdown|html|csv|json` generates a report
- [ ] `--output file.md` writes report to file instead of stdout
- [ ] `--enable-analytics --time-bucket 1h` shows time-series analytics
- [ ] Progress bar displays during analysis and handles Ctrl+C cleanly (exit code 130)
- [ ] Non-existent file paths print a clear error and exit code 1

---

## Epic 2: Analysis Results & Viewing

### US-2.1: View analysis results in the web UI
**As a** user, **I want to** see a dashboard with key metrics after uploading a file **so that** I can quickly understand the health of my system.

**Acceptance Criteria:**
- [ ] Dashboard shows: total lines, parse rate, error rate, time span
- [ ] Level breakdown chart renders with correct proportions
- [ ] Top errors list shows up to 10 entries with counts
- [ ] HTTP status codes section appears only for access logs (when `status_codes` is non-empty)
- [ ] Timestamps display in the user's local timezone
- [ ] "Pending" analyses show a loading/polling state until background processing completes

### US-2.2: Preview raw log lines
**As a** user, **I want to** see a sample of the raw log file **so that** I can verify the system parsed it correctly.

**Acceptance Criteria:**
- [ ] "Log Sample Preview" section is collapsible (default: collapsed)
- [ ] Clicking "Show" fetches up to 50 lines via `GET /api/v1/analysis/{id}/preview`
- [ ] Line numbers are displayed
- [ ] If the file has been deleted from disk, a clear "file no longer available" message appears (not 500)
- [ ] Encoding issues are handled gracefully (replacement characters, not crashes)

### US-2.3: List and search past analyses
**As a** user, **I want to** browse all my past analyses **so that** I can revisit previous results.

**Acceptance Criteria:**
- [ ] `/analyses` page shows a table with: filename, format, lines, parse rate, error rate, date
- [ ] Pagination works (Previous/Next buttons, page indicator)
- [ ] Search by filename filters results in real-time (debounced)
- [ ] Format dropdown filters by detected format
- [ ] "Errors only" checkbox filters to analyses with error_rate > 0
- [ ] Each row links to the analysis detail view
- [ ] Empty state shows "No analyses yet" with an upload CTA

### US-2.4: Delete an analysis
**As a** user, **I want to** delete an analysis I no longer need **so that** I can keep my workspace clean.

**Acceptance Criteria:**
- [ ] Delete button on analysis detail page removes the analysis
- [ ] Confirmation dialog before deletion (currently missing — should be added)
- [ ] Associated file is deleted from disk
- [ ] Associated triages are cascade-deleted
- [ ] User is redirected to home/analyses list after deletion
- [ ] Deleting a non-existent analysis returns 404

### US-2.5: Export analysis as JSON
**As a** user, **I want to** export analysis results as JSON **so that** I can share or archive them.

**Acceptance Criteria:**
- [ ] "Export" button on analysis detail page triggers a JSON file download
- [ ] Downloaded JSON contains all analysis fields (levels, errors, sources, timestamps, status codes)
- [ ] Filename follows pattern `analysis-{filename}-{date}.json`

---

## Epic 3: AI Triage & Deep Dive

### US-3.1: Run AI triage on an analysis
**As a** user, **I want to** run AI-powered triage on my log analysis **so that** I get intelligent issue classification and recommendations.

**Acceptance Criteria:**
- [ ] "Run AI Triage" button sends `POST /api/v1/triage` with the analysis ID
- [ ] Loading spinner shows during the AI call
- [ ] Results display: overall severity badge, confidence %, summary, and issues list
- [ ] Each issue shows: severity, category, title, description, root cause analysis, evidence, recommendation
- [ ] Previously-run triages are loaded automatically when viewing an analysis
- [ ] Provider is auto-selected from available providers (Anthropic > Gemini > Ollama)
- [ ] Rate limit (10/minute) is respected; 429 shows a "please wait" message

### US-3.2: Run deep-dive on a specific issue
**As a** user, **I want to** get a detailed AI analysis of a specific triage issue **so that** I get actionable remediation steps.

**Acceptance Criteria:**
- [ ] "Deep Dive" button appears on each triage issue card
- [ ] Sends `POST /api/v1/triage/deep-dive` with issue context
- [ ] Loading state per-issue (not global)
- [ ] Result panel shows: detailed markdown analysis, provider used, model, analysis time
- [ ] Deep dive includes: root cause, resolution plan, verification steps, prevention strategies

### US-3.3: Handle AI provider unavailability
**As a** user, **I want** clear feedback when no AI provider is available **so that** I know what to configure.

**Acceptance Criteria:**
- [ ] 503 response displays "No AI provider available. Configure ANTHROPIC_API_KEY, GOOGLE_API_KEY, or start Ollama."
- [ ] Error message includes links to setup instructions
- [ ] The triage button is not disabled preemptively (user may have Ollama running)
- [ ] Rate limit 429 errors show remaining wait time

---

## Epic 4: Real-Time Log Viewing (WebSocket)

### US-4.1: Replay a log file in the viewer
**As a** user, **I want to** replay a log file line-by-line at configurable speed **so that** I can observe the sequence of events.

**Acceptance Criteria:**
- [ ] Replay mode streams parsed log lines via WebSocket
- [ ] Play/Pause button works correctly
- [ ] Speed selector (1x, 2x, 5x, 10x, Max) adjusts playback rate
- [ ] Progress bar shows current position
- [ ] Line counter shows current/total lines
- [ ] "Complete" status shows when replay finishes
- [ ] Auto-scroll keeps the view at the bottom (toggleable)
- [ ] Buffer is bounded at 2000 lines (older lines trimmed)

### US-4.2: Live tail a log file
**As a** user, **I want to** watch a log file for new lines in real-time **so that** I can monitor live systems.

**Acceptance Criteria:**
- [ ] Tail mode uses Watchdog to detect file changes
- [ ] New lines appear in the viewer as they're appended
- [ ] Status badge shows "Live" when connected
- [ ] Disconnection is handled gracefully with a "Disconnected" status

### US-4.3: Filter log viewer output
**As a** user, **I want to** filter log lines by level and regex **so that** I can focus on relevant events.

**Acceptance Criteria:**
- [ ] Level filter buttons (CRITICAL, ERROR, WARNING, INFO, DEBUG) toggle visibility
- [ ] Regex filter input applies server-side filtering
- [ ] Invalid regex patterns are handled gracefully (no crash, silently ignored)
- [ ] Switching between Replay and Tail modes clears the buffer and reconnects
- [ ] Clear button empties the display

---

## Epic 5: Log Format Parsing

### US-5.1: Auto-detect log format
**As a** user, **I want** the system to automatically detect the log format **so that** I don't have to specify it manually.

**Acceptance Criteria:**
- [ ] Format detection samples the first N lines and tests all registered parsers
- [ ] Detection order: cloud (AWS/GCP/Azure) → container (Docker/K8s/containerd) → standard (Apache/nginx/JSON/syslog) → fallback
- [ ] Detected format name is shown on the analysis detail page
- [ ] If no format matches, `UniversalFallbackParser` is used (when `use_fallback=True`)

### US-5.2: Parse all supported formats correctly
**As a** user, **I want** each format parsed with high fidelity **so that** severity, timestamps, and sources are extracted accurately.

**Acceptance Criteria:**
- [ ] **Apache Access** — parses IP, timestamp, method, path, status code, bytes, user agent
- [ ] **Apache Error** — parses timestamp, severity, message, client IP
- [ ] **Nginx Access** — similar to Apache access with nginx-specific fields
- [ ] **JSON** — parses structured JSON log lines with configurable field mapping
- [ ] **Syslog** — parses RFC 3164/5424 format with facility, severity, hostname, process
- [ ] **AWS CloudWatch** — handles JSON batch and plain text, extracts logGroup/logStream
- [ ] **GCP Cloud Logging** — requires severity + timestamp, extracts resource labels
- [ ] **Azure Monitor** — handles string/numeric severity levels, category, operationName
- [ ] **Docker JSON** — parses log/stream/time fields, stderr→WARNING default
- [ ] **Kubernetes CRI** — parses TIMESTAMP STREAM FLAG MSG format, handles F/P flags
- [ ] **containerd** — CRI with JSON payloads, component extraction
- [ ] Each parser has tests using real public log samples (not synthetic)
- [ ] RFC3339Nano timestamps with nanoseconds are truncated to microseconds correctly

### US-5.3: View supported formats
**As a** user, **I want to** see which log formats are supported **so that** I know if my logs will be parsed correctly.

**Acceptance Criteria:**
- [ ] Upload page shows a grid of supported formats with names and descriptions
- [ ] `GET /api/v1/formats` returns the full list with descriptions
- [ ] CLI `--format` help text lists available formats

---

## Epic 6: Authentication & Security

### US-6.1: Protect API with an API key
**As an** admin, **I want to** require an API key for API access **so that** unauthorized users can't use the service.

**Acceptance Criteria:**
- [ ] When `LOG_ANALYZER_API_KEY` is set, all `/api/v1/*` routes require `X-API-Key` header
- [ ] Invalid or missing key returns 403 with `"Could not validate credentials"`
- [ ] `/health` and `/` endpoints remain public (no auth required)
- [ ] Frontend sends `X-API-Key` from `VITE_API_KEY` env var when configured

### US-6.2: Secure WebSocket endpoints
**As an** admin, **I want** WebSocket endpoints to respect authentication **so that** unauthenticated users can't stream log data.

**Acceptance Criteria:**
- [x] **RESOLVED (04a42b0)**: `/realtime/ws/*` endpoints currently have NO authentication — they need to be secured
- [x] WebSocket connections should validate API key via query param or initial message
- [x] Unauthenticated WebSocket connections are rejected

### US-6.3: Prevent path traversal attacks
**As an** admin, **I want** the system to block directory traversal attempts **so that** attackers can't read arbitrary files.

**Acceptance Criteria:**
- [ ] WebSocket endpoints validate file paths are within the uploads directory
- [ ] Path traversal patterns (`../../etc/passwd`) are rejected with "Access denied"
- [ ] Uploaded filenames are sanitized (UUID-based, only alnum extensions)

### US-6.4: Enforce rate limiting
**As an** admin, **I want** rate limiting on all endpoints **so that** the service isn't overwhelmed.

**Acceptance Criteria:**
- [ ] Default rate limit: 60 requests/minute per IP
- [ ] Triage endpoints: 10 requests/minute per IP
- [ ] 429 responses include `Retry-After` header
- [ ] Rate limits are configurable via `RATE_LIMIT_DEFAULT` env var

---

## Epic 7: Background Processing & Async Analysis

### US-7.1: Process large files asynchronously
**As a** user, **I want** large file analysis to run in the background **so that** I don't have to wait for the upload response.

**Acceptance Criteria:**
- [ ] Default (async) upload returns 202 immediately with a pending record
- [ ] Background processing updates the record in-place when complete
- [ ] Failed background analysis sets `detected_format="failed"` with error info

### US-7.2: Poll for analysis completion
**As a** user, **I want to** know when my background analysis is done **so that** I can view the results.

**Acceptance Criteria:**
- [x] **RESOLVED (66b1705)**: Frontend needs a polling mechanism to detect when `detected_format` changes from `"pending"` to a real format
- [x] Analysis detail page should poll `GET /api/v1/analysis/{id}` every few seconds while status is "pending"
- [x] Transition from "pending" to "complete" triggers a UI refresh
- [ ] Transition from "pending" to "failed" shows an error state

### US-7.3: Clean up orphaned files
**As an** admin, **I want** failed background analyses to clean up their uploaded files **so that** disk space isn't wasted.

**Acceptance Criteria:**
- [x] **RESOLVED (a3898ea)**: Background processing failure currently leaves the file on disk — it should be cleaned up
- [x] A periodic cleanup job or cleanup-on-read mechanism removes orphaned files

---

## Epic 8: Configuration & Deployment

### US-8.1: Configure the application via environment variables
**As an** admin, **I want to** configure all settings via env vars **so that** I can deploy in different environments.

**Acceptance Criteria:**
- [ ] All settings in `backend/config.py` are overridable via env vars
- [ ] `DATABASE_URL` switches between SQLite (dev) and PostgreSQL (prod)
- [ ] `CORS_ORIGINS` controls allowed frontend origins
- [ ] `MAX_UPLOAD_SIZE_MB` adjusts the upload limit
- [ ] `LOG_ANALYZER_API_KEY` enables/disables authentication
- [ ] Missing optional vars fall back to sensible defaults

### US-8.2: Run the full stack with Docker
**As a** developer, **I want to** `docker compose up` to run the entire stack **so that** I can get started quickly.

**Acceptance Criteria:**
- [ ] Docker Compose starts: backend API, frontend, PostgreSQL
- [ ] Environment variables are passed through `.env`
- [ ] Upload directory is persisted via a volume
- [ ] Health check endpoint is used for container readiness

### US-8.3: Run CI checks on every PR
**As a** developer, **I want** automated linting and testing on every PR **so that** regressions are caught early.

**Acceptance Criteria:**
- [ ] `backend-lint` job runs Ruff on Python code
- [ ] `backend-test` job runs pytest on Python 3.10 and 3.11
- [ ] `frontend-build` job builds the Vue app with Node 22
- [x] **RESOLVED (7896377)**: No frontend lint/test job exists — should add ESLint and Vitest

---

## Epic 9: Reporting & Export

### US-9.1: Generate reports in multiple formats
**As a** user, **I want to** export analysis results as Markdown, HTML, CSV, or JSON **so that** I can share findings with my team.

**Acceptance Criteria:**
- [ ] CLI `--report markdown --output report.md` generates a Markdown report
- [ ] CLI `--report html --output report.html` generates a standalone HTML report
- [ ] CLI `--report csv --output report.csv` exports key metrics as CSV
- [ ] CLI `--report json --output report.json` exports full analysis as JSON
- [ ] Without `--output`, report prints to stdout

---

## Epic 10: Error Handling & Resilience

### US-10.1: Handle large file uploads without OOM
**As a** user, **I want** the system to handle files up to 100 MB without running out of memory **so that** I can analyze large logs.

**Acceptance Criteria:**
- [x] **RESOLVED (04a42b0)**: Current implementation reads entire file into memory via `await file.read()` — should use streaming/chunked writes for large files
- [x] Memory usage stays bounded during upload and analysis
- [x] Counter pruning prevents memory spikes during analysis (already implemented)

### US-10.2: Handle Content-Length bypass
**As an** admin, **I want** the upload size limit enforced even without Content-Length header **so that** chunked transfers can't bypass the limit.

**Acceptance Criteria:**
- [x] **RESOLVED (04a42b0)**: `LimitUploadSize` middleware only checks when `content-length` header is present — chunked transfers bypass it
- [x] Server should also track bytes received during streaming and reject if limit exceeded

### US-10.3: Display meaningful error messages
**As a** user, **I want** all errors to show human-readable messages **so that** I can understand what went wrong.

**Acceptance Criteria:**
- [ ] 403 → "Invalid API key. Check your X-API-Key header."
- [ ] 404 → "Analysis not found" (with the ID)
- [ ] 413 → "File too large. Maximum size is 100MB."
- [ ] 422 → Parsed validation error (field name + message)
- [ ] 429 → "Rate limit exceeded. Please try again in X seconds."
- [ ] 500 → "An unexpected error occurred. Please try again."
- [ ] 503 → "AI provider unavailable. Configure an API key or start Ollama."

---

## Epic 11: Observability & Monitoring

### US-11.1: Structured JSON logging
**As an** admin, **I want** all requests logged as structured JSON **so that** I can ship them to a log aggregator.

**Acceptance Criteria:**
- [ ] Every request logs: timestamp, level, request_id, method, path, status, duration_ms
- [ ] `X-Request-ID` header is returned on every response
- [ ] 4xx errors log at WARNING level, 5xx at ERROR level
- [ ] AI triage calls log provider, model, and latency

---

## Resolved Bugs

| ID | Bug | Location | Epic | Resolution |
|----|-----|----------|------|------------|
| B1 | WebSocket endpoints have no authentication | `backend/realtime.py` | 6.2 | Resolved in `04a42b0` |
| B2 | Background processing failure doesn't clean up files | `analyzer_service.py:200-238` | 7.3 | Resolved in `a3898ea` |
| B3 | `LimitUploadSize` bypassed by chunked transfer | `backend/main.py:71-87` | 10.2 | Resolved in `04a42b0` |
| B4 | `await file.read()` loads entire file into memory | `analyzer_service.py:58` | 10.1 | Resolved in `04a42b0` |
| B5 | No frontend polling for async analysis completion | Frontend `AnalysisView.vue` | 7.2 | Resolved in `66b1705` |
| B6 | No delete confirmation dialog in UI | Frontend `AnalysisView.vue` | 2.4 | Resolved in `66b1705` |
| B7 | No AI call timeout — could hang indefinitely | `triage_service.py` deep_dive | 3.2 | Resolved in `a3898ea` |
| B8 | Frontend CI has no lint or test job | `.github/workflows/ci.yml` | 8.3 | Resolved in `7896377` |
