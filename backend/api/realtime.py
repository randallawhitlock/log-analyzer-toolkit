"""
Real-time log streaming endpoints using WebSockets and Watchdog.

Provides two modes:
- Tail mode: watches a file for appends (classic tail -f)
- Replay mode: streams an uploaded log file line-by-line at configurable speed,
  with each line parsed through the detected format parser for structured display.
"""

import asyncio
import contextlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from backend.constants import UPLOAD_DIRECTORY
from backend.db import crud
from backend.db.database import SessionLocal
from log_analyzer.analyzer import AVAILABLE_PARSERS
from log_analyzer.parsers import UniversalFallbackParser

router = APIRouter(prefix="/realtime", tags=["realtime"])
logger = logging.getLogger(__name__)

# Resolve the allowed base directory for file reads
_ALLOWED_BASE_DIR = Path(UPLOAD_DIRECTORY).resolve()


class LogFileEventHandler(FileSystemEventHandler):
    """
    Watchdog event handler that triggers a callback when a specific file is modified.
    """

    def __init__(self, file_path: str, callback):
        self.file_path = str(Path(file_path).resolve())
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory and str(Path(event.src_path).resolve()) == self.file_path:
            self.callback()


class LogTailer:
    """
    Manages tailing of a single log file for a WebSocket connection.
    """

    def __init__(self, websocket: WebSocket, file_path: str, filter_regex: Optional[str] = None):
        self.websocket = websocket
        self.file_path = Path(file_path).resolve()
        # Validate filter regex to prevent ReDoS
        if filter_regex:
            try:
                re.compile(filter_regex)
            except re.error:
                filter_regex = None
        self.filter_pattern = re.compile(filter_regex) if filter_regex else None
        self.observer = None
        self._stop_event = asyncio.Event()
        self.last_pos = 0

    async def start(self):
        """Start tailing the file."""
        if not self.file_path.exists():
            await self.websocket.send_json({"error": f"File not found: {self.file_path}"})
            return

        # Send initial tail (last 50 lines)
        await self._send_initial_lines()

        # Set up watchdog observer
        loop = asyncio.get_running_loop()

        def on_file_modified():
            """Callback for watchdog thread to schedule async read."""
            asyncio.run_coroutine_threadsafe(self._process_new_lines(), loop)

        event_handler = LogFileEventHandler(str(self.file_path), on_file_modified)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.file_path.parent), recursive=False)
        self.observer.start()

        try:
            # Keep connection alive until client disconnects
            while not self._stop_event.is_set():
                await self.websocket.receive_text()  # Wait for any message (ping/close)
        except WebSocketDisconnect:
            pass
        finally:
            self.stop()

    def stop(self):
        """Stop the tailer and clean up."""
        self._stop_event.set()
        if self.observer:
            self.observer.stop()
            self.observer.join()

    async def _send_initial_lines(self, n: int = 50):
        """Read and send the last N lines of the file."""
        try:
            async with aiofiles.open(self.file_path) as f:
                # Move to end to get size
                await f.seek(0, 2)
                file_size = await f.tell()

                # Simple heuristic: Read last 8KB if file is large, or all if small
                read_size = min(file_size, 8192)
                if read_size > 0:
                    await f.seek(file_size - read_size)
                    content = await f.read()
                    lines = content.splitlines()
                    # Return last N lines
                    initial_lines = lines[-n:] if len(lines) > n else lines

                    for line in initial_lines:
                        await self._send_line(line)

                self.last_pos = await f.tell()
        except Exception as e:
            logger.error(f"Error reading initial lines: {e}")
            await self.websocket.send_json({"error": str(e)})

    async def _process_new_lines(self):
        """Read new data from file since last position."""
        try:
            async with aiofiles.open(self.file_path) as f:
                await f.seek(self.last_pos)
                new_content = await f.read()
                if new_content:
                    self.last_pos = await f.tell()
                    for line in new_content.splitlines():
                        await self._send_line(line)
        except Exception as e:
            logger.error(f"Error processing new lines: {e}")

    async def _send_line(self, line: str):
        """Send a line to the websocket if it matches the filter."""
        if not line.strip():
            return

        if self.filter_pattern and not self.filter_pattern.search(line):
            return

        try:
            await self.websocket.send_json({"timestamp": datetime.now(timezone.utc).isoformat(), "line": line})
        except Exception:
            # Connection likely closed
            self.stop()


@router.websocket("/ws/logs/tail")
async def websocket_tail_logs(
    websocket: WebSocket,
    analysis_id: str = Query(..., description="Analysis UUID to tail"),
    filter: Optional[str] = Query(None, description="Regex filter"),
):
    """
    WebSocket endpoint for real-time log tailing.

    Query Params:
    - analysis_id: UUID of the analysis (resolves file path via DB)
    - filter: Optional regex pattern to filter lines
    """
    await websocket.accept()

    # Resolve file path from analysis ID via database lookup
    db = SessionLocal()
    try:
        analysis = crud.get_analysis(db, analysis_id)
    finally:
        db.close()

    if not analysis:
        await websocket.send_json({"error": f"Analysis {analysis_id} not found"})
        await websocket.close()
        return

    file_path = analysis.file_path

    # Validate that the resolved file is within the allowed uploads directory
    resolved_path = Path(file_path).resolve()
    if not str(resolved_path).startswith(str(_ALLOWED_BASE_DIR)):
        await websocket.send_json({"error": "Access denied: file path is outside the allowed directory"})
        await websocket.close()
        return

    tailer = LogTailer(websocket, file_path, filter)
    await tailer.start()


def _resolve_parser(detected_format: str):
    """Find the parser instance matching a detected format name."""
    for parser in AVAILABLE_PARSERS:
        if parser.name == detected_format:
            return parser
    return UniversalFallbackParser()


def _parse_line(parser, line: str) -> dict:
    """Parse a single log line into a structured dict for the frontend."""
    entry = parser.parse(line)
    if entry:
        ts = None
        if entry.timestamp:
            try:
                ts = entry.timestamp.isoformat()
            except Exception:
                ts = str(entry.timestamp)
        return {
            "line": line,
            "level": entry.level or "INFO",
            "timestamp": ts,
            "message": entry.message or line,
            "source": entry.source,
            "parsed": True,
        }
    return {
        "line": line,
        "level": "INFO",
        "timestamp": None,
        "message": line,
        "source": None,
        "parsed": False,
    }


class LogReplayer:
    """
    Replays a log file line-by-line over a WebSocket connection at configurable speed.

    Supports commands from the client:
    - {"cmd": "play"}
    - {"cmd": "pause"}
    - {"cmd": "speed", "value": 1|2|5|10|0}  (0 = max speed, no delay)
    - {"cmd": "jump", "value": <line_number>}  (jump to a specific line)
    """

    # Speed multiplier → delay between lines in seconds
    SPEED_DELAYS = {
        1: 0.2,  # 5 lines/sec — readable pace
        2: 0.1,  # 10 lines/sec
        5: 0.04,  # 25 lines/sec
        10: 0.02,  # 50 lines/sec
        0: 0.0,  # max speed — no delay (batch of 50)
    }

    def __init__(self, websocket: WebSocket, file_path: str, parser, filter_regex: Optional[str] = None):
        self.websocket = websocket
        self.file_path = Path(file_path).resolve()
        self.parser = parser
        if filter_regex:
            try:
                self.filter_pattern = re.compile(filter_regex)
            except re.error:
                self.filter_pattern = None
        else:
            self.filter_pattern = None
        self._playing = True
        self._speed = 1
        self._stop = False
        self._current_line = 0
        self._jump_target = None

    async def start(self):
        """Start replaying the file."""
        if not self.file_path.exists():
            await self.websocket.send_json({"type": "error", "error": f"File not found: {self.file_path}"})
            return

        # Count total lines and send metadata
        total_lines = 0
        async with aiofiles.open(self.file_path, errors="replace") as f:
            async for _ in f:
                total_lines += 1

        await self.websocket.send_json(
            {
                "type": "meta",
                "total_lines": total_lines,
                "file": self.file_path.name,
            }
        )

        # Start command listener in background
        cmd_task = asyncio.create_task(self._listen_commands())

        try:
            await self._replay_lines(total_lines)
        finally:
            self._stop = True
            cmd_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await cmd_task

    async def _listen_commands(self):
        """Listen for client commands (play/pause/speed/jump)."""
        try:
            while not self._stop:
                raw = await self.websocket.receive_text()
                try:
                    msg = json.loads(raw)
                except (json.JSONDecodeError, ValueError):
                    continue

                cmd = msg.get("cmd")
                if cmd == "play":
                    self._playing = True
                elif cmd == "pause":
                    self._playing = False
                elif cmd == "speed":
                    val = msg.get("value", 1)
                    if val in self.SPEED_DELAYS:
                        self._speed = val
                elif cmd == "jump":
                    val = msg.get("value", 0)
                    if isinstance(val, int) and val >= 0:
                        self._jump_target = val
                        self._playing = True
        except (WebSocketDisconnect, Exception):
            self._stop = True

    async def _replay_lines(self, total_lines: int):
        """Read and stream the file line by line."""
        async with aiofiles.open(self.file_path, errors="replace") as f:
            line_num = 0
            async for raw_line in f:
                if self._stop:
                    return

                # Handle jump: skip lines until we reach the target
                if self._jump_target is not None:
                    if line_num < self._jump_target:
                        line_num += 1
                        continue
                    self._jump_target = None

                # Wait while paused
                while not self._playing and not self._stop:
                    await asyncio.sleep(0.1)
                    # Check for jump while paused
                    if self._jump_target is not None:
                        break

                if self._stop:
                    return

                # If jump was requested while paused, restart from the top
                if self._jump_target is not None:
                    # We need to restart the file read — send a signal and break
                    break

                line = raw_line.rstrip("\n\r")
                if not line.strip():
                    line_num += 1
                    continue

                # Apply filter
                if self.filter_pattern and not self.filter_pattern.search(line):
                    line_num += 1
                    continue

                # Parse and send
                parsed = _parse_line(self.parser, line)
                parsed["line_num"] = line_num
                parsed["progress"] = line_num / max(total_lines, 1)
                parsed["type"] = "log"

                try:
                    await self.websocket.send_json(parsed)
                except Exception:
                    self._stop = True
                    return

                line_num += 1
                self._current_line = line_num

                # Apply speed delay
                delay = self.SPEED_DELAYS.get(self._speed, 0.2)
                if delay > 0:
                    await asyncio.sleep(delay)
                elif line_num % 50 == 0:
                    # Max speed: yield every 50 lines to keep the event loop responsive
                    await asyncio.sleep(0)

        # If we broke out for a jump, restart
        if self._jump_target is not None:
            await self._replay_lines(total_lines)
            return

        # Send completion
        with contextlib.suppress(Exception):
            await self.websocket.send_json(
                {
                    "type": "complete",
                    "total_lines": total_lines,
                }
            )


@router.websocket("/ws/logs/replay")
async def websocket_replay_logs(
    websocket: WebSocket,
    analysis_id: str = Query(..., description="Analysis UUID to replay"),
    filter: Optional[str] = Query(None, description="Regex filter"),
):
    """
    WebSocket endpoint for replaying a log file with parsed, structured output.

    Streams the uploaded log line-by-line at configurable speed.
    Each line is parsed through the detected format parser.

    Client can send JSON commands:
    - {"cmd": "play"}
    - {"cmd": "pause"}
    - {"cmd": "speed", "value": 1|2|5|10|0}
    - {"cmd": "jump", "value": <line_number>}
    """
    await websocket.accept()

    # Resolve file path and format from analysis
    db = SessionLocal()
    try:
        analysis = crud.get_analysis(db, analysis_id)
    finally:
        db.close()

    if not analysis:
        await websocket.send_json({"type": "error", "error": f"Analysis {analysis_id} not found"})
        await websocket.close()
        return

    file_path = analysis.file_path
    resolved_path = Path(file_path).resolve()
    if not str(resolved_path).startswith(str(_ALLOWED_BASE_DIR)):
        await websocket.send_json({"type": "error", "error": "Access denied: file outside allowed directory"})
        await websocket.close()
        return

    parser = _resolve_parser(analysis.detected_format)
    replayer = LogReplayer(websocket, file_path, parser, filter)
    await replayer.start()
