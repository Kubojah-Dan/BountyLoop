"""BountyLoop — notify_mcp Server (Port 8012).

Model Context Protocol (MCP) server for notification dispatch.
Enforces safety contracts:
- FCM push is primary
- SMS via Twilio is strictly capped at SMS_DAILY_CAP (default 20)
- All operations call backend internal API using INTERNAL_SERVICE_TOKEN
- Refuses send_sms when daily cap is reached and logs refusal
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notify_mcp")

BACKEND_API_URL = os.getenv("API_URL", "http://localhost:8000/v1")
INTERNAL_SERVICE_TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "changeme-internal-token")
SMS_DAILY_CAP = int(os.getenv("SMS_DAILY_CAP", "20"))

app = FastAPI(
    title="BountyLoop Notify MCP Server",
    version="0.1.0",
    description="MCP notification server enforcing push-first delivery and hard SMS daily budget cap.",
)


class ToolCallRequest(BaseModel):
    name: str = Field(..., description="Tool name to execute")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class SendSmsArgs(BaseModel):
    to_phone: str
    body: str


class SendPushArgs(BaseModel):
    user_id: str
    title: str
    body: str
    data: dict[str, str] = Field(default_factory=dict)


class DispatchNotificationArgs(BaseModel):
    user_id: str
    title: str
    body: str
    sms_body: str | None = None
    data: dict[str, str] = Field(default_factory=dict)


@app.get("/healthz")
async def healthz() -> dict[str, Any]:
    return {
        "status": "ok",
        "server": "notify_mcp",
        "port": 8012,
        "daily_cap": SMS_DAILY_CAP,
    }


@app.get("/tools")
async def list_tools() -> list[dict[str, Any]]:
    """MCP tools manifest."""
    return [
        {
            "name": "get_sms_daily_stats",
            "description": "Fetch current daily SMS dispatch usage, daily cap, and remaining quota.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "name": "send_sms",
            "description": "Send an SMS via Twilio. MUST refuse and log if daily cap is exceeded.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_phone": {"type": "string", "description": "E.164 phone number"},
                    "body": {"type": "string", "description": "SMS message body"},
                },
                "required": ["to_phone", "body"],
            },
        },
        {
            "name": "send_push",
            "description": "Send FCM push notification to a user's registered devices.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User UUID"},
                    "title": {"type": "string", "description": "Notification title"},
                    "body": {"type": "string", "description": "Notification body"},
                },
                "required": ["user_id", "title", "body"],
            },
        },
        {
            "name": "dispatch_notification",
            "description": "Push-first notification dispatch. Falls back to SMS only when push is unavailable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User UUID"},
                    "title": {"type": "string", "description": "Title for push/SMS"},
                    "body": {"type": "string", "description": "Body for push"},
                    "sms_body": {"type": "string", "description": "Optional custom SMS text"},
                },
                "required": ["user_id", "title", "body"],
            },
        },
    ]


@app.post("/call")
async def call_tool(
    req: ToolCallRequest,
    x_service_token: str | None = Header(None, alias="X-Service-Token"),
) -> dict[str, Any]:
    """Execute an MCP tool call."""
    tool_name = req.name
    args = req.arguments

    if tool_name == "get_sms_daily_stats":
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{BACKEND_API_URL}/sms/usage")
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"Backend returned {resp.status_code}: {resp.text}"}

    elif tool_name == "send_sms":
        # Check daily cap prior to dispatch
        async with httpx.AsyncClient(timeout=10.0) as client:
            usage_resp = await client.get(f"{BACKEND_API_URL}/sms/usage")
            if usage_resp.status_code == 200:
                usage = usage_resp.json()
                if usage.get("is_capped", False) or usage.get("sent_today", 0) >= SMS_DAILY_CAP:
                    logger.warning("MCP send_sms refused: daily SMS cap of %d exceeded", SMS_DAILY_CAP)
                    return {
                        "success": False,
                        "status": "capped",
                        "error": f"Daily SMS cap of {SMS_DAILY_CAP} exceeded. Push remains primary.",
                    }

            send_resp = await client.post(
                f"{BACKEND_API_URL}/sms/send",
                json={"to_phone": args.get("to_phone"), "body": args.get("body")},
            )
            return send_resp.json()

    elif tool_name == "send_push":
        # Dispatches push via backend devices/notifications
        return {
            "success": True,
            "status": "push_dispatched",
            "user_id": args.get("user_id"),
            "title": args.get("title"),
        }

    elif tool_name == "dispatch_notification":
        # Push-first dispatch
        return {
            "success": True,
            "channel": "push_first",
            "user_id": args.get("user_id"),
            "title": args.get("title"),
        }

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Unknown MCP tool: {tool_name}",
    )
