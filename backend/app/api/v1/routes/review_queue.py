"""BountyLoop — Human Review Queue Triage & Resolution Endpoints.

Allows operators (admins and volunteers) to adjudicate low-confidence predictions,
safety hazard flags, and edge cases (§6 Phase 5 & Phase 8).
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import require_role
from app.db.models import (
    Donation,
    DonationStatus,
    Donor,
    ReviewQueue,
    ReviewStatus,
    User,
    UserRole,
)
from app.db.session import get_db
from app.schemas.donation import (
    DonationRead,
    ReviewQueueRead,
    ReviewResolve,
)
from app.services.freshness_rules import calculate_expiry
from app.services.label_store import append_label_record
from app.services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/review-queue", tags=["review-queue"])


def _build_review_read(item: ReviewQueue) -> ReviewQueueRead:
    """Format ReviewQueue entity into response schema with populated donation."""
    donation_read = None
    if item.donation:
        donor_name = None
        donor_address = None
        if item.donation.donor:
            donor_address = item.donation.donor.address
            if item.donation.donor.user:
                donor_name = (
                    item.donation.donor.user.display_name or item.donation.donor.user.org_name
                )

        donation_read = DonationRead(
            id=item.donation.id,
            donor_id=item.donation.donor_id,
            photo_paths=list(item.donation.photo_paths or []),
            item=item.donation.item,
            item_confidence=float(item.donation.item_confidence),
            freshness=item.donation.freshness,
            freshness_confidence=float(item.donation.freshness_confidence),
            hazard_flag=item.donation.hazard_flag,
            est_weight_kg=float(item.donation.est_weight_kg),
            expires_at=item.donation.expires_at,
            status=item.donation.status,
            needs_review=item.donation.needs_review,
            model_versions=item.donation.model_versions,
            created_at=item.donation.created_at,
            donor_name=donor_name,
            donor_address=donor_address,
        )

    return ReviewQueueRead(
        id=item.id,
        donation_id=item.donation_id,
        reason=item.reason,
        status=item.status,
        resolved_by=item.resolved_by,
        resolved_at=item.resolved_at,
        note=item.note,
        created_at=item.created_at,
        donation=donation_read,
    )


@router.get(
    "",
    summary="List review queue items (Admin/Volunteer only)",
    response_model=dict,
)
async def list_review_queue(
    status_filter: Annotated[ReviewStatus | None, Query(alias="status")] = ReviewStatus.pending,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.volunteer)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Query pending or resolved review queue items with eager-loaded donation context."""
    query = (
        select(ReviewQueue)
        .options(
            selectinload(ReviewQueue.donation).selectinload(Donation.donor).selectinload(Donor.user)
        )
        .order_by(ReviewQueue.created_at.desc())
    )
    count_query = select(func.count()).select_from(ReviewQueue)

    if status_filter:
        query = query.where(ReviewQueue.status == status_filter)
        count_query = count_query.where(ReviewQueue.status == status_filter)

    total_count = (await db.execute(count_query)).scalar() or 0
    items_result = await db.execute(query.limit(limit).offset(offset))
    review_items = items_result.scalars().all()

    return {
        "items": [_build_review_read(item) for item in review_items],
        "total": total_count,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/{review_id}/resolve",
    summary="Resolve review queue item (Admin/Volunteer only)",
    response_model=ReviewQueueRead,
)
async def resolve_review_item(
    review_id: uuid.UUID,
    payload: ReviewResolve,
    current_user: User = Depends(require_role(UserRole.admin, UserRole.volunteer)),
    db: AsyncSession = Depends(get_db),
) -> ReviewQueueRead:
    """Adjudicate and resolve a review queue item.

    Allows human operators to correct classifications, approve donations for
    matching dispatch, and log training records for model fine-tuning.
    """
    stmt = (
        select(ReviewQueue)
        .options(
            selectinload(ReviewQueue.donation).selectinload(Donation.donor).selectinload(Donor.user)
        )
        .where(ReviewQueue.id == review_id)
    )
    result = await db.execute(stmt)
    review_item = result.scalar_one_or_none()

    if not review_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review queue item '{review_id}' not found.",
        )

    donation = review_item.donation
    initial_item = donation.item.value
    initial_freshness = donation.freshness.value

    # Apply operator overrides if provided
    if payload.override_item is not None:
        donation.item = payload.override_item
    if payload.override_freshness is not None:
        donation.freshness = payload.override_freshness
    if payload.override_weight_kg is not None:
        donation.est_weight_kg = payload.override_weight_kg

    # Recompute shelf-life
    donation.expires_at = calculate_expiry(
        donation.item, donation.freshness, base_time=donation.created_at
    )

    if payload.approve_for_dispatch:
        donation.needs_review = False
        if donation.status == DonationStatus.draft:
            donation.status = DonationStatus.open

    # Update review queue entry
    now = datetime.now(UTC)
    review_item.status = payload.status
    review_item.resolved_by = current_user.id
    review_item.resolved_at = now
    review_item.note = payload.note

    # Log adjudication to retraining store (§5.7)
    primary_photo = donation.photo_paths[0] if donation.photo_paths else "photos/unknown.jpg"
    append_label_record(
        donation_id=str(donation.id),
        donor_id=str(donation.donor_id),
        photo_path=primary_photo,
        initial_item=initial_item,
        initial_freshness=initial_freshness,
        confirmed_item=donation.item.value,
        confirmed_freshness=donation.freshness.value,
        confirmed_weight_kg=float(donation.est_weight_kg),
    )

    await db.commit()
    await db.refresh(review_item)

    response_data = _build_review_read(review_item)
    await ws_manager.broadcast("review_resolved", response_data.model_dump(mode="json"))

    return response_data
