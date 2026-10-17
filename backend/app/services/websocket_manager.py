"""BountyLoop — WebSocket Connection Manager.

Broadcasting real-time donation lifecycle events to connected dashboards and clients:
- donation_created
- donation_confirmed
- donation_cancelled
- review_needed
- review_resolved
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages active WebSocket connections and broadcasts events."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        """Accept incoming WebSocket connection and register."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket client connected. Active connections: %d",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Unregister closed connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                "WebSocket client disconnected. Remaining connections: %d",
                len(self.active_connections),
            )

    async def broadcast(self, event_type: str, data: dict[str, Any]) -> None:
        """Broadcast an event payload to all connected subscribers."""
        if not self.active_connections:
            return

        payload = {
            "event": event_type,
            "data": data,
        }
        message_text = json.dumps(payload, default=str)

        dead_connections: list[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message_text)
            except Exception as exc:
                logger.warning("Failed sending message to WebSocket client: %s", exc)
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


ws_manager = WebSocketManager()
