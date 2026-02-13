"""
Real-time log streaming endpoints.
"""
import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/realtime", tags=["realtime"])


class ConnectionManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # Clean up dead connections
        for conn in dead_connections:
            self.active_connections.remove(conn)


manager = ConnectionManager()


@router.websocket("/ws/logs/tail")
async def websocket_tail_logs(websocket: WebSocket):
    """
    WebSocket endpoint for tailing log files in real-time.

    Client sends: {"file": "path/to/file.log", "lines": 50}
    Server streams: new log lines as they appear
    """
    await manager.connect(websocket)

    try:
        # Receive initial request
        data = await websocket.receive_json()
        file_path = data.get("file")
        lines = data.get("lines", 50)

        if not file_path:
            await websocket.send_json({"error": "file parameter required"})
            return

        # Tail the file
        async for line in tail_file(file_path, lines):
            await websocket.send_json({
                "type": "log_line",
                "timestamp": datetime.utcnow().isoformat(),
                "line": line
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        await websocket.send_json({"error": str(e)})


@router.get("/stream/errors")
async def stream_errors():
    """
    Server-Sent Events endpoint for streaming errors in real-time.

    Usage:
      const eventSource = new EventSource('/realtime/stream/errors');
      eventSource.onmessage = (e) => console.log(JSON.parse(e.data));
    """
    async def generate():
        while True:
            # Check for new errors (poll database/cache)
            errors = await get_recent_errors()

            for error in errors:
                yield f"data: {json.dumps(error)}\n\n"

            await asyncio.sleep(2)  # Poll every 2 seconds

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get("/tail/{file_id}")
async def tail_log_file(file_id: str, lines: int = 100):
    """
    REST endpoint to tail a log file.

    Returns the last N lines and continues streaming new lines.
    """
    async def generate():
        async for line in tail_file(file_id, lines):
            yield f"data: {json.dumps({'line': line})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


# Helper functions

async def tail_file(file_path: str, lines: int = 50) -> AsyncGenerator[str, None]:
    """
    Async generator to tail a file (like `tail -f`).

    Yields new lines as they appear in the file.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            yield f"Error: File not found: {file_path}"
            return

        # Read last N lines initially
        with open(path) as f:
            # Simple approach: read all and take last N
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                yield line.strip()

        # Continue watching for new lines
        with open(path) as f:
            # Seek to end
            f.seek(0, 2)

            while True:
                line = f.readline()
                if line:
                    yield line.strip()
                else:
                    await asyncio.sleep(0.5)  # Wait for new data

    except Exception as e:
        yield f"Error tailing file: {str(e)}"


async def get_recent_errors() -> list[dict]:
    """
    Get recent errors from the database or cache.

    This is a placeholder - implement based on your storage backend.
    """
    # TODO: Query actual error store
    # For now, return empty list
    return []
