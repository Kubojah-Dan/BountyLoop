"""BountyLoop — SMS & Communication Schemas.

Pydantic models for SMS dispatch, daily quota usage, and inbound webhooks.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class SmsUsageRead(BaseModel):
    """Current day's SMS dispatch volume and budget limits."""

    date: str
    sent_today: int
    daily_cap: int
    remaining: int
    is_capped: bool


class SmsSendRequest(BaseModel):
    """Request to send an outbound SMS."""

    to_phone: str = Field(..., description="Recipient phone number in E.164 format")
    body: str = Field(..., max_length=1600, description="SMS text content")
    user_id: uuid.UUID | None = None
    claim_id: uuid.UUID | None = None


class SmsSendResponse(BaseModel):
    """Outcome of an SMS dispatch attempt."""

    success: bool
    status: str
    to_phone: str
    body: str
    daily_count: int
    daily_cap: int
    message_sid: str | None = None
    error: str | None = None


class InboundWebhookResponse(BaseModel):
    """Parsed outcome of an inbound Twilio SMS webhook."""

    status: str
    command: str
    reply: str
    claim_id: str | None = None
    user_id: str | None = None
