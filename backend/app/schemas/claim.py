"""BountyLoop — Claim, Offer, and Device Schemas.

Defines Pydantic contracts for:
- Device FCM registration (POST /v1/devices)
- Recipient candidate offers query (GET /v1/offers)
- Claim creation, decline, and pickup verification (POST /v1/claims)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import ClaimStatus, DonationStatus, FoodCategory, FreshnessGrade
from app.schemas.donation import DonationRead


class DeviceRegister(BaseModel):
    """Payload to register an FCM device token."""

    fcm_token: str = Field(..., min_length=10, max_length=512, description="FCM device token")
    platform: str = Field(
        default="android", max_length=32, description="Device OS: android, ios, web"
    )


class OfferRead(BaseModel):
    """Candidate surplus offer for recipient discovery."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    donor_id: uuid.UUID
    donor_name: str | None = None
    donor_address: str | None = None
    photo_paths: list[str] = Field(default_factory=list)
    item: FoodCategory
    freshness: FreshnessGrade
    est_weight_kg: float
    expires_at: datetime
    hours_remaining: float
    distance_km: float | None = None
    status: DonationStatus
    created_at: datetime


class ClaimCreate(BaseModel):
    """Request payload to claim a donation."""

    donation_id: uuid.UUID = Field(..., description="ID of the open donation being claimed")


class ClaimDecline(BaseModel):
    """Request payload to decline an offer."""

    reason: str | None = Field(
        default=None, max_length=255, description="Reason for declining offer"
    )


class ClaimPickup(BaseModel):
    """Request payload to confirm donation pickup."""

    proof_photo_path: str | None = Field(
        default=None, description="Optional path to pickup proof photo"
    )
    notes: str | None = Field(default=None, max_length=512, description="Optional pickup notes")


class ClaimRead(BaseModel):
    """Serialized representation of a claim and its lifecycle status."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    donation_id: uuid.UUID
    recipient_id: uuid.UUID
    recipient_name: str | None = None
    donor_name: str | None = None
    status: ClaimStatus
    score: float
    score_breakdown: dict[str, Any] | None = None
    offered_at: datetime
    responded_at: datetime | None = None
    picked_up_at: datetime | None = None
    proof_photo_path: str | None = None
    donation: DonationRead | None = None
    impact: dict[str, float] | None = None
