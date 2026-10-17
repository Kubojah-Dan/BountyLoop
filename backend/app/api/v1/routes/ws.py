"""BountyLoop — Real-Time WebSocket Endpoints.

Provides live streaming updates of donation state transitions, review events,
and claims for operator dashboards and connected clients.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/donations")
async def websocket_donations(websocket: WebSocket) -> None:
    """Live WebSocket feed for donation lifecycle events."""
    await ws_manager.connect(websocket)
    try:
        # Send initial confirmation event
        await websocket.send_json({"event": "connected", "msg": "Subscribed to live donation feed"})
        while True:
            # Keep connection open; clients may optionally send heartbeat pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket exception: %s", exc)
        ws_manager.disconnect(websocket)
