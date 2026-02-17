"""
Real-time log streaming endpoints using WebSockets and Watchdog.
"""

import asyncio
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
    file: str = Query(..., description="Path to log file"),
    filter: Optional[str] = Query(None, description="Regex filter"),
):
    """
    WebSocket endpoint for real-time log tailing.

    Query Params:
    - file: Path to log file (must be within the uploads directory)
    - filter: Optional regex pattern to filter lines
    """
    await websocket.accept()

    # Validate that the requested file is within the allowed uploads directory
    resolved_path = Path(file).resolve()
    if not str(resolved_path).startswith(str(_ALLOWED_BASE_DIR)):
        await websocket.send_json({"error": "Access denied: file path is outside the allowed directory"})
        await websocket.close()
        return

    tailer = LogTailer(websocket, file, filter)
    await tailer.start()
