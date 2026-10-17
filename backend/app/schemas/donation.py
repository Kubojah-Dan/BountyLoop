"""BountyLoop — Donation & Review Queue Pydantic Schemas.

Defines request/response contracts for:
- Donation creation & confirmation
- Donation details & pagination
- Human review queue triage & resolution
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import (
    DonationStatus,
    FoodCategory,
    FreshnessGrade,
    HazardFlag,
    ReviewReason,
    ReviewStatus,
)


class DonationConfirm(BaseModel):
    """Payload for donor confirmation/correction of CV predictions."""

    item: FoodCategory | None = Field(
        default=None,
        description="Confirmed food category (overrides initial CV prediction if corrected).",
    )
    freshness: FreshnessGrade | None = Field(
        default=None,
        description="Confirmed freshness grade (overrides initial CV prediction if corrected).",
    )
    est_weight_kg: float | None = Field(
        default=None,
        ge=0.1,
        le=5000.0,
        description="Confirmed or adjusted weight in kilograms.",
    )


class DonationRead(BaseModel):
    """Complete serialized representation of a donation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    donor_id: uuid.UUID
    photo_paths: list[str] = Field(default_factory=list)
    item: FoodCategory
    item_confidence: float
    freshness: FreshnessGrade
    freshness_confidence: float
    hazard_flag: HazardFlag
    est_weight_kg: float
    expires_at: datetime
    status: DonationStatus
    needs_review: bool
    model_versions: dict[str, Any] | None = None
    created_at: datetime

    # Denormalized / enriched donor presentation fields
    donor_name: str | None = None
    donor_address: str | None = None


class ReviewQueueRead(BaseModel):
    """Review queue item requiring human triage."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    donation_id: uuid.UUID
    reason: ReviewReason
    status: ReviewStatus
    resolved_by: uuid.UUID | None = None
    resolved_at: datetime | None = None
    note: str | None = None
    created_at: datetime
    donation: DonationRead | None = None


class ReviewResolve(BaseModel):
    """Operator adjudication payload to resolve a review queue item."""

    status: ReviewStatus = Field(
        default=ReviewStatus.resolved,
        description="Resolution status (typically resolved).",
    )
    note: str | None = Field(
        default=None,
        description="Operator explanation or adjudication rationale.",
    )
    override_item: FoodCategory | None = Field(
        default=None,
        description="Corrected food category if initial classification was mistaken.",
    )
    override_freshness: FreshnessGrade | None = Field(
        default=None,
        description="Corrected freshness grade if initial classification was mistaken.",
    )
    override_weight_kg: float | None = Field(
        default=None,
        ge=0.1,
        description="Corrected weight in kilograms if adjusted during review.",
    )
    approve_for_dispatch: bool = Field(
        default=True,
        description="If True, marks donation as open and clears needs_review flag.",
    )
