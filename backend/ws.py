"""
ws.py
WebSocket connection manager.
Maintains a set of active connections and broadcasts to all of them.
Used by the bot runner to push live price/RSI/signal updates.
"""
from __future__ import annotations
import asyncio
import json
import logging
from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe WebSocket broadcaster for FastAPI."""

    def __init__(self):
        """Initialise with empty connection list."""
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        """Accept a new WebSocket connection and register it."""
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        log.info(f"WebSocket connected. Total: {len(self._connections)}")

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection from the registry."""
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)
        log.info(f"WebSocket disconnected. Total: {len(self._connections)}")

    async def broadcast(self, data: dict) -> None:
        """Send a JSON message to every connected client. Silently drops dead connections."""
        message = json.dumps(data)
        dead: list[WebSocket] = []
        async with self._lock:
            targets = list(self._connections)
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws)


manager = ConnectionManager()
